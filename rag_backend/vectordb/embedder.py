"""
vectordb/embedder.py
bge-m3 封装：dense + sparse 双路向量

- dense  : 1024 维，用于向量相似度检索
- sparse : 词权重字典，用于 BM25/稀疏检索
"""

from __future__ import annotations
import os

from loguru import logger

_model = None
_openai_client = None


def _get_model():
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel
        from config import EMBED_MODEL, EMBED_LOCAL_FILES_ONLY, HF_ENDPOINT

        if HF_ENDPOINT:
            os.environ["HF_ENDPOINT"] = HF_ENDPOINT

        logger.info(
            f"加载 Embedding 模型：{EMBED_MODEL} "
            f"(local_only={EMBED_LOCAL_FILES_ONLY}, hf_endpoint={HF_ENDPOINT or 'default'})"
        )

        try:
            _model = BGEM3FlagModel(
                EMBED_MODEL,
                use_fp16=True,
                local_files_only=EMBED_LOCAL_FILES_ONLY,
            )
        except Exception as exc:
            raise RuntimeError(
                "Embedding 模型加载失败：无法从 HuggingFace 下载或读取本地模型。"
                "请检查网络，或在 .env 中设置 HF_ENDPOINT 镜像，"
                "或将 EMBED_MODEL 指向本地模型目录并开启 EMBED_LOCAL_FILES_ONLY=true。"
            ) from exc
    return _model


def _embed_texts_openai_compatible(texts: list[str], batch_size: int) -> list[dict]:
    from config import (
        OPENAI_BASE_URL,
        OPENAI_API_KEY,
        OPENAI_EMBED_MODEL,
        OPENAI_TIMEOUT_SECONDS,
        OPENAI_EMBED_DIMENSIONS,
    )
    from openai import OpenAI

    if not OPENAI_BASE_URL:
        raise RuntimeError("未配置 OPENAI_BASE_URL，无法使用 openai_compatible embedding")
    if not OPENAI_API_KEY:
        raise RuntimeError("未配置 OPENAI_API_KEY，无法使用 openai_compatible embedding")

    global _openai_client
    if _openai_client is None:
        base = OPENAI_BASE_URL.rstrip("/")
        if base.endswith("/embeddings"):
            base = base[:-len("/embeddings")]
        _openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=base,
            timeout=OPENAI_TIMEOUT_SECONDS,
        )
        logger.info(f"初始化 OpenAI 兼容 embedding client：base_url={base}, model={OPENAI_EMBED_MODEL}")

    results: list[dict] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        kwargs = {
            "model": OPENAI_EMBED_MODEL,
            "input": batch,
        }
        if OPENAI_EMBED_DIMENSIONS:
            kwargs["dimensions"] = int(OPENAI_EMBED_DIMENSIONS)

        try:
            response = _openai_client.embeddings.create(**kwargs)
        except Exception as exc:
            logger.exception(f"Embedding API 请求失败：batch_start={i}, batch_size={len(batch)}")
            raise RuntimeError(f"Embedding API 请求失败：{exc}") from exc

        vectors = sorted(response.data, key=lambda x: x.index)
        if len(vectors) != len(batch):
            raise RuntimeError("Embedding API 返回条数与输入不一致")

        for item in vectors:
            emb = item.embedding or []
            if not emb:
                raise RuntimeError("Embedding API 返回空向量")
            results.append({"dense": emb, "sparse": {}})

    return results


def embed_texts(
    texts: list[str],
    batch_size: int | None = None,
    return_sparse: bool = True,
) -> list[dict]:
    """
    返回每条文本的：
      {"dense": [float, ...], "sparse": {token_id: weight, ...}}
    """
    from config import EMBED_BATCH_SIZE, EMBED_PROVIDER
    bs = batch_size or EMBED_BATCH_SIZE
    logger.debug(f"开始 embedding：provider={EMBED_PROVIDER}, texts={len(texts)}, batch_size={bs}")

    if EMBED_PROVIDER == "openai_compatible":
        logger.info("使用 openai_compatible embedding provider")
        return _embed_texts_openai_compatible(texts, bs)

    model = _get_model()

    try:
        outputs = model.encode(
            texts,
            batch_size=bs,
            max_length=512,
            return_dense=True,
            return_sparse=return_sparse,
            return_colbert_vecs=False,
        )
    except Exception as exc:
        logger.exception("本地 embedding 编码失败")
        raise RuntimeError("Embedding 编码失败，请检查模型与运行环境") from exc

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
