"""
pipeline/chunker.py
两层分块策略（见 rag方案.md §3）：
  第一层：按 Markdown heading 结构边界切块
  第二层：在结构块内做滑动窗口语义切分（按字符数）

每块携带 section_path（标题栈）供 metadata 生成使用。
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field

from config import CHUNK_MAX_CHARS, CHUNK_MIN_CHARS, CHUNK_OVERLAP_CHARS
from pipeline.parser import ParsedDocument


@dataclass
class TextChunk:
    text: str
    section_path: str       # 如 "3. 需求 > 3.4 能力需求 > 3.4.2 用户管理"
    page_start: int = 0
    chunk_index: int = 0    # 在文档内的顺序编号


# ── 标题识别 ─────────────────────────────────────────────────────────────
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _parse_heading(line: str) -> tuple[int, str] | None:
    """返回 (level, title_text) 或 None"""
    m = _HEADING_RE.match(line.strip())
    return (len(m.group(1)), m.group(2).strip()) if m else None


# ── 第一层：按 heading 边界切块 ──────────────────────────────────────────
def _structural_split(full_text: str) -> list[tuple[str, list[str]]]:
    """
    返回 [(section_text, heading_stack), ...]
    heading_stack 是当前章节的祖先标题列表
    """
    lines = full_text.splitlines()
    sections: list[tuple[list[str], list[str]]] = []  # (lines, heading_stack)
    heading_stack: list[tuple[int, str]] = []
    current: list[str] = []

    def push_section():
        if any(l.strip() for l in current):
            path = " > ".join(t for _, t in heading_stack)
            sections.append(("\n".join(current), list(heading_stack)))
        current.clear()

    for line in lines:
        h = _parse_heading(line)
        if h:
            level, title = h
            push_section()
            # 更新标题栈：弹出同级或更深的标题
            heading_stack = [(lvl, t) for lvl, t in heading_stack if lvl < level]
            heading_stack.append((level, title))
        current.append(line)

    push_section()

    result = []
    for text, stack in sections:
        path = " > ".join(t for _, t in stack)
        result.append((text, path))
    return result


# ── 第二层：滑动窗口语义切分 ─────────────────────────────────────────────
def _semantic_split(text: str, section_path: str, page_start: int, start_idx: int
                    ) -> list[TextChunk]:
    """在一个结构块内按字符数做滑动窗口切分"""
    # 按自然边界（句号/分号/列表项/换行）优先断开
    sentences = re.split(r"(?<=[。！？；\n])", text)
    sentences = [s for s in sentences if s.strip()]

    chunks: list[TextChunk] = []
    buf = ""
    idx = start_idx

    for sent in sentences:
        if len(buf) + len(sent) <= CHUNK_MAX_CHARS:
            buf += sent
        else:
            if len(buf) >= CHUNK_MIN_CHARS:
                chunks.append(TextChunk(
                    text=buf.strip(),
                    section_path=section_path,
                    page_start=page_start,
                    chunk_index=idx,
                ))
                idx += 1
                # 保留 overlap
                buf = buf[-CHUNK_OVERLAP_CHARS:] + sent
            else:
                buf += sent  # 当前块太短，继续积累

    if buf.strip() and len(buf.strip()) >= CHUNK_MIN_CHARS // 2:
        chunks.append(TextChunk(
            text=buf.strip(),
            section_path=section_path,
            page_start=page_start,
            chunk_index=idx,
        ))

    return chunks


# ── 特殊块检测（表格/接口/编号列表单独成块，不拆分）────────────────────
_SPECIAL_PATTERNS = [
    re.compile(r"(\|.+\|.+\n){2,}"),          # Markdown 表格
    re.compile(r"(FR|NFR|IF|TC|SD)-\d+"),      # 编号体系
    re.compile(r"```[\s\S]+?```"),              # 代码块
]


def _is_special(text: str) -> bool:
    return any(p.search(text) for p in _SPECIAL_PATTERNS)


# ── 公共 API ─────────────────────────────────────────────────────────────
def chunk_document(doc: ParsedDocument) -> list[TextChunk]:
    """对一整份 ParsedDocument 做两层分块，返回有序 TextChunk 列表"""
    full_text = doc.full_text
    structural_sections = _structural_split(full_text)

    all_chunks: list[TextChunk] = []
    idx = 0

    for sec_text, section_path in structural_sections:
        if not sec_text.strip():
            continue

        # 特殊内容整块保留，不二次切分
        if _is_special(sec_text) or len(sec_text) <= CHUNK_MAX_CHARS:
            all_chunks.append(TextChunk(
                text=sec_text.strip(),
                section_path=section_path,
                page_start=0,
                chunk_index=idx,
            ))
            idx += 1
        else:
            sub = _semantic_split(sec_text, section_path, 0, idx)
            all_chunks.extend(sub)
            idx += len(sub)

    return all_chunks
