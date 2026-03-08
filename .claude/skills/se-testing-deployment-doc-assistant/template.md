# SE Testing & Deployment Template Fragment

[TODO: Use this fragment for standardized testing reports and deployment steps]

## 1. 测试用例执行摘要 [TC-XXXX]
- **关联需求**: [REQ-XXXX]
- **测试环境**: [OS/Browser/Backend version]
- **执行结果**: [Pass/Fail/Blocked]
- **实际表现**: [描述观察到的现象, 可附加 Log 片段]

## 2. 缺陷闭环记录 [BUG-XXXX]
- **问题描述**: [简述复现路径]
- **严重级别**: [P0-P3]
- **修复措施**: [代码变动或配置修正]
- **回归情况**: [通过验证的具体 Commit Hash]

## 3. 部署操作手册 (Step-by-Step)
1. **基础环境**: Ensure Node.js v18+/Python 3.10+ installed.
2. **依赖安装**: `npm install` or `pip install -r requirements.txt`
3. **配置注入**: Copy `.env.example` to `.env` and set `DB_URL`.
4. **启动与验证**: Run `npm start`, check `http://localhost:3000/health`.
5. **回滚操作**: `git checkout vX.Y.Z && docker-compose up -d`

## 4. 用户 FAQ 手段
- **Q**: 无法连接数据库
- **A**: 检查 `.env` 中的 `DB_HOST` 是否配置为 `localhost` 而非内网 IP。
