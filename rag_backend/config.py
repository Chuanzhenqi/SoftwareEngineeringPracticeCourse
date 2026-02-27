"""全局配置（从 .env 文件或环境变量读取）"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

# ── 路径 ──────────────────────────────────────────
BASE_DIR = Path(__file__).parent
RULES_DIR = BASE_DIR / "rules"

# ── Qdrant ────────────────────────────────────────
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "se_course_docs")

# ── Embedding ─────────────────────────────────────
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "16"))
VECTOR_DIM = 1024   # bge-m3 dense 维度

# ── Chunking ──────────────────────────────────────
CHUNK_MIN_CHARS = 200
CHUNK_MAX_CHARS = 700
CHUNK_OVERLAP_CHARS = 100

# ── 检索 ──────────────────────────────────────────
TOPK_RECALL = 50       # 向量召回候选数
TOPK_RERANK = 12       # rerank 后保留数
CONTINUITY_EXPAND = 4  # 跨阶段连续性补链数

# 综合评分权重（见 rag方案.md §11.4）
SCORE_W_SIM = 0.60
SCORE_W_META = 0.25
SCORE_W_CONTINUITY = 0.15

# ── Metadata 自动生成 ─────────────────────────────
CONFIDENCE_THRESHOLD = 0.75   # 低于此值进入人工复核队列
