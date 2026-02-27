"""
pipeline/ingest.py
全量入库流水线（见 rag方案.md §12.6）

步骤：
  1. PDF 解析
  2. 结构+语义分块
  3. Metadata 自动生成
  4. Embedding（仅 text，metadata 不参与）
  5. 写入 Qdrant
  6. 输出校验报告
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from loguru import logger
from tqdm import tqdm

from pipeline.parser import parse_pdf
from pipeline.chunker import chunk_document
from pipeline.metadata import generate_metadata
from vectordb.client import get_qdrant_client, ensure_collection
from vectordb.schema import build_point


def ingest_file(
    file_path: str | Path,
    project_id: Optional[str] = None,
    term: Optional[str] = None,
    year: Optional[int] = None,
    batch_size: int = 32,
) -> dict:
    """
    入库单个文件，返回统计报告。

    可选参数用于手动覆盖自动推断的 metadata（project_id / term / year）。
    """
    file_path = Path(file_path)
    logger.info(f"开始解析：{file_path.name}")

    # ── 1. 解析 ──────────────────────────────────────────────────────────
    doc = parse_pdf(file_path)
    if not doc.pages:
        return {"status": "empty", "file": str(file_path), "chunks": 0}

    first_heading = ""
    for line in doc.full_text.splitlines():
        if line.startswith("#"):
            first_heading = line.lstrip("#").strip()
            break

    # ── 2. 分块 ──────────────────────────────────────────────────────────
    chunks = chunk_document(doc)
    logger.info(f"分块完成：{len(chunks)} 块")

    # ── 3. Metadata 生成 ─────────────────────────────────────────────────
    points_data = []
    needs_review_list = []

    for chunk in chunks:
        meta, conf, needs_review = generate_metadata(
            chunk=chunk,
            file_path=str(file_path),
            first_heading=first_heading,
        )
        # 手动覆盖
        if project_id:
            meta["project_id"] = project_id
        if term:
            meta["term"] = term
        if year:
            meta["year"] = year

        points_data.append((chunk.text, meta))
        if needs_review:
            needs_review_list.append({"chunk_id": meta["chunk_id"], "reason": "low_confidence"})

    # ── 4 & 5. Embedding + 写入 Qdrant ────────────────────────────────
    from vectordb.embedder import embed_texts  # lazy import（避免启动时加载模型）

    client = get_qdrant_client()
    ensure_collection(client)

    texts = [t for t, _ in points_data]
    metas = [m for _, m in points_data]

    inserted = 0
    for i in tqdm(range(0, len(texts), batch_size), desc="入库中"):
        batch_texts = texts[i:i + batch_size]
        batch_metas = metas[i:i + batch_size]
        vectors = embed_texts(batch_texts)
        pts = [build_point(text=t, vector=v, meta=m)
               for t, v, m in zip(batch_texts, vectors, batch_metas)]
        client.upsert(collection_name=__import__("config").QDRANT_COLLECTION, points=pts)
        inserted += len(pts)

    # ── 6. 校验报告 ──────────────────────────────────────────────────────
    report = {
        "status": "ok",
        "file": str(file_path),
        "pages": len(doc.pages),
        "chunks_total": len(chunks),
        "chunks_inserted": inserted,
        "needs_review_count": len(needs_review_list),
        "needs_review_items": needs_review_list[:20],  # 最多展示 20 条
        "coverage": {
            "has_term_pct": _field_fill_pct(metas, "term"),
            "has_phase_pct": _field_fill_pct(metas, "phase"),
            "has_doc_type_pct": _field_fill_pct(metas, "doc_type"),
        },
    }
    logger.info(f"入库完成：{report}")
    return report


def _field_fill_pct(metas: list[dict], field: str) -> float:
    filled = sum(1 for m in metas if m.get(field))
    return round(filled / len(metas) * 100, 1) if metas else 0.0


def ingest_directory(directory: str | Path, **kwargs) -> list[dict]:
    """批量入库目录下所有 PDF / DOCX"""
    directory = Path(directory)
    files = list(directory.rglob("*.pdf")) + list(directory.rglob("*.docx"))
    logger.info(f"共找到 {len(files)} 个文件待入库")
    return [ingest_file(f, **kwargs) for f in files]
