"""
vectordb/schema.py
Qdrant Collection 建表 schema 与 Point 构建
"""

from __future__ import annotations
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    PayloadSchemaType,
    CreateAliasOperation,
    TextIndexParams,
    TokenizerType,
)

from config import QDRANT_COLLECTION, VECTOR_DIM


def create_collection(client: QdrantClient, collection_name: str = QDRANT_COLLECTION) -> None:
    """
    建表：
    - vectors        : dense (1024 维 Cosine)
    - sparse_vectors : BGE-M3 sparse（为混合检索）
    - payload 索引   : phase / doc_type / term / project_id / quality_level
    """
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
        },
        on_disk_payload=False,
    )

    # 为高频过滤字段建 payload 索引
    for field in ["phase", "doc_type", "term", "project_id", "quality_level",
                  "year", "course", "artifact_type"]:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD,
        )

    # 为 section_path 建全文索引（支持模糊匹配）
    client.create_payload_index(
        collection_name=collection_name,
        field_name="section_path",
        field_schema=TextIndexParams(
            type="text",
            tokenizer=TokenizerType.WORD,
            min_token_len=2,
        ),
    )


def build_point(text: str, vector: dict, meta: dict) -> dict:
    """
    构建 Qdrant PointStruct-like dict
    vector: {"dense": [...], "sparse": {token_id: weight}}
    """
    from qdrant_client.models import PointStruct, SparseVector

    # sparse 格式：indices + values
    sparse_dict = vector.get("sparse", {})
    if sparse_dict:
        indices = [int(k) for k in sparse_dict.keys()]
        values = [float(v) for v in sparse_dict.values()]
        sparse_vec = SparseVector(indices=indices, values=values)
    else:
        sparse_vec = SparseVector(indices=[], values=[])

    payload = {**meta, "text": text}

    return PointStruct(
        id=str(uuid.uuid4()),
        vector={"dense": vector["dense"], "sparse": sparse_vec},
        payload=payload,
    )
