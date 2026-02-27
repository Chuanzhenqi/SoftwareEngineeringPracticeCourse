"""
vectordb/client.py
Qdrant 客户端单例 + collection 初始化
"""

from __future__ import annotations

from qdrant_client import QdrantClient

from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION

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
