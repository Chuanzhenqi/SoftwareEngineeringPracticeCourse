"""
vectordb/retriever.py
混合检索 + 重排 + 连续性扩展（见 rag方案.md §6 & §11）

检索流程：
  1. 硬过滤（term / phase / doc_type）
  2. Dense + Sparse 混合召回 TopK_recall
  3. Cross-encoder Rerank → TopK_rerank
  4. 连续性扩展（沿 trace_links 补跨阶段 chunk）
  5. 综合评分 + 排序
  6. 返回结果（含命中原因）
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue, MatchAny,
    SearchRequest, SparseVector,
    QueryResponse,
)

from config import (
    QDRANT_COLLECTION,
    TOPK_RECALL, TOPK_RERANK, CONTINUITY_EXPAND,
    SCORE_W_SIM, SCORE_W_META, SCORE_W_CONTINUITY,
    RERANK_ENABLED, RERANK_MODEL,
)
from vectordb.client import get_qdrant_client
from vectordb.embedder import embed_query

# Reranker（lazy 加载）
_reranker = None

# 文档名命中上限加分：在保留语义检索主导的前提下，
# 让“查询里包含文档名”的场景更稳定地返回对应文档。
DOCNAME_MAX_BONUS = 0.20

_FILE_HINT_RE = re.compile(r"([^\s/\\]+\.(?:pdf|docx|md|markdown))", re.IGNORECASE)
_QUOTED_HINT_RE = re.compile(r"[\"'`《](.{3,120}?)[\"'`》]")
_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", re.IGNORECASE)


def _get_reranker():
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker
        logger.info(f"加载 Reranker 模型：{RERANK_MODEL}")
        _reranker = FlagReranker(RERANK_MODEL, use_fp16=True)
    return _reranker


def _extract_docname_hints(query: str) -> list[str]:
    hints: list[str] = []

    for m in _FILE_HINT_RE.findall(query):
        s = (m or "").strip().lower()
        if s:
            hints.append(s)

    for m in _QUOTED_HINT_RE.findall(query):
        s = (m or "").strip().lower()
        if s:
            hints.append(s)

    # 去重并保持顺序
    seen = set()
    uniq = []
    for h in hints:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq


def _file_stem_and_name(source_file: str) -> tuple[str, str]:
    # source_file 常见格式："{document_id}/原始文件名.ext"
    # 这里统一抽 basename + stem 参与匹配。
    p = Path(str(source_file))
    name = p.name.lower()
    stem = p.stem.lower()
    return stem, name


def _docname_match_score(query: str, payload: dict, hints: Optional[list[str]] = None) -> tuple[float, str]:
    source_file = str(payload.get("source_file") or "").strip()
    if not source_file:
        return 0.0, "none"

    stem, name = _file_stem_and_name(source_file)
    query_lc = (query or "").lower()
    hints = hints or []

    # 强命中：查询直接包含完整文件名或 stem
    if name and name in query_lc:
        return 1.0, "filename_in_query"
    if stem and stem in query_lc:
        return 0.95, "filestem_in_query"

    # hint 命中：例如 query 中提到 "需求规格说明书.md" 或带引号标题
    for h in hints:
        if h in name:
            return 0.9, "hint_in_filename"
        if h in stem:
            return 0.85, "hint_in_filestem"

    # token 交集命中：容忍下划线/短横线/空格差异
    q_tokens = set(_TOKEN_RE.findall(query_lc))
    f_tokens = set(_TOKEN_RE.findall(stem or name))
    if not q_tokens or not f_tokens:
        return 0.0, "none"
    inter = q_tokens & f_tokens
    if not inter:
        return 0.0, "none"

    overlap = len(inter) / max(1, len(f_tokens))
    if overlap >= 0.7:
        return 0.8, "token_overlap_high"
    if overlap >= 0.4:
        return 0.6, "token_overlap_mid"
    return 0.35, "token_overlap_low"


def _docname_recall(
    client: QdrantClient,
    query: str,
    qdrant_filter: Optional[Filter],
    limit: int,
) -> list[dict]:
    """
    仅当 query 含“文档名信号”时触发补充召回：
    通过扫描 payload.source_file 做字符串匹配，把相关 chunk 追加到候选集。
    """
    hints = _extract_docname_hints(query)
    if not hints:
        return []

    matched: list[dict] = []
    seen_ids: set[str] = set()
    offset = None
    scanned = 0
    max_scan = 3000  # 防止在大库上全量扫描

    while len(matched) < limit and scanned < max_scan:
        hits, offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=qdrant_filter,
            limit=256,
            with_payload=True,
            with_vectors=False,
            offset=offset,
        )
        if not hits:
            break

        scanned += len(hits)
        for h in hits:
            hid = str(h.id)
            if hid in seen_ids:
                continue
            payload = h.payload or {}
            score, reason = _docname_match_score(query, payload, hints)
            if score < 0.6:
                continue

            seen_ids.add(hid)
            matched.append(
                {
                    "id": hid,
                    "score": 0.2 + 0.2 * score,
                    "payload": payload,
                    "docname_score": score,
                    "docname_reason": reason,
                }
            )
            if len(matched) >= limit:
                break

        if offset is None:
            break

    matched.sort(key=lambda x: x.get("docname_score", 0.0), reverse=True)
    return matched[:limit]


# 过滤条件构建 ─
def _build_filter(
    term: Optional[str] = None,
    phase: Optional[str] = None,
    doc_type: Optional[str] = None,
    project_id: Optional[str] = None,
    quality_level: Optional[list[str]] = None,
    artifact_type: Optional[str] = None,
) -> Optional[Filter]:
    must = []

    def add(field, value):
        if value:
            must.append(FieldCondition(key=field, match=MatchValue(value=value)))

    add("term", term)
    add("phase", phase)
    add("doc_type", doc_type)
    add("project_id", project_id)
    add("artifact_type", artifact_type)

    if quality_level:
        must.append(FieldCondition(key="quality_level", match=MatchAny(any=quality_level)))

    return Filter(must=must) if must else None


def _relaxed_filter_chain(
    term: Optional[str],
    phase: Optional[str],
    doc_type: Optional[str],
    project_id: Optional[str],
    quality_level: Optional[list[str]],
    artifact_type: Optional[str],
) -> list[Optional[Filter]]:
    """
    渐进式放宽过滤条件：
    1) 全量过滤
    2) 放宽 doc_type / quality_level / artifact_type
    3) 继续放宽 phase
    4) 最后放宽 term

    project_id 始终保留，避免跨项目串库。
    """
    chain = [
        _build_filter(
            term=term,
            phase=phase,
            doc_type=doc_type,
            project_id=project_id,
            quality_level=quality_level,
            artifact_type=artifact_type,
        ),
        _build_filter(
            term=term,
            phase=phase,
            doc_type=None,
            project_id=project_id,
            quality_level=None,
            artifact_type=None,
        ),
        _build_filter(
            term=term,
            phase=None,
            doc_type=None,
            project_id=project_id,
            quality_level=None,
            artifact_type=None,
        ),
        _build_filter(
            term=None,
            phase=None,
            doc_type=None,
            project_id=project_id,
            quality_level=None,
            artifact_type=None,
        ),
    ]

    # 去重（Filter 对象不可哈希，使用 repr 作为稳定键）
    uniq: list[Optional[Filter]] = []
    seen: set[str] = set()
    for f in chain:
        key = repr(f)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    return uniq


# 混合召回
def _hybrid_search(
    client: QdrantClient,
    query_vec: dict,
    qdrant_filter: Optional[Filter],
    limit: int,
) -> list[dict]:
    """Dense + Sparse 混合 query，返回标准化结果列表"""
    sparse_dict = query_vec.get("sparse", {})
    sparse_indices = [int(k) for k in sparse_dict.keys()]
    sparse_values = [float(v) for v in sparse_dict.values()]

    # Qdrant Query API（1.9+）支持 prefetch + 融合
    try:
        from qdrant_client.models import (
            Query, FusionQuery, Prefetch, Fusion
        )
        results = client.query_points(
            collection_name=QDRANT_COLLECTION,
            prefetch=[
                Prefetch(
                    query=query_vec["dense"],
                    using="dense",
                    limit=limit,
                    filter=qdrant_filter,
                ),
                Prefetch(
                    query=SparseVector(indices=sparse_indices, values=sparse_values),
                    using="sparse",
                    limit=limit,
                    filter=qdrant_filter,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=limit,
        ).points
    except Exception as exc:
        logger.warning(f"Qdrant 混合检索失败，回退 dense-only：{type(exc).__name__}: {exc}")
        # fallback: 仅 dense
        results = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=("dense", query_vec["dense"]),
            query_filter=qdrant_filter,
            limit=limit,
            with_payload=True,
        )

    return [
        {"id": str(r.id), "score": r.score, "payload": r.payload}
        for r in results
    ]


# 综合评分
def _composite_score(
    sim: float,
    payload: dict,
    required_meta: dict,
    docname_score: float = 0.0,
    docname_reason: str = "none",
) -> tuple[float, dict]:
    """
    Score = 0.60*Sim + 0.25*MetaMatch + 0.15*Continuity
    (见 rag方案.md §11.4)
    """
    # MetaMatch
    meta_hits = 0
    meta_total = 0
    for k, v in required_meta.items():
        if v is not None:
            meta_total += 1
            if payload.get(k) == v:
                meta_hits += 1
    meta_match = meta_hits / meta_total if meta_total else 0.5

    # Continuity：有 trace_links 或 req_ids 的块加分
    has_trace = bool(payload.get("trace_links"))
    has_req = bool(payload.get("req_ids"))
    continuity = 0.8 if (has_trace and has_req) else (0.5 if has_req else 0.2)

    score = (
        SCORE_W_SIM * sim
        + SCORE_W_META * meta_match
        + SCORE_W_CONTINUITY * continuity
        + DOCNAME_MAX_BONUS * docname_score
    )

    why = {
        "why_semantic_score": round(sim, 4),
        "why_metadata_match": f"{meta_hits}/{meta_total}",
        "why_continuity": "trace+req" if has_trace else ("req_only" if has_req else "none"),
        "why_docname_match": docname_reason,
        "why_docname_score": round(docname_score, 4),
    }
    return round(score, 4), why


# 连续性扩展
def _continuity_expand(
    client: QdrantClient,
    results: list[dict],
    expand_n: int,
) -> list[dict]:
    """
    从 top 结果的 trace_links 中找关联 chunk，
    按 chunk_id 到 Qdrant payload 查询并追加。
    """
    existing_ids = {r["id"] for r in results}
    extra = []

    for r in results[:TOPK_RERANK // 2]:  # 只对 top 一半扩展
        links = r["payload"].get("trace_links", [])
        for link in links[:expand_n]:
            linked_id_pat = link.get("to", "")
            if not linked_id_pat:
                continue
            # 用 section_path 关键词做 payload 过滤召回
            try:
                hits = client.scroll(
                    collection_name=QDRANT_COLLECTION,
                    scroll_filter=Filter(
                        must=[FieldCondition(
                            key="req_ids",
                            match=MatchAny(any=[linked_id_pat]),
                        )]
                    ),
                    limit=2,
                    with_payload=True,
                )[0]
                for h in hits:
                    hid = str(h.id)
                    if hid not in existing_ids:
                        extra.append({"id": hid, "score": 0.0, "payload": h.payload})
                        existing_ids.add(hid)
            except Exception as exc:
                logger.warning(
                    f"连续性扩展查询失败，跳过该 link（to={linked_id_pat}）："
                    f"{type(exc).__name__}: {exc}"
                )
        if len(extra) >= expand_n:
            break

    return extra


# 公共 API
def search(
    query: str,
    term: Optional[str] = None,
    phase: Optional[str] = None,
    doc_type: Optional[str] = None,
    project_id: Optional[str] = None,
    quality_level: Optional[list[str]] = None,
    artifact_type: Optional[str] = None,
    use_reranker: bool = True,
) -> list[dict]:
    """
    返回 TopK_rerank 条结果，每条含：
      text / metadata / composite_score / why_hit
    """
    logger.info(
        f"开始检索：query={query[:60]!r}, phase={phase}, term={term}, "
        f"doc_type={doc_type}, use_reranker={use_reranker}"
    )
    client = get_qdrant_client()

    # 1. Embedding
    query_vec = embed_query(query)

    # 2. 过滤条件（支持渐进放宽）
    qdrant_filter = _build_filter(
        term=term, phase=phase, doc_type=doc_type,
        project_id=project_id, quality_level=quality_level,
        artifact_type=artifact_type,
    )
    required_meta = {
        "term": term, "phase": phase, "doc_type": doc_type,
        "quality_level": quality_level[0] if quality_level else None,
    }

    # 3. 混合召回（严格过滤结果过少时自动放宽）
    filter_chain = _relaxed_filter_chain(
        term=term,
        phase=phase,
        doc_type=doc_type,
        project_id=project_id,
        quality_level=quality_level,
        artifact_type=artifact_type,
    )
    candidates: list[dict] = []
    by_id: dict[str, dict] = {}
    target_min = max(8, TOPK_RERANK)
    for idx, f in enumerate(filter_chain):
        batch = _hybrid_search(client, query_vec, f, TOPK_RECALL)
        for b in batch:
            hid = b["id"]
            if hid in by_id:
                # 保留更高分
                if float(b.get("score", 0.0)) > float(by_id[hid].get("score", 0.0)):
                    by_id[hid] = b
            else:
                by_id[hid] = b
                candidates.append(b)

        if len(candidates) >= target_min:
            if idx > 0:
                logger.info(f"严格过滤结果偏少，已放宽至第 {idx + 1} 层过滤，候选数={len(candidates)}")
            break

    # 文档名补充召回：当 query 中出现文件名/标题 hint 时，把相关文档补入候选。
    docname_candidates = _docname_recall(
        client=client,
        query=query,
        qdrant_filter=qdrant_filter,
        limit=max(4, TOPK_RERANK // 2),
    )
    if docname_candidates:
        by_id = {c["id"]: c for c in candidates}
        merged = list(candidates)
        for dc in docname_candidates:
            existed = by_id.get(dc["id"])
            if existed is None:
                merged.append(dc)
                by_id[dc["id"]] = dc
            else:
                existed["docname_score"] = max(
                    float(existed.get("docname_score", 0.0)),
                    float(dc.get("docname_score", 0.0)),
                )
                if "docname_reason" not in existed:
                    existed["docname_reason"] = dc.get("docname_reason", "none")
        candidates = merged
    logger.debug(f"召回候选：{len(candidates)} 条")

    if not candidates:
        return []

    # 4. Rerank（cross-encoder）
    if use_reranker and not RERANK_ENABLED:
        logger.info("已跳过 reranker：RERANK_ENABLED=false（当前仅使用向量召回结果）")

    if use_reranker and RERANK_ENABLED and len(candidates) > TOPK_RERANK:
        try:
            reranker = _get_reranker()
            pairs = [(query, c["payload"].get("text", "")) for c in candidates]
            rr_scores = reranker.compute_score(pairs, normalize=True)
            for c, rs in zip(candidates, rr_scores):
                c["rerank_score"] = float(rs)
                c["ranking_score"] = float(rs) + DOCNAME_MAX_BONUS * float(c.get("docname_score", 0.0))
            candidates.sort(key=lambda x: x.get("ranking_score", x.get("rerank_score", 0)), reverse=True)
        except Exception as exc:
            logger.warning(f"Reranker 不可用，自动降级为仅向量召回：{type(exc).__name__}: {exc}")

    candidates = candidates[:TOPK_RERANK]

    # 5. 连续性扩展
    extra = _continuity_expand(client, candidates, CONTINUITY_EXPAND)
    candidates.extend(extra)

    # 6. 综合评分
    output = []
    for c in candidates:
        sim = c.get("rerank_score", c.get("score", 0.0))
        composite, why = _composite_score(
            sim=sim,
            payload=c["payload"],
            required_meta=required_meta,
            docname_score=float(c.get("docname_score", 0.0)),
            docname_reason=str(c.get("docname_reason", "none")),
        )
        output.append({
            "text": c["payload"].get("text", ""),
            "metadata": {k: v for k, v in c["payload"].items() if k != "text"},
            "composite_score": composite,
            "why_hit": why,
        })

    # 按阶段顺序排（需求→设计→实现→测试部署），相同阶段按评分降序
    phase_order = {"requirement": 0, "design": 1, "implementation": 2, "testing_deployment": 3}
    output.sort(key=lambda x: (
        phase_order.get(x["metadata"].get("phase", ""), 9),
        -x["composite_score"],
    ))
    logger.info(f"检索完成：返回 {len(output)} 条")

    return output
