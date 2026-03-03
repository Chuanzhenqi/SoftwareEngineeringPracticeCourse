"""
pipeline/parser.py
PDF / DOCX → 结构化 Markdown 文本

主要逻辑：
1. pdfplumber 提取文本（带坐标，可识别标题层级）
2. 将粗标题还原为 Markdown heading
3. 若 pdfplumber 失败，fallback 到 PyMuPDF
4. 返回带页码信息的 ParsedDocument
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber
import fitz  # PyMuPDF fallback
from loguru import logger


@dataclass
class ParsedPage:
    page_num: int
    text: str       # 清洗后 Markdown 文本


@dataclass
class ParsedDocument:
    file_path: str
    file_name: str
    pages: list[ParsedPage] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())


# ── 标题层级推断（基于字体大小 & 粗体标志）─────────────────────────────────
_HEADING_MIN_SIZE = 11.0

def _size_to_heading(size: float, is_bold: bool) -> Optional[str]:
    """把字体大小映射成 Markdown heading 前缀，返回 None 表示正文"""
    if size >= 18:
        return "# "
    if size >= 15:
        return "## "
    if size >= 13:
        return "### "
    if size >= _HEADING_MIN_SIZE and is_bold:
        return "#### "
    return None


def _clean_line(line: str) -> str:
    """去除多余空白，合并零宽字符"""
    line = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", line)
    line = re.sub(r" {3,}", "  ", line)
    return line.strip()


def _parse_page_pdfplumber(page: pdfplumber.page.Page) -> str:
    """精确解析单页，尽可能还原 heading 层级"""
    words = page.extract_words(
        extra_attrs=["fontname", "size"],
        keep_blank_chars=False,
    )
    if not words:
        return page.extract_text() or ""

    lines: list[str] = []
    current_line_words: list[dict] = []
    current_y = None

    for w in words:
        y = round(float(w.get("top", 0)), 1)
        if current_y is None or abs(y - current_y) < 3:
            current_y = y
            current_line_words.append(w)
        else:
            # 提交上一行
            lines.append(_flush_line(current_line_words))
            current_line_words = [w]
            current_y = y
    if current_line_words:
        lines.append(_flush_line(current_line_words))

    return "\n".join(lines)


def _flush_line(words: list[dict]) -> str:
    sizes = [float(w.get("size", 10)) for w in words]
    fonts = [w.get("fontname", "") for w in words]
    text = " ".join(w["text"] for w in words)
    text = _clean_line(text)

    avg_size = sum(sizes) / len(sizes) if sizes else 10
    is_bold = any("Bold" in f or "bold" in f for f in fonts)
    prefix = _size_to_heading(avg_size, is_bold)
    return f"{prefix}{text}" if prefix else text


def _parse_page_pymupdf(page: fitz.Page) -> str:
    """fallback：pymupdf 提取，尝试识别标题"""
    blocks = page.get_text("dict")["blocks"]
    lines: list[str] = []
    for b in blocks:
        for line in b.get("lines", []):
            spans = line.get("spans", [])
            texts = [s["text"] for s in spans if s["text"].strip()]
            if not texts:
                continue
            full = _clean_line(" ".join(texts))
            max_size = max((s["size"] for s in spans), default=10)
            is_bold = any("bold" in s["font"].lower() for s in spans)
            prefix = _size_to_heading(max_size, is_bold)
            lines.append(f"{prefix}{full}" if prefix else full)
    return "\n".join(lines)


# ── 后处理：删除模板噪声 ──────────────────────────────────────────────────
_NOISE_PATTERNS = [
    re.compile(r"^[\*_~>]{0,3}\s*本条应.{0,60}$"),
    re.compile(r"^[\*_~>]{0,3}\s*说明：.*$"),
    re.compile(r"^[\*_~>]{0,3}\s*最终文档请删除.*$"),
    re.compile(r"^[\*_~>]{0,3}\s*\[?TOC\]?$", re.IGNORECASE),
]

def _remove_template_noise(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if any(p.match(stripped) for p in _NOISE_PATTERNS):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


# ── 公共 API ─────────────────────────────────────────────────────────────
def parse_pdf(path: str | Path) -> ParsedDocument:
    """解析 PDF 文件，返回 ParsedDocument"""
    path = Path(path)
    doc = ParsedDocument(file_path=str(path), file_name=path.name)
    logger.info(f"开始解析 PDF：{path.name}")

    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                try:
                    raw = _parse_page_pdfplumber(page)
                except Exception as exc:
                    logger.warning(f"pdfplumber 精细解析失败，回退基础提取（file={path.name}, page={i}）：{type(exc).__name__}: {exc}")
                    raw = page.extract_text() or ""
                cleaned = _remove_template_noise(raw)
                if cleaned.strip():
                    doc.pages.append(ParsedPage(page_num=i, text=cleaned))
    except Exception as exc:
        logger.warning(f"pdfplumber 整体解析失败，切换到 PyMuPDF（file={path.name}）：{type(exc).__name__}: {exc}")
        # fallback to PyMuPDF
        try:
            fitz_doc = fitz.open(str(path))
            for i, page in enumerate(fitz_doc, 1):
                raw = _parse_page_pymupdf(page)
                cleaned = _remove_template_noise(raw)
                if cleaned.strip():
                    doc.pages.append(ParsedPage(page_num=i, text=cleaned))
            fitz_doc.close()
        except Exception as fallback_exc:
            logger.exception(f"PyMuPDF fallback 解析失败（file={path.name}）")
            raise RuntimeError(
                f"PDF 解析失败（pdfplumber={type(exc).__name__}: {exc}; "
                f"pymupdf={type(fallback_exc).__name__}: {fallback_exc}）"
            ) from fallback_exc

    logger.info(f"PDF 解析完成：{path.name}，共 {len(doc.pages)} 页有效内容")

    return doc


def parse_docx(path: str | Path) -> ParsedDocument:
    """DOCX → ParsedDocument，每个段落为一 “page”"""
    from docx import Document as DocxDocument
    path = Path(path)
    doc = ParsedDocument(file_path=str(path), file_name=path.name)
    logger.info(f"开始解析 DOCX：{path.name}")

    try:
        dx = DocxDocument(str(path))
    except Exception as exc:
        logger.exception(f"DOCX 解析失败（file={path.name}）")
        raise RuntimeError(f"DOCX 解析失败：{type(exc).__name__}: {exc}") from exc
    current_lines: list[str] = []
    page_num = 1

    def _flush():
        nonlocal page_num
        text = _remove_template_noise("\n".join(current_lines).strip())
        if text:
            doc.pages.append(ParsedPage(page_num=page_num, text=text))
            page_num += 1
        current_lines.clear()

    def _heading_level_from_style(style_name: str) -> int | None:
        lowered = style_name.lower().strip()
        if "heading 1" in lowered or "标题 1" in style_name:
            return 1
        if "heading 2" in lowered or "标题 2" in style_name:
            return 2
        if "heading 3" in lowered or "标题 3" in style_name:
            return 3
        if "heading" in lowered or "标题" in style_name:
            return 4
        return None

    for para in dx.paragraphs:
        raw = para.text.strip()
        if not raw:
            continue
        style = para.style.name if para.style else ""
        level = _heading_level_from_style(style)

        # 标题模式: Heading / 标题 1/2/3 → Markdown heading
        if level is not None:
            _flush()
            current_lines.append(f"{'#' * level} {raw}")
        else:
            current_lines.append(raw)

        # 每 60 行切一个虚拟页（避免单页过大）
        if len(current_lines) >= 60:
            _flush()

    _flush()
    logger.info(f"DOCX 解析完成：{path.name}，共 {len(doc.pages)} 页有效内容")
    return doc


def parse_md(path: str | Path) -> ParsedDocument:
    """Markdown 文件 → ParsedDocument，按一级标题切割虚拟页"""
    path = Path(path)
    doc = ParsedDocument(file_path=str(path), file_name=path.name)
    logger.info(f"开始解析 Markdown：{path.name}")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.exception(f"Markdown 读取失败（file={path.name}）")
        raise RuntimeError(f"Markdown 读取失败：{type(exc).__name__}: {exc}") from exc
    text = _remove_template_noise(text)

    # 按 H1/H2 切割成多个虚拟页
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#{1,2} ", line) and current:
            sections.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current))

    for i, sec in enumerate(sections, 1):
        sec = sec.strip()
        if sec:
            doc.pages.append(ParsedPage(page_num=i, text=sec))
    logger.info(f"Markdown 解析完成：{path.name}，共 {len(doc.pages)} 页有效内容")
    return doc


def parse_document(path: str | Path) -> ParsedDocument:
    """Dispatcher: 根据后缀自动选择解析器"""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix == ".docx":
        return parse_docx(path)
    if suffix in (".md", ".markdown"):
        return parse_md(path)
    raise ValueError(f"不支持的文件类型：{suffix}，支持 .pdf / .docx / .md")