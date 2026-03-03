"""
api/search.py
POST /api/search  → 混合检索 + 重排
GET  /api/search  → 简单关键词检索（快速调试）
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from vectordb.retriever import search

router = APIRouter(prefix="/api", tags=["search"])


def _norm_optional_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    if v.lower() in {"string", "none", "null"}:
        return None
    return v


def _norm_quality_level(value: Optional[list[str]]) -> Optional[list[str]]:
    if not value:
        return None
    cleaned = [x.strip() for x in value if isinstance(x, str) and x.strip() and x.strip().lower() not in {"string", "none", "null"}]
    return cleaned or None


class SearchRequest(BaseModel):
    query: str = Field(..., description="自然语言检索语句")
    term: Optional[str] = Field(None, description="春季 / 夏季")
    phase: Optional[str] = Field(
        None, description="requirement / design / implementation / testing_deployment"
    )
    doc_type: Optional[str] = Field(None, description="文档类型，如'需求'")
    project_id: Optional[str] = Field(None, description="限定某个项目")
    quality_level: Optional[list[str]] = Field(
        None, description="质量级别过滤：['high'] 或 ['high','medium']"
    )
    artifact_type: Optional[str] = Field(
        None, description="内容类型：requirement / interface / test_case ..."
    )
    use_reranker: bool = Field(True, description="是否使用 cross-encoder 重排")


class SearchResult(BaseModel):
    text: str
    metadata: dict
    composite_score: float
    why_hit: dict


@router.post("/search", response_model=list[SearchResult])
async def search_documents(req: SearchRequest):
    """
    混合检索（Dense + Sparse）+ 重排 + 连续性扩展。

    返回结果按"需求→设计→实现→测试部署"阶段顺序排列，相同阶段按综合评分降序。

    每条结果附 `why_hit`，说明命中原因（语义相似度 / 标签匹配率 / 连续性）。
    """
    term = _norm_optional_str(req.term)
    phase = _norm_optional_str(req.phase)
    doc_type = _norm_optional_str(req.doc_type)
    project_id = _norm_optional_str(req.project_id)
    artifact_type = _norm_optional_str(req.artifact_type)
    quality_level = _norm_quality_level(req.quality_level)

    results = search(
        query=req.query,
        term=term,
        phase=phase,
        doc_type=doc_type,
        project_id=project_id,
        quality_level=quality_level,
        artifact_type=artifact_type,
        use_reranker=req.use_reranker,
    )
    return results


@router.get("/search", response_model=list[SearchResult])
async def search_simple(
    q: str = Query(..., description="查询语句"),
    phase: Optional[str] = Query(None),
    term: Optional[str] = Query(None),
):
    """GET 简化接口，快速调试用"""
    return search(
        query=q,
        phase=_norm_optional_str(phase),
        term=_norm_optional_str(term),
    )
