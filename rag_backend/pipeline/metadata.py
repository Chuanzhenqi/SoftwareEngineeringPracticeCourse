"""
pipeline/metadata.py
Metadata 自动生成（见 rag方案.md §12）

优先级：
  A. 规则抽取（高精度，来自文件路径 / 标题 / 正则）
  B. 章节关键词词典匹配（半规则）
  C. confidence 打分 + 低置信度标记

不依赖外部模型，所有字段均可纯规则完成；
quality_level 通过简单启发式规则打分（可后续替换为模型）。
"""

from __future__ import annotations
import hashlib
import re
from pathlib import Path
from typing import Optional

import yaml

from config import CONFIDENCE_THRESHOLD, RULES_DIR
from pipeline.chunker import TextChunk


# ── 规则文件加载 ──────────────────────────────────────────────────────────
def _load_rules() -> dict:
    rules_path = RULES_DIR / "metadata_rules.yaml"
    with open(rules_path, encoding="utf-8") as f:
        return yaml.safe_load(f)

_RULES: dict = {}

def get_rules() -> dict:
    global _RULES
    if not _RULES:
        _RULES = _load_rules()
    return _RULES


# ── A. 路径 / 文件名规则抽取 ─────────────────────────────────────────────
_YEAR_RE = re.compile(r"(20\d{2})")
_TERM_ZH = {"春季": ["春季", "spring"], "夏季": ["夏季", "summer", "暑"]}


def _extract_year(path_str: str) -> tuple[Optional[int], float]:
    m = _YEAR_RE.search(path_str)
    return (int(m.group(1)), 1.0) if m else (None, 0.0)


def _extract_term(path_str: str) -> tuple[Optional[str], float]:
    rules = get_rules().get("term_rules", {})
    for term, keywords in rules.items():
        if any(kw.lower() in path_str.lower() for kw in keywords):
            return term, 1.0
    return None, 0.0


def _extract_doc_type_and_phase(filename: str) -> tuple[Optional[str], Optional[str], float]:
    """从文件名/文档一级标题匹配 doc_type 和 phase"""
    rules = get_rules().get("doc_type_rules", [])
    for rule in rules:
        if re.search(rule["pattern"], filename):
            return rule["doc_type"], rule["phase"], 0.98
    return None, None, 0.0


def _extract_project_id(path_str: str) -> tuple[Optional[str], float]:
    """
    从路径中提取 project_id：
    约定：路径中包含项目文件夹名，格式如 projA / 项目名_年份
    """
    parts = Path(path_str).parts
    # 取倒数第 2 段作为候选 project 目录
    if len(parts) >= 2:
        candidate = parts[-2]
        # 过滤纯年份或学期目录
        if not re.fullmatch(r"20\d{2}|春季|夏季|summer|spring", candidate, re.IGNORECASE):
            # 转换为合法 slug
            slug = re.sub(r"[^\w\-]", "_", candidate)[:32]
            return slug, 0.90
    return None, 0.0


# ── B. 章节关键词匹配 ────────────────────────────────────────────────────
def _match_rule(text: str, rules: list[dict], key: str) -> tuple[Optional[str], float]:
    for rule in rules:
        if re.search(rule["pattern"], text):
            return rule[key], 0.85
    return None, 0.0


def _extract_artifact_type(section_path: str, text: str) -> tuple[Optional[str], float]:
    combined = section_path + " " + text[:200]
    return _match_rule(combined, get_rules().get("artifact_rules", []), "artifact_type")


def _extract_evidence_type(text: str) -> tuple[Optional[str], float]:
    return _match_rule(text, get_rules().get("evidence_rules", []), "evidence_type")


def _extract_status(text: str) -> tuple[Optional[str], float]:
    rules = get_rules().get("status_rules", {})
    for status, keywords in rules.items():
        if any(kw in text for kw in keywords):
            return status, 0.80
    return None, 0.0


# ── C. 编号提取（req_ids / design_ids / test_ids）────────────────────────
_REQ_RE = re.compile(r"\b(FR|NFR|IF)-\d+\b")
_DESIGN_RE = re.compile(r"\b(SD|DES)-\d+\b")
_TEST_RE = re.compile(r"\b(TC|TEST)-\d+\b")
_IMPL_RE = re.compile(r"\b([A-Z][a-zA-Z0-9]*(?:Controller|Service|Repository|Manager|Handler|API))\b")


def _extract_ids(text: str) -> dict:
    req_ids = list(set(_REQ_RE.findall(text)))
    design_ids = list(set(_DESIGN_RE.findall(text)))
    test_ids = list(set(_TEST_RE.findall(text)))
    impl_refs = list(set(m for m in _IMPL_RE.findall(text) if len(m) > 4))

    # 简单 trace_links：同块内同时出现 req + test/design 建立边
    trace_links = []
    for r in req_ids:
        for t in test_ids:
            trace_links.append({"from": r, "to": t})
        for d in design_ids:
            trace_links.append({"from": r, "to": d})

    return {
        "req_ids": req_ids,
        "design_ids": design_ids,
        "test_ids": test_ids,
        "impl_refs": impl_refs,
        "trace_links": trace_links,
    }


# ── D. 质量评分（启发式）────────────────────────────────────────────────
def _heuristic_quality(text: str, chunk_len: int) -> tuple[str, float]:
    """
    high:  含编号/度量/代码块/表格，且长度充足
    low:   过短或几乎全是模板噪声
    medium: 其他
    """
    has_id = bool(_REQ_RE.search(text) or _TEST_RE.search(text))
    has_metric = bool(re.search(r"\d+ms|\d+%|TPS|QPS|并发", text))
    has_code = "```" in text
    has_table = re.search(r"\|.+\|", text) is not None

    score = sum([has_id, has_metric, has_code, has_table])
    if score >= 2 and chunk_len >= 200:
        return "high", 0.80
    if chunk_len < 80:
        return "low", 0.75
    return "medium", 0.70


# ── chunk_id 生成 ─────────────────────────────────────────────────────────
def _make_chunk_id(year: Optional[int], term: Optional[str], project_id: Optional[str],
                   doc_type: Optional[str], chunk_index: int, text: str) -> str:
    parts = [
        str(year or "unk"),
        (term or "unk").replace(" ", ""),
        (project_id or "unk")[:12],
        (doc_type or "unk")[:8],
        str(chunk_index),
        hashlib.md5(text[:50].encode()).hexdigest()[:6],
    ]
    return "-".join(parts)


# ── 合并置信度（各字段加权平均）─────────────────────────────────────────
def _overall_confidence(conf: dict) -> float:
    weights = {
        "year": 0.1, "term": 0.15, "doc_type": 0.25,
        "phase": 0.20, "artifact_type": 0.15,
        "quality_level": 0.05, "evidence_type": 0.05,
        "status": 0.05,
    }
    total, weight_sum = 0.0, 0.0
    for k, w in weights.items():
        if k in conf:
            total += conf[k] * w
            weight_sum += w
    return total / weight_sum if weight_sum else 0.0


# ── 公共 API ──────────────────────────────────────────────────────────────
def generate_metadata(
    chunk: TextChunk,
    file_path: str,
    first_heading: str = "",
) -> tuple[dict, dict, bool]:
    """
    Returns:
        metadata (dict)    : 面向 Qdrant payload 的字段
        confidence (dict)  : 各字段置信度
        needs_review (bool): 是否需要人工复核
    """
    fp = file_path
    filename = Path(fp).name + " " + first_heading

    year, cy = _extract_year(fp)
    term, ct = _extract_term(fp)
    doc_type, phase, cdt = _extract_doc_type_and_phase(filename)
    project_id, cpid = _extract_project_id(fp)
    artifact_type, cat = _extract_artifact_type(chunk.section_path, chunk.text)
    evidence_type, cev = _extract_evidence_type(chunk.text)
    status, cst = _extract_status(chunk.text)
    quality_level, cql = _heuristic_quality(chunk.text, len(chunk.text))

    ids = _extract_ids(chunk.text)

    chunk_id = _make_chunk_id(year, term, project_id, doc_type, chunk.chunk_index, chunk.text)

    metadata = {
        "course": "软件工程实践",
        "chunk_id": chunk_id,
        "year": year,
        "term": term,
        "project_id": project_id,
        "doc_type": doc_type,
        "phase": phase,
        "section_path": chunk.section_path,
        "artifact_type": artifact_type,
        "evidence_type": evidence_type,
        "status": status,
        "quality_level": quality_level,
        **ids,
    }

    confidence = {
        "year": cy, "term": ct, "doc_type": cdt,
        "phase": cdt,  # phase 与 doc_type 一起抽取
        "project_id": cpid,
        "artifact_type": cat,
        "evidence_type": cev,
        "status": cst,
        "quality_level": cql,
    }

    overall = _overall_confidence(confidence)

    # 人工复核触发条件（见 rag方案.md §12.5）
    missing_required = any(metadata.get(k) is None for k in
                           ["term", "doc_type", "phase", "project_id"])
    needs_review = missing_required or overall < CONFIDENCE_THRESHOLD

    metadata["_confidence_overall"] = round(overall, 3)
    metadata["_needs_review"] = needs_review

    return metadata, confidence, needs_review
