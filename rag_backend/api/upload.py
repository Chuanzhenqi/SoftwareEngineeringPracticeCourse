"""
api/upload.py
POST /api/upload  → 上传 PDF/DOCX，存入 MinIO，触发入库流水线
"""

from __future__ import annotations
import io
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from pipeline.ingest import ingest_file
from config import MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_BUCKET, MINIO_SECURE

router = APIRouter(prefix="/api", tags=["ingest"])


def _format_exc(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _norm_optional_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    if v.lower() in {"string", "none", "null"}:
        return None
    return v


def _get_minio_client():
    """懒加载 MinIO 客户端（MinIO 不可用时不影响启动）"""
    try:
        from minio import Minio
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ROOT_USER,
            secret_key=MINIO_ROOT_PASSWORD,
            secure=MINIO_SECURE,
        )
        # 确保 bucket 存在
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
        return client
    except Exception as exc:
        logger.warning(f"MinIO 连接失败，原始文件将不被备份：{_format_exc(exc)}")
        return None


def _save_to_minio(client, filename: str, content: bytes) -> str | None:
    """将文件内容上传到 MinIO，返回 object key；失败返回 None"""
    if client is None:
        return None
    try:
        object_key = filename
        client.put_object(
            MINIO_BUCKET,
            object_key,
            io.BytesIO(content),
            length=len(content),
            content_type="application/octet-stream",
        )
        logger.info(f"原始文件已备份至 MinIO：{MINIO_BUCKET}/{object_key}")
        return object_key
    except Exception as exc:
        logger.warning(f"MinIO 上传失败：{_format_exc(exc)}")
        return None


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(..., description="待入库 PDF/DOCX 文件"),
    project_id: Optional[str] = Form(None, description="项目 ID（可选，自动推断）"),
    term: Optional[str] = Form(None, description="春季 / 夏季（可选，自动推断）"),
    year: Optional[int] = Form(None, description="年份，如 2024（可选，自动推断）"),
):
    """
    上传 PDF/DOCX 文档并入库。

    - 原始文件同步备份至 MinIO 对象存储。
    - 自动完成解析、分块、metadata 生成、向量化入库（Qdrant）。
    - project_id / term / year 若不填写则由文件名与内容自动推断。
    - 返回入库统计报告，含 needs_review_count（需人工核查的块数）。
    """
    project_id = _norm_optional_str(project_id)
    term = _norm_optional_str(term)
    logger.info(f"收到上传请求：filename={file.filename}, project_id={project_id}, term={term}, year={year}")
    if not file.filename.lower().endswith((".pdf", ".docx", ".md", ".markdown")):
        raise HTTPException(status_code=400, detail="仅支持 PDF、DOCX 或 Markdown 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    logger.info(f"文件读取完成：filename={file.filename}, size={len(content)} bytes")

    # 1. 备份原始文件到 MinIO
    minio_client = _get_minio_client()
    object_key = _save_to_minio(minio_client, file.filename, content)

    # 2. 写入临时文件（保留原始文件名，用于规则推断）
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
        logger.exception(f"入库失败：{file.filename}")
        raise HTTPException(status_code=500, detail=f"入库失败：{_format_exc(e)}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    report["minio_object"] = object_key  # 把备份路径带回给前端
    logger.info(f"上传入库成功：filename={file.filename}, chunks_inserted={report.get('chunks_inserted', 0)}")
    return JSONResponse(content={"success": True, "report": report})


@router.get("/files")
async def list_files():
    """列出 MinIO 中已备份的原始文件列表"""
    minio_client = _get_minio_client()
    if minio_client is None:
        return JSONResponse(content={"files": [], "error": "MinIO 不可用"})
    try:
        objects = minio_client.list_objects(MINIO_BUCKET, recursive=True)
        files = [
            {
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
            }
            for obj in objects
        ]
        return JSONResponse(content={"files": files})
    except Exception as exc:
        logger.exception("列出 MinIO 文件失败")
        return JSONResponse(content={"files": [], "error": str(exc)})
