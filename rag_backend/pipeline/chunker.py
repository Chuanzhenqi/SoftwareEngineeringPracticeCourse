"""
pipeline/chunker.py
两层分块策略（见 rag方案.md §3）：
    第一层：按 Markdown 一级/二级标题切块；当段落过长时按三级标题补切
    第二层：在结构块内做滑动窗口语义切分（按字符数）

说明：
    - 当同一文档包含多个“模块小结/本章小结”时，优先按小结切开，避免跨模块语义串扰。
    - 每块携带 section_path（标题栈）供 metadata 生成使用。
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


#  标题识别
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_STRUCTURAL_SPLIT_MAX_HEADING_LEVEL = 2
# 二级段落累计过长时，允许在三级标题处补切，提升语义完整性与可读性平衡。
_H3_SPLIT_TRIGGER_CHARS = CHUNK_MAX_CHARS * 2
_SUMMARY_TITLE_RE = re.compile(
    r"^(?:第?[一二三四五六七八九十百千\d]+[章节部分篇]?\s*)?"
    r"(?:本章|本节|模块|阶段|单元)?"
    r"(?:小结|总结|结论|回顾|总结与展望)"
    r"(?:[：:]?.*)?$"
)


def _parse_heading(line: str) -> tuple[int, str] | None:
    """返回 (level, title_text) 或 None"""
    m = _HEADING_RE.match(line.strip())
    return (len(m.group(1)), m.group(2).strip()) if m else None


def _normalize_title(text: str) -> str:
    return re.sub(r"[：:。；;\-—\s]+$", "", text.strip())


def _looks_like_summary_boundary(line: str) -> str | None:
    """
    判断一行是否可作为“小结边界”，返回标准化标题；否则返回 None。

    规则：
    - Markdown heading（### 模块小结）优先按标题文本判断
    - 普通行（OCR/PDF 抽取常见）在长度较短且命中“小结/总结”模式时识别为边界
    """
    heading = _parse_heading(line)
    title = heading[1] if heading else line.strip()
    title = _normalize_title(title)
    if not title:
        return None

    if _SUMMARY_TITLE_RE.match(title):
        return title

    if len(title) <= 32 and ("小结" in title or title.endswith(("总结", "结论"))):
        if re.fullmatch(r"[\w\u4e00-\u9fa5\s、，,。.；;:：()（）《》【】\-]+", title):
            return title
    return None


#  第一层：按 heading 边界切块 
def _structural_split(full_text: str) -> list[tuple[str, list[str]]]:
    """
    返回 [(section_text, heading_stack), ...]
    heading_stack 是当前章节的祖先标题列表。
    默认仅按一级/二级标题切分；若当前段落过长，遇到三级标题触发补切。
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
            # 仅按一级/二级标题进行结构切分，三级及以下标题保留在段内，
            # 以提升单块语义完整性（避免被切得过碎）。
            if level <= _STRUCTURAL_SPLIT_MAX_HEADING_LEVEL:
                push_section()
                # 更新标题栈：弹出同级或更深的标题
                heading_stack = [(lvl, t) for lvl, t in heading_stack if lvl < level]
                heading_stack.append((level, title))
            elif level == 3:
                current_len = len("\n".join(current).strip())
                if current_len >= _H3_SPLIT_TRIGGER_CHARS:
                    push_section()
                    # 触发补切时，把三级标题纳入路径，便于后续定位。
                    heading_stack = [(lvl, t) for lvl, t in heading_stack if lvl < level]
                    heading_stack.append((level, title))
        current.append(line)

    push_section()

    result = []
    for text, stack in sections:
        path = " > ".join(t for _, t in stack)
        result.append((text, path))
    return result


#  第二层：滑动窗口语义切分
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


def _split_by_summary_boundaries(text: str) -> list[tuple[str, str]]:
    """
    在结构块内部继续按“小结边界”拆分。

    返回 [(sub_text, boundary_title), ...]，boundary_title 为空串表示未命中边界。
    """
    lines = text.splitlines()
    if not lines:
        return []

    sections: list[tuple[str, str]] = []
    current_lines: list[str] = []
    current_boundary = ""

    def push_section() -> None:
        if any(line.strip() for line in current_lines):
            sections.append(("\n".join(current_lines).strip(), current_boundary))

    for line in lines:
        boundary_title = _looks_like_summary_boundary(line)
        if boundary_title and any(x.strip() for x in current_lines):
            push_section()
            current_lines = [line]
            current_boundary = boundary_title
            continue
        if boundary_title and not current_lines:
            current_boundary = boundary_title
        current_lines.append(line)

    push_section()
    return sections


#  特殊块检测（表格/接口/编号列表单独成块，不拆分）
_SPECIAL_PATTERNS = [
    re.compile(r"(\|.+\|.+\n){2,}"),          # Markdown 表格
    re.compile(r"(FR|NFR|IF|TC|SD)-\d+"),      # 编号体系
    re.compile(r"```[\s\S]+?```"),              # 代码块
]


def _is_special(text: str) -> bool:
    return any(p.search(text) for p in _SPECIAL_PATTERNS)


#  公共 API ─
def chunk_document(doc: ParsedDocument) -> list[TextChunk]:
    """对一整份 ParsedDocument 做两层分块，返回有序 TextChunk 列表"""
    full_text = doc.full_text
    structural_sections = _structural_split(full_text)

    all_chunks: list[TextChunk] = []
    idx = 0

    for sec_text, section_path in structural_sections:
        if not sec_text.strip():
            continue

        sub_sections = _split_by_summary_boundaries(sec_text)
        if not sub_sections:
            sub_sections = [(sec_text, "")]

        for sub_text, boundary_title in sub_sections:
            scoped_path = section_path
            if boundary_title:
                scoped_path = f"{section_path} > {boundary_title}" if section_path else boundary_title

            # 特殊内容整块保留，不二次切分
            if _is_special(sub_text) or len(sub_text) <= CHUNK_MAX_CHARS:
                all_chunks.append(TextChunk(
                    text=sub_text.strip(),
                    section_path=scoped_path,
                    page_start=0,
                    chunk_index=idx,
                ))
                idx += 1
            else:
                sub = _semantic_split(sub_text, scoped_path, 0, idx)
                all_chunks.extend(sub)
                idx += len(sub)

    return all_chunks
