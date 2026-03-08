# SE Course RAG Backend API 接口文档

本项目为软件工程课程 RAG（检索增强生成）系统后端，基于 FastAPI 构建，提供文档解析、向量化入库及多维混合检索功能。

## 基础信息
- **Base URL**: `http://localhost:8000` (或实际部署地址)
- **Content-Type**: `application/json` (除上传接口外)

---

## 1. 系统健康检查
`GET /health`

确认后端服务及数据库连接状态。

**响应示例**:
```json
{
  "status": "ok"
}
```

---

## 2. 文档入库 (Ingestion)

### 2.1 批量上传与入库 (推荐)
`POST /api/batch`

支持将同一项目下的多个文档批量解析并入库。系统会自动完成 Markdown 转换、表格提取、图片语义标记及项目特征识别。

**请求参数 (Multipart/Form-Data)**:
- `files`: 多文件列表 (支持 `.pdf`, `.docx`, `.md`)
- `project_id`: **[建议]** 项目唯一标识符（如 `2024-group12-oj`）
- `term`: [可选] 课程学期 (如 `春季` / `夏季`)
- `year`: [可选] 课程年份

**响应示例**:
```json
{
  "project_id": "2024-group-01",
  "files": [
    {
      "filename": "需求规格说明书.pdf",
      "status": "ok",
      "chunks_ingested": 42,
      "metadata": {
        "is_arch": false,
        "is_biz": true,
        "p_id": "2024-group-01"
      }
    },
    ...
  ]
}
```

### 2.2 单文件上传
`POST /api/upload`

**请求参数 (Multipart/Form-Data)**:
- `file`: 单个文件对象
- `project_id`: [可选] 若不提供，后端将尝试基于文件名/内容自动识别
- `term` / `year`: [可选] 课程筛选维度

---

## 3. 文档检索 (Search)

### 3.1 混合检索 (Dense + Sparse + Rerank)
`POST /api/search`

执行高精度检索。采用 BGE 密集向量检索 + BM25 稀疏向量检索，并通过 Reranker 交叉验证评分。

**请求体 (JSON)**:
```json
{
  "query": "登录模块的数据库设计",
  "project_id": "2024-group-01",
  "phase": "design",
  "artifact_type": "interface",
  "use_reranker": true
}
```

**参数说明**:
- `query` (str): **[必填]** 自然语言查询语句。
- `project_id` (str): [可选] 限制查询某个特定项目的内容。
- `phase` (str): [可选] 阶段过滤 (`requirement` / `design` / `implementation` / `testing_deployment`)。
- `quality_level` (list[str]): [可选] 例 `["high"]` 仅检索优秀范例。
- `use_reranker` (bool): 默认为 `true`。设为 `false` 可提升响应速度但可能降低相关性。

**响应示例**:
```json
[
  {
    "text": "#### 3.2 用户登录接口设计\n用户通过 POST /api/login 提交凭据...",
    "metadata": {
      "p_id": "2024-group-01",
      "is_arch": true,
      "source_file": "详细设计说明书.docx"
    },
    "composite_score": 0.92,
    "why_hit": {
      "semantic_sim": 0.85,
      "keyword_overlap": 0.1,
      "context_boost": 1.2
    }
  }
]
```

---

## 4. 管理接口

### 4.1 已备份文件列表
`GET /api/files`

获取 MinIO 中存储的原始文档列表及其最后修改时间。用于维护追踪。

---

## 5. 错误处理规范
API 采用标准 HTTP 状态码：
- `200 OK`: 请求成功。
- `400 Bad Request`: 参数校验失败（如文件格式不支持）。
- `404 Not Found`: 资源不存在。
- `500 Internal Server Error`: 后端逻辑或数据库异常（详情见 `detail` 字段）。

---

> **注意**: 
> 1. 上传 PDF 时，后端会自动识别并使用流水线提取**表格数据**，转换为 Markdown 格式存储。
> 2. 检索逻辑具备“**自动松弛 (Relaxation)**”特性：如果带 project_id 的检索结果不足，会自动退回全局检索以确保结果召回率。
