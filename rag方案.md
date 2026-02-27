# 软件工程课程历史文档 RAG / Embedding 方案（Agent 调用规范）

> 目标：让学生在同一项目上体现“瀑布式阶段连续性”，并能从往年文档中检索到**同阶段可借鉴内容**和**跨阶段可追踪证据**。

## 1. 设计原则

- **连续性优先**：同一项目的需求→设计→实现→测试部署要能串起来检索。
- **模板一致性优先**：所有生成内容必须贴合课程模板章节，避免格式漂移。
- **证据优先**：优先召回含事实证据（接口、测试结果、缺陷、提交记录）的段落。
- **可过滤优先**：向量块必须带结构化标签，不能“裸文本入库”。

## 2. 入库对象与清洗

### 2.1 入库对象

- 往年作业文档（春季/夏季模板下全部 md/docx 转 md）
- 可选扩展：项目 README、测试报告、部署说明、迭代记录

### 2.2 文本清洗规则

- 删除模板说明性噪声（如“灰色说明文字”“最终请删除本段”等）
- 统一标题层级（`#`/`##`/`###`）并保留章节路径
- 将表格转为行文本（保留列名）
- 图片内容采用 OCR/图注摘要（若无 OCR，至少保留图片标题与上下文）
- 统一术语（如“需求规格说明书/SRS”映射为同义词集合）

## 3. 分块（Chunking）策略

采用“**结构分块 + 语义二次切分**”两层策略：

### 3.1 第一层：按章节结构切块

- 以模板标题为主边界：文档 > 章节 > 小节
- 每块保留：`doc_title`、`section_path`（例如 `3.4 CSCI能力需求 > 3.4.2 用户管理`）

### 3.2 第二层：按语义长度切块

- 单块建议：`300~700` 中文字（或约 `250~450` tokens）
- 重叠建议：`60~120` 中文字（或约 `40~80` tokens）
- 切分优先在自然边界（句号、分号、列表项）处断开

### 3.3 特殊块处理

- 表格、用例、接口定义、需求编号列表单独成块
- 包含“编号体系”（FR/NFR/IF/TC）的内容单独成块并提取编号标签

## 4. 向量块标签（Metadata Tags）规范

每个 chunk 必须携带以下标签：

### 4.1 基础标签（必填）

- `course`: 软件工程实践
- `year`: 年份（如 2024）
- `term`: 春季/夏季
- `project_id`: 项目标识（同一项目唯一）
- `project_name`: 项目名
- `doc_type`: 需求/概要设计/详细设计/开发计划/项目管理/测试报告/用户手册/项目总结
- `phase`: requirement/design/implementation/testing_deployment
- `section_path`: 章节路径
- `chunk_id`: 块唯一 ID

### 4.2 教学语义标签（强烈建议）

- `artifact_type`: goal/requirement/interface/data_model/module/design_decision/implementation/test_case/defect/deployment/risk/summary
- `status`: planned/in_progress/done/blocked
- `quality_level`: high/medium/low（可由规则或模型打分）
- `evidence_type`: narrative/table/metric/screenshot/code_ref/log

### 4.3 连续性标签（关键）

- `req_ids`: [FR-001, NFR-003 ...]
- `design_ids`: [SD-xx ...]
- `impl_refs`: [module/service/api 名称]
- `test_ids`: [TC-xxx]
- `trace_links`: [{from:req_id, to:design_id/test_id/impl_ref}]
- `prev_phase_chunk_ids`: 上游阶段相关 chunk
- `next_phase_chunk_ids`: 下游阶段相关 chunk

## 5. 向量模型与索引建议

### 5.1 Embedding 模型

中文场景建议优先：
- `bge-m3`（支持 dense/sparse/multi-vector，适合混合检索）

备选：
- 云端通用 embedding（若已有平台规范）

### 5.2 检索模式

- **混合检索**：Dense + BM25（或 sparse）
- **重排**：Cross-encoder reranker（如 `bge-reranker-v2-m3`）
- **元数据过滤**：先按 `term + phase + doc_type` 过滤，再向量召回

### 5.3 索引组织

- 逻辑上按 `term/year` 分区
- 同一 `project_id` 建立“连续性图谱索引”（关系边）
- 高频字段（`phase/doc_type/project_id`）建立可过滤索引

## 6. 检索与组装流程（面向 Agent）

1. **意图识别**：判断当前在写哪个阶段、哪种文档
2. **过滤条件生成**：`term + doc_type + phase`，可附加 `project_type`
3. **候选召回**：TopK（建议 30~60）
4. **重排**：取前 8~15 个高相关块
5. **连续性扩展**：沿 `trace_links/prev_phase_chunk_ids` 补 3~5 个跨阶段证据块
6. **上下文组装**：按“需求→设计→实现→测试部署”顺序拼接，避免断层

## 7. 生成约束（防止格式不统一）

- 输出必须映射到课程模板章节，不得自创章节体系
- 每个关键结论尽量附“来源块标识”（`project_id + doc_type + section_path`）
- 严禁照抄整段往年文本；采用“提炼结构 + 重写内容”
- 对无法验证的数据标注“待确认”，不编造

## 8. 评估指标

- `Recall@K`：是否能召回对应阶段高质量样例
- `ContinuityScore`：同一主题跨阶段链路完整度
- `TemplateAlignment`：输出与模板章节匹配率
- `ContradictionRate`：跨块信息冲突率

## 9. 建议的数据结构（示例）

```json
{
	"chunk_id": "2024-summer-projA-req-3.4.2-001",
	"text": "...",
	"metadata": {
		"course": "软件工程实践",
		"year": 2024,
		"term": "夏季",
		"project_id": "projA",
		"project_name": "智能教学平台",
		"doc_type": "项目管理文档",
		"phase": "implementation",
		"section_path": "项目迭代开发过程 > Day 03",
		"artifact_type": "implementation",
		"status": "done",
		"req_ids": ["FR-003"],
		"impl_refs": ["UserController", "TaskService"],
		"test_ids": ["TC-021"],
		"trace_links": [{"from": "FR-003", "to": "TC-021"}]
	}
}
```

## 10. 在 Skills 中的使用约定

- 所有课程文档类 skills 必须显式声明“遵循本文件规范”
- 默认先做 metadata 过滤再做向量召回
- 输出中给出“参考来源分布”（按 phase/doc_type 统计）

## 11. Metadata 与检索判定细则（关键补充）

### 11.1 Metadata 是否影响向量值

- **默认不影响**：embedding 只对 `text` 字段计算，`metadata` 不进入向量编码。
- `metadata` 主要用于：过滤（filter）、召回后打分（boost）、结果解释（why hit）。
- **不建议**将 metadata 直接拼进正文再计算向量，否则会污染语义空间。

### 11.2 什么时候会“间接影响”

以下做法会改变向量值（需谨慎）：

- 把 `phase/doc_type/project_id` 等标签串接到 chunk 正文后再 embedding。
- 使用“文本模板化前缀”（如 `这是需求阶段文档：...`）统一加在正文前。

建议：标签走 metadata 字段，文本保持自然语义。

### 11.3 检索时如何判断“这是我需要的”

采用三段式判定：

1. **硬过滤（必须命中）**：`term + phase + doc_type`（必要时加 `project_id`）
2. **语义相关（向量相似度）**：在过滤后的候选集里做 dense/sparse 混合召回
3. **业务重排（课程连续性）**：优先有 `req_ids/test_ids/trace_links` 的块

### 11.4 推荐综合评分公式

可使用线性加权：

$$
Score = 0.60 \cdot Sim + 0.25 \cdot MetaMatch + 0.15 \cdot Continuity
$$

- `Sim`：向量/混合检索相似度（归一化到 0~1）
- `MetaMatch`：标签匹配分（phase、doc_type、artifact_type、quality_level）
- `Continuity`：是否能连接上下游阶段（`trace_links`、`prev/next_phase_chunk_ids`）

可按阶段调权：
- 需求/设计阶段：提高 `MetaMatch`
- 实现/测试阶段：提高 `Continuity`

### 11.5 结果解释（可观测性）

每条返回结果建议附命中原因：

- `why_semantic`: 与查询语义最接近的关键词或句子
- `why_metadata`: 命中的关键标签（如 `phase=design`）
- `why_continuity`: 关联的上/下游编号（如 `FR-003 -> TC-021`）

### 11.6 课程场景默认检索模板

```yaml
must_filter:
	term: 夏季|春季
	phase: requirement|design|implementation|testing_deployment
	doc_type: 对应阶段文档类型

optional_boost:
	quality_level: high
	evidence_type: metric|code_ref|log
	artifact_type: 当前写作目标类型

retrieve:
	topk_recall: 50
	topk_rerank: 12
	continuity_expand: 4
```

## 12. Metadata 自动生成方案（无需手工逐条标注）

### 12.1 总体思路

采用“**规则优先 + 模型补全 + 校验回写**”三阶段流水线：

1. **规则抽取（高精度）**：从文件路径、文档标题、章节号、编号模式中直接提取 metadata
2. **模型补全（补召回）**：对规则无法确定的字段，用轻量分类/抽取模型推断
3. **一致性校验（降风险）**：跨字段校验与置信度评估，不达标的进入人工复核队列

### 12.2 自动抽取字段分层

#### A. 可 100% 规则抽取字段（优先）

- `year`: 从目录名/文件名正则提取（如 `2024`）
- `term`: 从路径命中 `春季|夏季`
- `doc_type`: 由文件名映射（如“软件需求规格说明书”→`需求`）
- `phase`: 由 `doc_type` 映射（需求→requirement，测试报告→testing_deployment）
- `section_path`: 由 Markdown 标题栈生成
- `chunk_id`: `year-term-project_id-doc_type-section-hash`

#### B. 半规则抽取字段（规则 + 词典）

- `artifact_type`: 根据章节关键词映射（如“接口/API”→`interface`）
- `status`: 通过关键词判定（已完成/进行中/未完成/阻塞）
- `evidence_type`: 根据内容特征判定（表格、日志、指标、代码引用）

#### C. 需模型推断字段（可选）

- `quality_level`: 由质量打分模型给出 high/medium/low
- `project_name`: 多文档聚类后统一命名
- `impl_refs`: 从代码标识符抽取（类名/服务名/API 路径）

### 12.3 规则引擎建议

使用 `YAML/JSON` 规则文件驱动，避免把规则写死在代码里。

```yaml
doc_type_rules:
	- pattern: "软件需求规格说明书|SRS"
		doc_type: "需求"
		phase: "requirement"
	- pattern: "软件概要设计说明书|概要设计"
		doc_type: "概要设计"
		phase: "design"
	- pattern: "测试报告"
		doc_type: "测试报告"
		phase: "testing_deployment"

artifact_rules:
	- pattern: "接口|API|通信"
		artifact_type: "interface"
	- pattern: "数据库|数据结构|ER"
		artifact_type: "data_model"
	- pattern: "用例|测试|断言"
		artifact_type: "test_case"
```

### 12.4 编号与链路自动提取

- `req_ids`：正则 `FR-\\d+|NFR-\\d+|IF-\\d+`
- `design_ids`：正则 `SD-\\d+|DES-\\d+`
- `test_ids`：正则 `TC-\\d+|TEST-\\d+`
- `trace_links` 生成逻辑：同一 chunk 或同一 section 内出现 `req_id` 与 `test_id/design_id/impl_ref` 即建立边

建议在文档级建立反向索引：
- `id -> chunk_ids`
- 用于后续补全 `prev_phase_chunk_ids/next_phase_chunk_ids`

### 12.5 置信度与人工复核策略（低成本）

每个字段记录 `confidence`：

- 规则命中：`0.95~1.0`
- 模型预测：`0.60~0.90`
- 冲突修正后：`<=0.70`

进入人工复核条件（仅少量）：

- 必填字段缺失（`term/doc_type/phase/project_id`）
- `doc_type` 与 `phase` 冲突
- 编号链路异常（如测试块无任何可追踪来源）
- 总体置信度低于阈值（建议 `0.75`）

### 12.6 最小实现流水线（建议）

1. 文档转 markdown + 清洗
2. 结构分块（带 `section_path`）
3. 规则抽取 metadata
4. 模型补全缺失字段
5. 约束校验 + 冲突修复
6. 写入 `jsonl`（`text + metadata + confidence`）
7. 向量化入库（仅 `text` 计算 embedding）

### 12.7 入库前校验清单（自动化）

- 必填字段完整率 >= 99%
- `doc_type -> phase` 映射正确率 >= 99%
- `section_path` 非空率 = 100%
- 编号提取命中率（FR/NFR/TC）可观测
- 抽样 5% 人审通过率 >= 95%

### 12.8 推荐输出 JSONL 结构

```json
{"text":"...","metadata":{"term":"夏季","phase":"design","doc_type":"概要设计","section_path":"2.7 系统总体架构","project_id":"projA"},"confidence":{"doc_type":0.99,"artifact_type":0.83}}
```
