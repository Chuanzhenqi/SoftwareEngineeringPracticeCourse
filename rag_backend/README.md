# SE Course RAG Backend

PDF 文档解析 + Metadata 自动生成 + Qdrant 向量存取后端。

## 目录结构

```
rag_backend/
├── main.py                  # FastAPI 入口
├── config.py                # 全局配置（从环境变量读取）
├── requirements.txt
├── pipeline/
│   ├── parser.py            # PDF → 结构化 Markdown
│   ├── chunker.py           # 两层分块（结构/小结边界 + 语义）
│   ├── metadata.py          # metadata 自动生成（规则 + 启发式）
│   └── ingest.py            # 全量入库流水线
├── vectordb/
│   ├── embedder.py          # bge-m3 dense + sparse
│   ├── client.py            # Qdrant 客户端单例
│   ├── schema.py            # Collection 建表 & Point 构建
│   └── retriever.py         # 混合检索 + 重排 + 连续性扩展
├── api/
│   ├── upload.py            # POST /api/upload
│   └── search.py            # POST /api/search
├── rules/
│   └── metadata_rules.yaml  # 可配置规则引擎
└── scripts/
    └── batch_ingest.py      # 批量入库 CLI
```

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Qdrant（Docker）

```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 3. 启动后端

```bash
cd rag_backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

访问 http://localhost:8000/docs 查看交互式 API 文档。

### 4. 启动 MCP Server（供 Claude Code 调用）

```bash
cd rag_backend
python mcp_server.py
```

说明：MCP Server 使用 `stdio` 传输，不对外暴露 HTTP 端口；通常由 `.mcp.json` 自动拉起，手动启动主要用于本地调试。

## 批量入库往年文档

```bash
# 整目录入库
python scripts/batch_ingest.py --dir ./往年作业 --term 春季 --year 2024

# 单文件入库，手动指定 project_id
python scripts/batch_ingest.py --file ./需求规格说明书.pdf --project_id projA --term 夏季

# 输出报告到 JSON
python scripts/batch_ingest.py --dir ./往年作业 --report report.json
```

## API 接口

### 上传文档

```
POST /api/upload
Content-Type: multipart/form-data

file      : PDF 文件（必填）
project_id: 项目 ID（可选，自动推断）
term      : 春季/夏季（可选，自动推断）
year      : 年份（可选，自动推断）
```

### 检索

```
POST /api/search
Content-Type: application/json

{
  "query": "用户登录接口设计",
  "term": "春季",
  "phase": "design",
  "doc_type": "概要设计",
  "quality_level": ["high"],
  "use_reranker": true
}
```

返回按瀑布阶段排序的结果列表，每条含 `why_hit` 命中原因。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `QDRANT_HOST` | localhost | Qdrant 地址 |
| `QDRANT_PORT` | 6333 | Qdrant 端口 |
| `QDRANT_COLLECTION` | se_course_docs | Collection 名 |
| `EMBED_MODEL` | BAAI/bge-m3 | Embedding 模型 |
| `EMBED_BATCH_SIZE` | 16 | 批量 embedding 大小 |
| `EMBED_PROVIDER` | local_bge | `local_bge` / `openai_compatible` |
| `OPENAI_BASE_URL` | 空 | OpenAI 兼容接口地址（如 `https://api.apiyi.com/v1`） |
| `OPENAI_API_KEY` | 空 | OpenAI 兼容接口密钥（也兼容 `APIYI_API_KEY` / `API_KEY`） |
| `OPENAI_EMBED_MODEL` | text-embedding-3-small | embedding 模型名 |
| `OPENAI_EMBED_DIMENSIONS` | 空 | 可选：部分模型支持自定义向量维度 |
| `OPENAI_EMBED_DIM` | 1536 | provider 为 openai 时默认向量维度 |

## 使用 OpenAI 兼容 Embedding（apiyi 示例）

在 `rag_backend/.env` 中设置：

```env
EMBED_PROVIDER=openai_compatible
OPENAI_BASE_URL=https://api.apiyi.com/v1
OPENAI_API_KEY=YOUR_API_KEY
OPENAI_EMBED_MODEL=text-embedding-3-small
# 可选：OPENAI_EMBED_DIMENSIONS=1536
```

### 先用 curl 验证接口可用

```bash
curl https://api.apiyi.com/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "input": "人工智能正在改变世界",
    "model": "text-embedding-3-small"
  }'
```

### 用 OpenAI SDK 做最小验证

```python
from openai import OpenAI

client = OpenAI(api_key="YOUR_API_KEY", base_url="https://api.apiyi.com/v1")
resp = client.embeddings.create(
    input=["人工智能正在改变世界", "深度学习推动了AI的发展"],
    model="text-embedding-3-small",
)
print(len(resp.data), len(resp.data[0].embedding))
```

项目内 `vectordb/embedder.py` 已按同样方式接入，`pipeline/ingest.py` 会自动批量调用 embedding 接口。配置完成后直接走上传或批量入库即可。
