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
import time
from pathlib import Path
from typing import Optional

from loguru import logger
from tqdm import tqdm

from pipeline.parser import parse_document
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
    start_ts = time.perf_counter()
    file_path = Path(file_path)
    logger.info(f"开始入库：{file_path.name}")

    # ── 1. 解析 ──────────────────────────────────────────────────────────
    try:
        doc = parse_document(file_path)
    except Exception as exc:
        logger.exception(f"文档解析失败：{file_path.name}")
        raise RuntimeError(f"文档解析失败：{type(exc).__name__}: {exc}") from exc
    if not doc.pages:
        logger.warning(f"文档无可用内容，跳过入库：{file_path.name}")
        return {"status": "empty", "file": str(file_path), "chunks": 0}

    first_heading = ""
    for line in doc.full_text.splitlines():
        if line.startswith("#"):
            first_heading = line.lstrip("#").strip()
            break

    # ── 2. 分块 ──────────────────────────────────────────────────────────
    try:
        chunks = chunk_document(doc)
    except Exception as exc:
        logger.exception(f"文档分块失败：{file_path.name}")
        raise RuntimeError(f"文档分块失败：{type(exc).__name__}: {exc}") from exc
    logger.info(f"分块完成：{len(chunks)} 块")

    # ── 3. Metadata 生成 ─────────────────────────────────────────────────
    points_data = []
    needs_review_list = []

    for chunk in chunks:
        try:
            meta, conf, needs_review = generate_metadata(
                chunk=chunk,
                file_path=str(file_path),
                first_heading=first_heading,
            )
        except Exception as exc:
            logger.exception(f"Metadata 生成失败：{file_path.name}")
            raise RuntimeError(f"Metadata 生成失败：{type(exc).__name__}: {exc}") from exc
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
    logger.info(f"开始向量化并写入 Qdrant：{file_path.name}，共 {len(texts)} 条")

    inserted = 0
    for i in tqdm(range(0, len(texts), batch_size), desc="入库中"):
        batch_texts = texts[i:i + batch_size]
        batch_metas = metas[i:i + batch_size]
        logger.debug(f"正在处理批次：{i // batch_size + 1}（batch_size={len(batch_texts)}）")
        try:
            vectors = embed_texts(batch_texts)
        except Exception as exc:
            logger.exception(f"Embedding 失败：{file_path.name}, batch_start={i}")
            raise RuntimeError(f"Embedding 失败：{type(exc).__name__}: {exc}") from exc
        pts = [build_point(text=t, vector=v, meta=m)
               for t, v, m in zip(batch_texts, vectors, batch_metas)]
        try:
            client.upsert(collection_name=__import__("config").QDRANT_COLLECTION, points=pts)
        except Exception as exc:
            logger.exception(f"Qdrant upsert 失败：{file_path.name}, batch_start={i}")
            raise RuntimeError(f"Qdrant 写入失败：{type(exc).__name__}: {exc}") from exc
        inserted += len(pts)

    # ── 6. 校验报告 ──────────────────────────────────────────────────────
    report = {
        "status": "ok",
        "file": str(file_path),
        "pages": len(doc.pages),
        "chunks_total": len(chunks),
        "chunks_summary_scoped": _count_summary_scoped_chunks(chunks),
        "chunks_inserted": inserted,
        "needs_review_count": len(needs_review_list),
        "needs_review_items": needs_review_list[:20],  # 最多展示 20 条
        "coverage": {
            "has_term_pct": _field_fill_pct(metas, "term"),
            "has_phase_pct": _field_fill_pct(metas, "phase"),
            "has_doc_type_pct": _field_fill_pct(metas, "doc_type"),
        },
        "elapsed_seconds": round(time.perf_counter() - start_ts, 3),
    }
    logger.info(
        f"入库完成：file={file_path.name}, inserted={inserted}, "
        f"needs_review={len(needs_review_list)}, elapsed={report['elapsed_seconds']}s"
    )
    return report


def _count_summary_scoped_chunks(chunks: list) -> int:
    return sum(1 for c in chunks if any(k in (c.section_path or "") for k in ("小结", "总结", "结论")))


def _field_fill_pct(metas: list[dict], field: str) -> float:
    filled = sum(1 for m in metas if m.get(field))
    return round(filled / len(metas) * 100, 1) if metas else 0.0


def ingest_directory(directory: str | Path, **kwargs) -> list[dict]:
    """批量入库目录下所有 PDF / DOCX / MD"""
    directory = Path(directory)
    exts = ("*.pdf", "*.docx", "*.md", "*.markdown")
    files = [f for ext in exts for f in directory.rglob(ext)]
    logger.info(f"共找到 {len(files)} 个文件待入库")
    return [ingest_file(f, **kwargs) for f in files]
