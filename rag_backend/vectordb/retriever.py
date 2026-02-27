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
)
from vectordb.client import get_qdrant_client
from vectordb.embedder import embed_query

# Reranker（lazy 加载）
_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker
        logger.info("加载 Reranker 模型：BAAI/bge-reranker-v2-m3")
        _reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
    return _reranker


# ── 过滤条件构建 ─────────────────────────────────────────────────────────
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


# ── 混合召回 ─────────────────────────────────────────────────────────────
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
    except Exception:
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


# ── 综合评分 ─────────────────────────────────────────────────────────────
def _composite_score(
    sim: float,
    payload: dict,
    required_meta: dict,
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

    score = SCORE_W_SIM * sim + SCORE_W_META * meta_match + SCORE_W_CONTINUITY * continuity

    why = {
        "why_semantic_score": round(sim, 4),
        "why_metadata_match": f"{meta_hits}/{meta_total}",
        "why_continuity": "trace+req" if has_trace else ("req_only" if has_req else "none"),
    }
    return round(score, 4), why


# ── 连续性扩展 ───────────────────────────────────────────────────────────
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
            except Exception:
                pass
        if len(extra) >= expand_n:
            break

    return extra


# ── 公共 API ─────────────────────────────────────────────────────────────
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
    client = get_qdrant_client()

    # 1. Embedding
    query_vec = embed_query(query)

    # 2. 过滤条件
    qdrant_filter = _build_filter(
        term=term, phase=phase, doc_type=doc_type,
        project_id=project_id, quality_level=quality_level,
        artifact_type=artifact_type,
    )
    required_meta = {
        "term": term, "phase": phase, "doc_type": doc_type,
        "quality_level": quality_level[0] if quality_level else None,
    }

    # 3. 混合召回
    candidates = _hybrid_search(client, query_vec, qdrant_filter, TOPK_RECALL)
    logger.debug(f"召回候选：{len(candidates)} 条")

    if not candidates:
        return []

    # 4. Rerank（cross-encoder）
    if use_reranker and len(candidates) > TOPK_RERANK:
        reranker = _get_reranker()
        pairs = [(query, c["payload"].get("text", "")) for c in candidates]
        rr_scores = reranker.compute_score(pairs, normalize=True)
        for c, rs in zip(candidates, rr_scores):
            c["rerank_score"] = float(rs)
        candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        candidates = candidates[:TOPK_RERANK]
    else:
        candidates = candidates[:TOPK_RERANK]

    # 5. 连续性扩展
    extra = _continuity_expand(client, candidates, CONTINUITY_EXPAND)
    candidates.extend(extra)

    # 6. 综合评分
    output = []
    for c in candidates:
        sim = c.get("rerank_score", c.get("score", 0.0))
        composite, why = _composite_score(sim, c["payload"], required_meta)
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

    return output
