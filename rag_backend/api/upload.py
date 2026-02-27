"""
api/upload.py
POST /api/upload  → 上传 PDF，触发入库流水线
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from pipeline.ingest import ingest_file

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(..., description="待入库 PDF 文件"),
    project_id: Optional[str] = Form(None, description="项目 ID（可选，自动推断）"),
    term: Optional[str] = Form(None, description="春季 / 夏季（可选，自动推断）"),
    year: Optional[int] = Form(None, description="年份，如 2024（可选，自动推断）"),
):
    """
    上传 PDF 文档并入库。

    - 自动完成解析、分块、metadata 生成、向量化入库。
    - project_id / term / year 若不填写则由文件路径与内容自动推断。
    - 返回入库统计报告，含 needs_review_count（需人工核查的块数）。
    """
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="仅支持 PDF 或 DOCX 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    # 写入临时文件（保留原始文件名，用于规则推断）
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix,
        prefix=Path(file.filename).stem + "_",
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        report = ingest_file(
            file_path=tmp_path,
            project_id=project_id,
            term=term,
            year=year,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"入库失败：{e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return JSONResponse(content={"success": True, "report": report})
