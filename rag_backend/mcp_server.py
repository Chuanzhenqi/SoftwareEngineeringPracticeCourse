"""
mcp_server.py
RAG 检索 MCP Server — 供 Claude Code 生成文档时调用

工具列表：
  search_course_docs   主检索入口（混合检索 + 重排 + 连续性扩展）
  get_phase_examples   快捷召回某阶段高质量样例
  get_project_chain    拉取某项目完整瀑布链路（需求→设计→实现→测试）

启动方式（由 .mcp.json 自动管理，也可手动启动调试）：
  cd rag_backend
  python mcp_server.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from vectordb.retriever import search
from vectordb.client import get_qdrant_client
from config import QDRANT_COLLECTION

mcp = FastMCP(
    name="se-course-rag",
    description="软件工程课程历史文档 RAG 检索，供文档生成时参考往年优质案例",
)


# ── 工具 1：通用检索 ────────────────────────────────────────────────────────
@mcp.tool()
def search_course_docs(
    query: str,
    phase: str = None,
    term: str = None,
    doc_type: str = None,
    quality_level: list[str] = None,
    artifact_type: str = None,
    use_reranker: bool = True,
) -> list[dict]:
    """
    从往年课程文档中检索与当前写作内容相关的参考片段。

    Args:
        query: 自然语言检索语句，如"用户登录接口设计"
        phase: 限定阶段 requirement / design / implementation / testing_deployment
        term: 限定学期 春季 / 夏季
        doc_type: 文档类型 需求 / 概要设计 / 详细设计 / 测试报告 / 用户手册 等
        quality_level: 质量过滤 ["high"] 或 ["high","medium"]
        artifact_type: 内容类型 requirement / interface / test_case / data_model 等
        use_reranker: 是否使用 cross-encoder 重排（精度更高但稍慢）

    Returns:
        list of {text, metadata, composite_score, why_hit}
        - text: 原始段落内容
        - metadata: phase/doc_type/section_path/project_id 等
        - composite_score: 综合得分（语义 0.6 + 标签匹配 0.25 + 连续性 0.15）
        - why_hit: 命中原因（语义分 / 标签命中率 / 连续性类型）
    """
    results = search(
        query=query,
        phase=phase,
        term=term,
        doc_type=doc_type,
        quality_level=quality_level,
        artifact_type=artifact_type,
        use_reranker=use_reranker,
    )
    # 精简输出：只返回 text + 关键 metadata + 得分
    return [
        {
            "text": r["text"],
            "source": {
                "project_id": r["metadata"].get("project_id"),
                "doc_type": r["metadata"].get("doc_type"),
                "phase": r["metadata"].get("phase"),
                "section_path": r["metadata"].get("section_path"),
                "quality_level": r["metadata"].get("quality_level"),
                "year": r["metadata"].get("year"),
                "term": r["metadata"].get("term"),
            },
            "score": r["composite_score"],
            "why": r["why_hit"],
        }
        for r in results
    ]


# ── 工具 2：快捷拉取某阶段高质量样例 ─────────────────────────────────────
@mcp.tool()
def get_phase_examples(
    phase: str,
    doc_type: str = None,
    n: int = 5,
) -> list[dict]:
    """
    拉取指定阶段的高质量历史文档片段，用于写作风格和结构参考。

    Args:
        phase: requirement / design / implementation / testing_deployment
        doc_type: 进一步限定文档类型（可选）
        n: 返回条数，默认 5

    Returns:
        高质量片段列表（quality_level=high 优先）
    """
    results = search(
        query=f"{phase} 阶段 典型案例",
        phase=phase,
        doc_type=doc_type,
        quality_level=["high"],
        use_reranker=False,   # 样例拉取不需要精排，追求速度
    )
    return [
        {
            "text": r["text"],
            "source": {
                "project_id": r["metadata"].get("project_id"),
                "doc_type": r["metadata"].get("doc_type"),
                "section_path": r["metadata"].get("section_path"),
            },
            "score": r["composite_score"],
        }
        for r in results[:n]
    ]


# ── 工具 3：拉取某项目的完整瀑布链路 ─────────────────────────────────────
@mcp.tool()
def get_project_chain(project_id: str) -> dict:
    """
    获取某个历史项目的完整瀑布链路快照（需求→设计→实现→测试），
    用于理解"同一项目如何保持各阶段文档的前后一致性"。

    Args:
        project_id: 项目标识，如 "projA"

    Returns:
        {requirement: [...], design: [...], implementation: [...], testing_deployment: [...]}
    """
    client = get_qdrant_client()
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    chain: dict[str, list] = {
        "requirement": [],
        "design": [],
        "implementation": [],
        "testing_deployment": [],
    }

    for phase in chain.keys():
        hits, _ = client.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(key="phase", match=MatchValue(value=phase)),
            ]),
            limit=8,
            with_payload=True,
        )
        chain[phase] = [
            {
                "text": h.payload.get("text", ""),
                "section_path": h.payload.get("section_path", ""),
                "doc_type": h.payload.get("doc_type", ""),
            }
            for h in hits
        ]

    return chain


if __name__ == "__main__":
    mcp.run(transport="stdio")
