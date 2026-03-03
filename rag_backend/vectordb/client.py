"""
vectordb/client.py
Qdrant 客户端单例 + collection 初始化
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from loguru import logger

from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION, VECTOR_DIM

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _client


def ensure_collection(client: QdrantClient) -> None:
    """如果 collection 不存在则自动建表"""
    from vectordb.schema import create_collection
    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in existing:
        create_collection(client, QDRANT_COLLECTION)
        return

    # 已存在时校验向量维度，避免 provider 切换后写入失败
    try:
        info = client.get_collection(QDRANT_COLLECTION)
        vectors_cfg = info.config.params.vectors
        if isinstance(vectors_cfg, dict):
            dense_cfg = vectors_cfg.get("dense")
            current_dim = getattr(dense_cfg, "size", None)
        else:
            current_dim = getattr(vectors_cfg, "size", None)

        if current_dim and int(current_dim) != int(VECTOR_DIM):
            logger.warning(
                f"检测到 Collection 向量维度不一致（existing={current_dim}, expected={VECTOR_DIM}），"
                "将自动重建 collection。"
            )
            create_collection(client, QDRANT_COLLECTION)
    except Exception as exc:
        logger.warning(f"Collection 维度检查失败，跳过自动重建：{exc}")
