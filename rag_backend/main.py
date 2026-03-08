import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.upload import router as upload_router
from api.search import router as search_router
from vectordb.client import get_qdrant_client, ensure_collection

app = FastAPI(
    title="SE Course RAG Backend",
    description="软件工程课程历史文档向量检索后端",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(search_router)


@app.on_event("startup")
async def startup():
    """启动时确保 Qdrant collection 存在"""
    try:
        client = get_qdrant_client()
        ensure_collection(client)
        logger.info("Qdrant collection 就绪")
    except Exception as e:
        logger.warning(f"Qdrant 连接失败，请确认服务已启动：{e}")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
