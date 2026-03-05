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

### 删除文档（联动删除 MinIO + Qdrant）

```
DELETE /api/files/{object_name}
```

说明：
- `object_name` 为 MinIO 对象名，格式通常为 `document_id/原文件名`；
- 接口会先删除 Qdrant 中 `source_file == object_name` 的所有 chunk；
- 再删除 MinIO 中对应原始文件；
- 返回删除统计：`qdrant_deleted`、`minio_deleted`。

返回示例：

```json
{
  "success": true,
  "object_name": "550e8400-e29b-41d4-a716-446655440000/需求规格说明书.pdf",
  "qdrant_deleted": 42,
  "minio_deleted": true,
  "errors": []
}
```

### 文件重名与主键策略

- 每次上传都会生成 `document_id(UUID)` 作为文档主键；
- MinIO 对象键采用 `document_id/原文件名`，同名文件不会覆盖；
- 入库时每个切片生成 `chunk_uuid(UUID)` 并写入 payload；
- Qdrant point id 采用 `chunk_uuid`，确保切片级主键稳定可追踪。

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

## 文档解析策略

本项目采用“解析 → 分块 → 元数据生成 → 向量化入库”的流水线策略，核心目标是：
- 保留章节结构，减少语义断裂；
- 通过 metadata 让后续检索可控（可过滤、可解释、可追踪）；
- 在不依赖大模型的情况下完成稳定的自动标注。

### 1) 多格式解析（PDF / DOCX / Markdown）

- `PDF`：优先使用 `pdfplumber` 按行提取（含字体信息），基于字体大小与粗体推断 Markdown 标题层级（`#` 到 `####`）。
- `PDF` 兜底：若 `pdfplumber` 失败，自动降级到 `PyMuPDF(fitz)` 继续解析。
- `DOCX`：按段落提取，识别 `Heading/标题 1-3` 转换为 Markdown 标题；每 60 行切分为“虚拟页”。
- `Markdown`：按 H1/H2 标题切分为“虚拟页”。
- 统一去噪：移除课程模板噪声行（如“本条应...”“最终文档请删除”“TOC”等）。

### 2) 两层分块策略（结构优先 + 语义优先）

第一层（结构切块）：
- 按 Markdown 标题边界切分；
- 额外识别“小结/总结/结论”边界，避免跨模块语义串扰。

第二层（语义切块）：
- 在结构块内按 `CHUNK_MIN_CHARS / CHUNK_MAX_CHARS / CHUNK_OVERLAP_CHARS` 进行滑窗切分；
- 优先在自然语句边界（句号、分号、换行）断开；
- 对“表格/编号条目/代码块”等特殊内容整块保留，避免破坏结构。

每个 chunk 保留：
- `text`：块文本；
- `section_path`：标题路径（用于检索解释与规则推断）；
- `chunk_index`：文档内顺序编号。

### 3) Metadata 自动生成（规则优先）

`pipeline/metadata.py` 使用规则与启发式生成字段：
- 路径/文件名规则：`year`、`term`、`doc_type`、`phase`、`project_id`；
- 内容规则：`artifact_type`、`evidence_type`、`status`；
- 编号抽取：`req_ids/design_ids/test_ids/impl_refs`；
- 链路信息：从同块编号关系构造 `trace_links`（用于连续性扩展）；
- 质量分级：按“编号/指标/代码块/表格 + 长度”启发式输出 `high/medium/low`。

同时计算 `_confidence_overall`，低于 `CONFIDENCE_THRESHOLD` 或缺少关键字段时标记 `_needs_review=true`。

### 4) 入库与校验

- 向量化后写入 Qdrant，payload 包含完整 metadata；
- 入库报告输出：`chunks_total/chunks_inserted/needs_review_count/coverage`；
- 启动时自动检查 collection 维度，不一致时自动重建，避免 provider 切换后写入失败。

## 查询策略

检索采用“硬过滤 + 混合召回 + 可选重排 + 连续性扩展 + 综合评分 + 阶段排序”。

### 1) 输入归一化

`/api/search` 会将 Swagger 占位值与空值归一化，避免误过滤：
- `"string" / "none" / "null" / ""` 视为未传；
- `quality_level` 自动清洗无效项。

### 2) Query 向量化

- 通过 `embed_query()` 生成查询向量；
- 当前支持两类 embedding provider：
  - `local_bge`：本地 BGE-M3（dense+sparse）；
  - `openai_compatible`：OpenAI 兼容 API（当前默认仅 dense，sparse 为空）。

### 3) 硬过滤（Metadata Filter）

在召回前先用 Qdrant `Filter` 做精确过滤：
- `term/phase/doc_type/project_id/artifact_type`（等值）；
- `quality_level`（`MatchAny`）。

过滤命中 0 时会直接返回空，属于预期行为。

### 4) 混合召回（Dense + Sparse）

优先路径：
- 使用 Qdrant `prefetch + Fusion(RRF)` 融合 dense/sparse 两路候选；
- 候选数由 `TOPK_RECALL` 控制。

降级路径：
- 若融合查询异常，自动回退到 dense-only 检索，不中断请求。

### 5) 可选重排（Reranker）

- `use_reranker=true` 且 `RERANK_ENABLED=true` 时，才执行 cross-encoder 重排；
- 当前默认：`openai_compatible` 下 `RERANK_ENABLED=false`，避免额外本地模型加载；
- 若重排模型不可用，自动降级为仅向量召回，不抛 500。

### 6) 连续性扩展（Trace Expansion）

对 top 候选的一部分读取 `trace_links`，沿 `req_ids` 做跨块补链，提升“需求→设计→实现→测试”链路完整性。

### 7) 综合评分与可解释输出

每条结果计算：

`Score = 0.60 * Sim + 0.25 * MetaMatch + 0.15 * Continuity`

- `Sim`：语义相似度（或重排分）；
- `MetaMatch`：过滤字段命中率；
- `Continuity`：是否含 `trace_links/req_ids`。

返回中附带 `why_hit`：
- `why_semantic_score`
- `why_metadata_match`
- `why_continuity`

最终按阶段顺序输出（`requirement → design → implementation → testing_deployment`），同阶段按综合分降序。

### 8) 性能建议（实践）

- API embedding 模式下，请求耗时主要在外部向量接口；
- 首次请求有冷启动开销（模块导入、客户端初始化）；
- 可通过关闭重排、减少过滤、增加缓存、改本地 embedding 模式优化时延。

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
