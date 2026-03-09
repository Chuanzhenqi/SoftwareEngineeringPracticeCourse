"""
mcp_server.py
RAG 检索 MCP Server — 供 Claude Code 生成文档时调用

工具列表：
  search_course_docs        主检索入口（混合检索 + 重排 + 连续性扩展）
  get_phase_examples        快捷召回某阶段高质量样例
  get_project_chain         拉取某项目完整瀑布链路（需求→设计→实现→测试）
  get_template_sections     返回指定文档类型的模版章节结构
  suggest_skills            根据文档阶段/类型返回推荐的 skill 列表
  search_by_section         按模版章节路径定向检索往年同章节内容

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
    instructions="软件工程课程历史文档 RAG 检索，供文档生成时参考往年优质案例",
)

# 模版章节结构（与模版库保持同步）
_TEMPLATE_SECTIONS: dict[str, list[str]] = {
    "软件需求规格说明书": [
        "1 范围 / 1.1 标识 / 1.2 系统概述 / 1.3 文档概述 / 1.4 基线",
        "2 引用文件",
        "3 需求 / 3.1 所需的状态和方式 / 3.2 需求概述 / 3.2.1 目标 / 3.2.2 运行环境",
        "3.3 CSCI能力需求（功能需求）",
        "3.4 CSCI外部接口需求",
        "3.5 CSCI内部接口需求",
        "3.6 适应性需求",
        "3.7 保密性和私密性需求",
        "3.8 CSCI环境需求",
        "3.9 计算机资源需求",
        "3.10 软件质量因素",
        "3.11 设计和实现约束",
        "4 合格性规定",
        "5 需求可追踪性",
        "6 尚未解决的问题",
        "7 注释",
    ],
    "软件概要设计说明书": [
        "1 范围 / 1.1 标识 / 1.2 系统概述 / 1.3 文档概述",
        "2 引用文件",
        "3 系统总体设计 / 3.1 系统基本设计方案 / 3.2 系统组成",
        "4 CSCI体系结构设计 / 4.1 体系结构 / 4.2 模块划分",
        "5 CSCI数据库设计",
        "6 CSCI接口设计 / 6.1 外部接口 / 6.2 内部接口",
        "7 运行设计",
        "8 出错处理设计",
        "9 注释",
    ],
    "软件详细设计说明书": [
        "1 范围",
        "2 引用文件",
        "3 CSCI级设计决策",
        "4 CSCI体系结构设计决策",
        "5 CSCI详细设计 / 5.x 模块详细设计（每模块一条）",
        "6 注释",
    ],
    "软件开发计划书": [
        "1 范围",
        "2 引用文件",
        "3 概述 / 3.1 项目概况 / 3.2 项目假定与约束",
        "4 项目组织",
        "5 项目计划 / 5.1 工作任务的分解与人员分工 / 5.2 进度计划 / 5.3 里程碑",
        "6 技术计划",
        "7 项目支持计划 / 7.1 配置管理计划 / 7.2 质量保证计划",
        "8 注释",
    ],
    "测试报告": [
        "1 范围",
        "2 引用文件",
        "3 测试结果概述 / 3.1 测试目标 / 3.2 测试摘要",
        "4 详细测试结果 / 4.x 各测试用例结果",
        "5 测试日志",
        "6 注释",
    ],
    "迭代需求文档": [
        "1 迭代目标与范围",
        "2 用户故事列表",
        "3 功能需求细化",
        "4 非功能需求",
        "5 验收标准",
        "6 变更记录",
    ],
    "项目管理文档": [
        "1 项目概述",
        "2 迭代计划（Sprint Backlog）",
        "3 任务分工与进度追踪",
        "4 燃尽图 / 速率统计",
        "5 缺陷管理",
        "6 风险管理",
        "7 迭代复盘",
    ],
    "项目总结": [
        "1 项目背景与目标",
        "2 交付成果总览",
        "3 技术方案与实施过程回顾",
        "4 质量与测试结果",
        "5 团队协作与过程管理复盘",
        "6 风险问题与改进措施",
        "7 课程收获与后续计划",
    ],
}

_DOC_TYPE_CANONICAL: dict[str, str] = {
    "软件需求规格说明书": "需求",
    "需求规格说明书": "需求",
    "需求": "需求",
    "软件概要设计说明书": "概要设计",
    "概要设计": "概要设计",
    "软件详细设计说明书": "详细设计",
    "详细设计": "详细设计",
    "软件开发计划书": "开发计划",
    "开发计划": "开发计划",
    "项目管理文档": "项目管理",
    "项目管理": "项目管理",
    "测试报告": "测试报告",
    "用户手册": "用户手册",
    "用户使用说明书": "用户手册",
    "项目总结报告": "项目总结",
    "项目总结": "项目总结",
    "总结报告": "项目总结",
    "人员分工": "人员分工",
}

_DOC_TYPE_TEMPLATE_KEY: dict[str, str] = {
    "软件需求规格说明书": "软件需求规格说明书",
    "需求": "软件需求规格说明书",
    "软件概要设计说明书": "软件概要设计说明书",
    "概要设计": "软件概要设计说明书",
    "软件详细设计说明书": "软件详细设计说明书",
    "详细设计": "软件详细设计说明书",
    "软件开发计划书": "软件开发计划书",
    "开发计划": "软件开发计划书",
    "测试报告": "测试报告",
    "迭代需求文档": "迭代需求文档",
    "项目管理文档": "项目管理文档",
    "项目管理": "项目管理文档",
    "项目总结": "项目总结",
    "项目总结报告": "项目总结",
    "用户手册": "用户手册",
    "用户使用说明书": "用户手册",
}


def _normalize_doc_type_for_search(doc_type: str | None) -> str | None:
    if not doc_type:
        return None
    s = doc_type.strip()
    if not s:
        return None
    return _DOC_TYPE_CANONICAL.get(s, s)


def _normalize_doc_type_for_template(doc_type: str) -> str:
    s = (doc_type or "").strip()
    return _DOC_TYPE_TEMPLATE_KEY.get(s, s)

# 阶段 → 推荐 Skills 映射 
_PHASE_SKILLS: dict[str, list[dict]] = {
    "requirement": [
        {"skill": "se-requirements-doc-assistant", "trigger": "生成需求规格说明书章节内容", "description": "用于结构化产出需求分析文档与验收标准"},
        {"skill": "ambiguity-detector", "trigger": "检测需求文本中的歧义表述", "description": "识别需求中的模糊词、范围不清与缺失约束"},
    ],
    "design": [
        {"skill": "se-architecture-doc-assistant", "trigger": "生成概要设计/详细设计章节", "description": "用于架构、模块、接口与数据结构设计文档输出"},
        {"skill": "api-design-assistant", "trigger": "设计接口规范（OpenAPI格式）", "description": "用于生成标准化接口定义与契约说明"},
    ],
    "implementation": [
        {"skill": "se-implementation-doc-assistant", "trigger": "生成实现阶段文档", "description": "用于整理实现说明、迭代记录与完成度证明"},
        {"skill": "se-project-management-doc-assistant", "trigger": "生成开发计划/迭代记录", "description": "用于生成项目管理材料与过程追踪文档"},
        {"skill": "code-change-summarizer", "trigger": "汇总 git 提交生成开发说明", "description": "用于从提交历史提炼阶段实现总结"},
    ],
    "testing_deployment": [
        {"skill": "se-testing-deployment-doc-assistant", "trigger": "生成测试报告/用户手册/部署说明", "description": "用于测试与部署阶段的文档化交付"},
    ],
    "all": [
        {"skill": "se-course-doc-orchestrator", "trigger": "统筹整个课程文档阶段，不确定从哪份写时优先使用", "description": "用于阶段编排与文档产出流程串联"},
        {"skill": "explain-code", "trigger": "需要在文档中解释代码实现逻辑", "description": "用于将代码行为转换为可读的实现说明"},
    ],
}


# 工具 1：通用检索 
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
        list of {text, source, score, why}
        - text: 原始段落内容
        - source: phase/doc_type/section_path/project_id 等来源信息
        - score: 综合得分（语义 0.6 + 标签匹配 0.25 + 连续性 0.15）
        - why: 命中原因（语义分 / 标签命中率 / 连续性类型）
    """
    normalized_doc_type = _normalize_doc_type_for_search(doc_type)

    results = search(
        query=query,
        phase=phase,
        term=term,
        doc_type=normalized_doc_type,
        quality_level=quality_level,
        artifact_type=artifact_type,
        use_reranker=use_reranker,
    )
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


# 工具 2：快捷拉取某阶段高质量样例 
@mcp.tool()
def get_phase_examples(
    phase: str,
    doc_type: str = None,
    topic_hint: str = None,
    n: int = 5,
) -> list[dict]:
    """
    拉取指定阶段的高质量历史文档片段，用于写作风格和结构参考。

    Args:
        phase: requirement / design / implementation / testing_deployment
        doc_type: 进一步限定文档类型（可选），如"概要设计"
        topic_hint: 内容主题提示（可选），如"数据库设计"或"接口定义"，
                    提供后检索更精准；不提供则返回该阶段通用高质量样例
        n: 返回条数，默认 5

    Returns:
        高质量片段列表（quality_level=high 优先）
    """
    # 用 topic_hint 精准检索，无提示时用阶段代表性关键词
    _DOC_TYPE_QUERY = {
        "需求": "功能需求 用户故事 验收标准",
        "概要设计": "架构设计 模块划分 接口设计",
        "详细设计": "类设计 数据结构 算法流程",
        "测试报告": "测试用例 测试结果 缺陷记录",
        "开发计划": "进度计划 里程碑 人员分工",
        "项目管理": "Sprint Backlog 迭代计划 燃尽图 复盘",
        "项目总结": "项目总结 复盘 技术选型 过程改进",
    }
    _PHASE_DEFAULT_QUERY = {
        "requirement": "功能需求 非功能需求 用例",
        "design": "体系结构 模块设计 数据库 接口",
        "implementation": "开发计划 迭代记录 模块实现",
        "testing_deployment": "测试报告 测试用例 部署说明",
    }

    normalized_doc_type = _normalize_doc_type_for_search(doc_type)

    if topic_hint:
        query = f"{topic_hint}"
    elif normalized_doc_type and normalized_doc_type in _DOC_TYPE_QUERY:
        query = _DOC_TYPE_QUERY[normalized_doc_type]
    else:
        query = _PHASE_DEFAULT_QUERY.get(phase, phase)

    results = search(
        query=query,
        phase=phase,
        doc_type=normalized_doc_type,
        quality_level=["high"],
        use_reranker=False,
    )
    return [
        {
            "text": r["text"],
            "source": {
                "project_id": r["metadata"].get("project_id"),
                "doc_type": r["metadata"].get("doc_type"),
                "section_path": r["metadata"].get("section_path"),
                "year": r["metadata"].get("year"),
                "term": r["metadata"].get("term"),
            },
            "score": r["composite_score"],
        }
        for r in results[:n]
    ]


#  工具 3：拉取某项目的完整瀑布链路
@mcp.tool()
def get_project_chain(project_id: str) -> dict:
    """
    获取某个历史项目的完整瀑布链路快照（需求→设计→实现→测试），
    用于理解"同一项目如何保持各阶段文档的前后一致性"。

    Args:
        project_id: 项目标识，如 "projA"

    Returns:
        {requirement: [...], design: [...], implementation: [...], testing_deployment: [...]}
        每个阶段返回按 quality_level 优先的代表性片段（最多 8 条）
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
        # 按 quality_level 排序（high > medium > low）
        _q_order = {"high": 0, "medium": 1, "low": 2}
        sorted_hits = sorted(
            hits,
            key=lambda h: _q_order.get(h.payload.get("quality_level", "low"), 3)
        )
        chain[phase] = [
            {
                "text": h.payload.get("text", ""),
                "section_path": h.payload.get("section_path", ""),
                "doc_type": h.payload.get("doc_type", ""),
                "quality_level": h.payload.get("quality_level", ""),
            }
            for h in sorted_hits
        ]

    return chain


# 工具 4：获取文档模版章节结构
@mcp.tool()
def get_template_sections(doc_type: str) -> dict:
    """
    返回指定文档类型的模版章节结构，供生成文档时作为框架参考。

    Args:
        doc_type: 文档类型，支持：
            软件需求规格说明书 / 软件概要设计说明书 / 软件详细设计说明书 /
            软件开发计划书 / 测试报告 / 迭代需求文档 / 项目管理文档 / 项目总结

    Returns:
        {doc_type, sections, template_path_hint}
        - sections: 章节列表（按顺序）
        - template_path_hint: 模版文件所在位置（相对于项目根目录）
    """
    _TEMPLATE_PATH_HINT = {
        "软件需求规格说明书": "模版库-供claudeCode调用/提交文件模版/春季/软件需求规格说明书.md",
        "软件概要设计说明书": "模版库-供claudeCode调用/提交文件模版/春季/软件概要设计说明书.md",
        "软件详细设计说明书": "模版库-供claudeCode调用/提交文件模版/春季/软件详细设计说明书.md",
        "软件开发计划书": "模版库-供claudeCode调用/提交文件模版/春季/软件开发计划书.md",
        "测试报告": "模版库-供claudeCode调用/提交文件模版/春季/测试报告.md",
        "迭代需求文档": None,
        "项目管理文档": "模版库-供claudeCode调用/提交文件模版/夏季/项目管理文档.md",
        "项目总结": "模版库-供claudeCode调用/提交文件模版/夏季/项目总结.md",
        "用户手册": "模版库-供claudeCode调用/提交文件模版/春季/用户手册模版.md",
    }

    resolved_doc_type = _normalize_doc_type_for_template(doc_type)

    sections = _TEMPLATE_SECTIONS.get(resolved_doc_type)
    if sections is None:
        available = list(_TEMPLATE_SECTIONS.keys())
        return {
            "error": f"未找到文档类型 '{doc_type}' 的模版",
            "available_doc_types": available,
        }

    return {
        "doc_type": resolved_doc_type,
        "sections": sections,
        "template_path_hint": _TEMPLATE_PATH_HINT.get(resolved_doc_type),
        "usage_note": (
            "请按 sections 列表逐章生成内容，"
            "对每个章节可调用 search_by_section 检索往年同章节的高质量写法"
        ),
    }


# 工具 5：推荐 Skills
@mcp.tool()
def suggest_skills(
    phase: str = None,
    doc_type: str = None,
) -> list[dict]:
    """
    根据当前所处的文档阶段或文档类型，推荐应激活的 Claude Code Skills。

    Args:
        phase: 当前阶段 requirement / design / implementation / testing_deployment
        doc_type: 文档类型（可选，用于更精确推荐），如"软件需求规格说明书"

    Returns:
        list of {skill, trigger, description}
        按推荐优先级排序，第一条为最优先激活的 skill
    """
    _DOC_TYPE_TO_PHASE = {
        "软件需求规格说明书": "requirement",
        "需求": "requirement",
        "迭代需求文档": "requirement",
        "软件概要设计说明书": "design",
        "概要设计": "design",
        "软件详细设计说明书": "design",
        "详细设计": "design",
        "软件开发计划书": "implementation",
        "开发计划": "implementation",
        "项目管理文档": "implementation",
        "项目管理": "implementation",
        "测试报告": "testing_deployment",
        "用户手册": "testing_deployment",
        "项目总结": "testing_deployment",
        "项目总结报告": "testing_deployment",
    }

    # doc_type 覆盖 phase
    resolved_phase = phase
    normalized_doc_type = _normalize_doc_type_for_template(doc_type) if doc_type else None
    if normalized_doc_type and normalized_doc_type in _DOC_TYPE_TO_PHASE:
        resolved_phase = _DOC_TYPE_TO_PHASE[normalized_doc_type]
    elif doc_type and doc_type in _DOC_TYPE_TO_PHASE:
        resolved_phase = _DOC_TYPE_TO_PHASE[doc_type]

    result = list(_PHASE_SKILLS.get("all", []))  # 通用 skills 始终包含
    if resolved_phase and resolved_phase in _PHASE_SKILLS:
        result = _PHASE_SKILLS[resolved_phase] + result

    return result


# 工具 6：按模版章节定向检索
@mcp.tool()
def search_by_section(
    section_path: str,
    doc_type: str = None,
    phase: str = None,
    quality_level: list[str] = None,
    n: int = 3,
) -> list[dict]:
    """
    按章节路径从往年文档中检索同一章节的高质量写法示例。
    适合在逐章节生成文档时，为每个章节提供参考内容。

    Args:
        section_path: 章节路径，如 "3.3 CSCI能力需求" 或 "4 CSCI体系结构设计"
        doc_type: 限定文档类型（推荐提供，提升精准度）
        phase: 限定阶段（可选）
        quality_level: 质量过滤，默认 ["high"]
        n: 返回条数，默认 3

    Returns:
        往年同章节的高质量写法片段列表
    """
    if quality_level is None:
        quality_level = ["high"]

    normalized_doc_type = _normalize_doc_type_for_search(doc_type)

    results = search(
        query=section_path,
        phase=phase,
        doc_type=normalized_doc_type,
        quality_level=quality_level,
        use_reranker=True,
    )
    return [
        {
            "text": r["text"],
            "source": {
                "project_id": r["metadata"].get("project_id"),
                "doc_type": r["metadata"].get("doc_type"),
                "section_path": r["metadata"].get("section_path"),
                "year": r["metadata"].get("year"),
                "term": r["metadata"].get("term"),
            },
            "score": r["composite_score"],
        }
        for r in results[:n]
    ]


if __name__ == "__main__":
    mcp.run(transport="stdio")
