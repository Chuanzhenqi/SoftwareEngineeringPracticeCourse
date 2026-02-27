"""
vectordb/embedder.py
bge-m3 封装：dense + sparse 双路向量

- dense  : 1024 维，用于向量相似度检索
- sparse : 词权重字典，用于 BM25/稀疏检索
"""

from __future__ import annotations
from typing import Union

from loguru import logger

_model = None


def _get_model():
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel
        from config import EMBED_MODEL
        logger.info(f"加载 Embedding 模型：{EMBED_MODEL}")
        _model = BGEM3FlagModel(EMBED_MODEL, use_fp16=True)
    return _model


def embed_texts(
    texts: list[str],
    batch_size: int | None = None,
    return_sparse: bool = True,
) -> list[dict]:
    """
    返回每条文本的：
      {"dense": [float, ...], "sparse": {token_id: weight, ...}}
    """
    from config import EMBED_BATCH_SIZE
    bs = batch_size or EMBED_BATCH_SIZE
    model = _get_model()

    outputs = model.encode(
        texts,
        batch_size=bs,
        max_length=512,
        return_dense=True,
        return_sparse=return_sparse,
        return_colbert_vecs=False,
    )

    dense_vecs = outputs["dense_vecs"]
    lexical_weights = outputs.get("lexical_weights", [{}] * len(texts))

    results = []
    for dv, lw in zip(dense_vecs, lexical_weights):
        results.append({
            "dense": dv.tolist() if hasattr(dv, "tolist") else list(dv),
            "sparse": dict(lw) if lw else {},
        })
    return results


def embed_query(query: str) -> dict:
    """单条查询 embedding"""
    return embed_texts([query])[0]
