# 示例：从 Git Log 到开发进展记录

本示例演示如何将原始 Git 信息转化为课程文档要求的“实施计划与执行对比”。

## 原始证据 (Git Log)
```bash
commit a1b2c3d (HEAD -> feature/F123-user-login)
Author: Student A <student-a@example.com>
Date:   Wed Mar 1 10:00:00 2026 +0800
    feat: 实现 JWT 登录认证，处理 Token 过期逻辑

commit e4f5g6h
Author: Student A <student-a@example.com>
Date:   Tue Feb 28 15:30:00 2026 +0800
    fix: 修复 Redis 缓存击穿问题，增加分布式锁
```

## 文档转换结果 (推荐写入内容)
### 软件开发计划-执行对比
| 计划任务 (REQ-123 用户登录) | 实际状态 | 对应代码/证据 | 备注 |
| :--- | :--- | :--- | :--- |
| **功能开发** | 已完成 | `src/auth/jwt.py` | 实现了双 Token (Access/Refresh) 刷新机制 |
| **安全加固** | 已完成 | `src/middleware/redis_lock.py` | 针对登录接口的高并发请求增加了分布式锁 |

### 个人权重说明 (Student A)
- **核心贡献**: 负责认证模块开发，解决关键技术难点（Redis 击穿、JWT 安全刷新）。
- **工作量统计**: 提交 15 次，完成代码量 ~800 行。
- **自评权重**: 1.1 (承担高难度模块开发)
