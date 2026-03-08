---
name: se-project-management-doc-assistant
description: 专项生成软件工程实践课程“项目管理文档”，适配夏季模板，强调迭代过程、任务追踪、分支策略、缺陷管理与过程复盘。用于将项目管理证据整理成结构化课程文档。
---

# SE Project Management Doc Assistant

专门面向夏季 `项目管理文档` 的写作与证据组织。

## Overview

专门面向夏季 `项目管理文档` 的写作与证据组织。

### 适用模板

- `assets/项目管理文档.md`
- 可联动：`assets/人员分工权重.md`、`assets/项目总结.md`

### 目标

- 清晰呈现迭代时间线（Day/Iteration）
- 说明需求、任务、缺陷如何被管理
- 证明仓库分支与项目进展一致
- 保留失败与风险，不粉饰过程

### 输入证据建议

- 看板/任务平台截图或导出数据
- Git 分支与提交历史
- 版本发布记录
- 缺陷清单与修复记录

## Workflow

### 1. 迭代过程记录

按 Day 或迭代维度：
- 确定本期目标
- 梳理已完成内容与未完成项
- 记录遇到的阻塞项与对应对策

### 2. 建立任务链路

构建“需求-任务-提交-缺陷”追踪链：
- 需求编号 → 关联任务 → 关键提交记录 → 发现的缺陷记录

### 3. 代码仓库治理说明

明确以下内容并验证一致性：
- 分支策略与合并规则
- 版本命名规则
- 紧急回滚策略

### 4. 过程复盘与持续改进

- 总结做得好的工程实践
- 分析主要失误与根本原因
- 提出具体的下一轮改进项

### 质量标准与写作规范

- **真实性**：时间线必须与 Git/看板事实一致。
- **证据链**：每个关键结论（如“已完成”）必须有具体证据支撑。
- **透明度**：不粉饰太平，缺陷与风险必须具体且可追踪。
- **落地性**：复盘建议必须是可执行的操作，而非空话。

## Examples

[TODO: Usage examples]

## Resources

### scripts/
- Executable code for automation and deterministic tasks

### references/
- Documentation and reference materials

### assets/
- Templates, boilerplate files, or static assets
