"""全局配置（从 .env 文件或环境变量读取）"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

# 路径 
BASE_DIR = Path(__file__).parent
RULES_DIR = BASE_DIR / "rules"

# Qdrant 
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "se_course_docs")

# Embedding 
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "local_bge").lower()  # local_bge / openai_compatible
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "16"))
EMBED_LOCAL_FILES_ONLY = os.getenv("EMBED_LOCAL_FILES_ONLY", "false").lower() == "true"
HF_ENDPOINT = os.getenv("HF_ENDPOINT", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")  # 例如 https://api.apiyi.com/v1
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("APIYI_API_KEY") or os.getenv("API_KEY", "")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
OPENAI_EMBED_DIM = int(os.getenv("OPENAI_EMBED_DIM", "1536"))
OPENAI_EMBED_DIMENSIONS = os.getenv("OPENAI_EMBED_DIMENSIONS", "").strip()

# Reranker（检索重排）
RERANK_ENABLED = os.getenv(
	"RERANK_ENABLED",
	"false" if EMBED_PROVIDER == "openai_compatible" else "true"
).lower() == "true"
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# 可显式覆盖 VECTOR_DIM；否则按 provider 推断
VECTOR_DIM = int(os.getenv(
	"VECTOR_DIM",
	str(OPENAI_EMBED_DIM if EMBED_PROVIDER == "openai_compatible" else 1024)
))

# Chunking 
CHUNK_MIN_CHARS = 200
CHUNK_MAX_CHARS = 700
CHUNK_OVERLAP_CHARS = 100

# 检索 
TOPK_RECALL = 80       # 向量召回候选数（放宽默认召回）
TOPK_RERANK = 18       # rerank 后保留数（提升长尾命中）
CONTINUITY_EXPAND = 4  # 跨阶段连续性补链数

# 综合评分权重（见 rag方案.md §11.4）
SCORE_W_SIM = 0.60
SCORE_W_META = 0.25
SCORE_W_CONTINUITY = 0.15

# Metadata 自动生成 
CONFIDENCE_THRESHOLD = 0.75   # 低于此值进入人工复核队列

# MinIO 对象存储 
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "rag-docs")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
