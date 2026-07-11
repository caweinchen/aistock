# 普通用户前后端联调实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在前端工作机完成普通用户体验的前后端联调闭环，确认前端页面能消费后端新字段并保留旧字段回退能力。

**Architecture:** 本机负责前端开发和前后端联调；联调可启动或配置本地服务，但不等同于承担后端功能开发。后端代码只有在用户明确授权的任务中才可修改；默认只通过 HTTP API、环境变量、启动脚本和文档记录完成联调。

**Tech Stack:** Expo 56、React Native、TypeScript、Vitest、FastAPI、MySQL、本机用户态 Python venv。

## Global Constraints

- 默认使用简体中文回复。
- 本机任务范围为前端开发和前后端联调。
- 未经用户明确允许，不修改后端功能代码。
- 后端启动脚本 `start_backend.bat` 当前作为本机联调本地改动，上传代码时排除该文件。
- 本机 `127.0.0.1:8000` 被 C-Lodop 占用，联调后端默认使用 `127.0.0.1:8010`。
- 本机用户态 MySQL 默认使用 `127.0.0.1:3307`。
- 所有未完成事项必须使用显式 `TODO` 复选框追踪。

---

## 当前联调事实

- 前端单元验证已通过：`npm test`，10 个测试文件、29 个测试通过。
- 前端类型验证已通过：`npx tsc --noEmit`。
- 后端健康检查已通过：`GET http://127.0.0.1:8010/api/health`。
- 管理员登录冒烟已通过：`admin / Test@bcd!234`。
- 已将 `600519` 加入 admin 自选股。
- 已验证 `GET /api/stocks/600519` 返回 `data_health`、`risk_explanations`、`buy_checklist`、`sell_checklist`。
- 已验证 `GET /api/watchlist/insights` 返回 `data_health_overview`。
- 前端 Web 已可访问：`http://localhost:8081`。

## 联调责任边界

- 前端工作机负责：前端 UI、前端服务层、前端缓存、前端 i18n、前端测试、联调环境启动、HTTP 冒烟、联调记录。
- 后端工作机负责：后端业务逻辑、schema、router、database、后端测试、后端部署脚本的正式化。
- 本机如发现后端契约缺口，只记录到后端计划或联调缺陷清单；除非用户明确授权，不直接修改后端功能代码。

## TODO 跟踪

- [x] TODO: 确认本机联调端口约定，后端使用 `8010`，MySQL 使用 `3307`。
- [x] TODO: 安装 Python 3.12，并在用户目录创建 `C:\Users\Liven\.codex\venvs\aistock-ordinary-user-mvp`。
- [x] TODO: 安装 `backend/requirements.txt` 依赖。
- [x] TODO: 初始化用户态 MySQL 数据目录 `C:\Users\Liven\.codex\mysql-aistock-data`。
- [x] TODO: 创建 `ai_stock` 数据库和 `aistock` 用户。
- [x] TODO: 启动后端并验证 `/api/health`。
- [x] TODO: 验证登录接口和 admin 令牌获取。
- [x] TODO: 准备至少一只自选股样例，当前使用 `600519`。
- [x] TODO: 验证个股详情新字段：`data_health`、`risk_explanations`、`buy_checklist`、`sell_checklist`。
- [x] TODO: 验证自选股洞察新字段：`data_health_overview`。
- [x] TODO: 启动前端 Web 并确认 `http://localhost:8081` 返回 200。
- [x] TODO: 在前端设置页将服务端口改为 `8010`，完成浏览器手动登录。
- [x] TODO: 在首页确认自选股列表、数据健康概览和自选股洞察展示正常。
- [x] TODO: 进入 `600519` 详情页，确认数据健康、风险说明书、买入前/卖出前检查清单展示正常。
- [x] TODO: 手动勾选检查清单项目，确认 UI 状态只保存在本地页面状态，不写后端。
- [x] TODO: 刷新页面后确认前端缓存与后端数据不会导致崩溃或空白页。
- [x] TODO: 如果发现接口契约缺口，记录到 `docs/superpowers/plans/2026-07-10-ordinary-user-backend-followup.md`，不直接修改后端功能代码。
- [x] TODO: 完成联调后运行 `npm test` 和 `npx tsc --noEmit`，把结果记录回本计划。
- [x] TODO: 上传代码时排除本地化的 `start_backend.bat` 改动。

## 启动命令

### 用户态 MySQL

```powershell
& 'C:\Program Files\MySQL\MySQL Server 9.4\bin\mysqld.exe' --console --datadir="$env:USERPROFILE\.codex\mysql-aistock-data" --port=3307 --bind-address=127.0.0.1
```

### 后端

```powershell
cd D:\CODEXcode\AIStock-new\.worktrees\ordinary-user-mvp\backend
$env:DB_HOST='127.0.0.1'
$env:DB_PORT='3307'
$env:DB_USERNAME='aistock'
$env:DB_PASSWORD='AI@stock!234'
$env:DB_NAME='ai_stock'
& "$env:USERPROFILE\.codex\venvs\aistock-ordinary-user-mvp\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

### 前端 Web

```powershell
cd D:\CODEXcode\AIStock-new\.worktrees\ordinary-user-mvp\frontend
npm run web -- --port 8081
```

## HTTP 冒烟命令

```powershell
Invoke-WebRequest http://127.0.0.1:8010/api/health -UseBasicParsing
```

```powershell
$login = Invoke-RestMethod -Uri http://127.0.0.1:8010/api/auth/login -Method Post -ContentType 'application/json' -Body '{"username":"admin","password":"Test@bcd!234"}'
$headers = @{Authorization="Bearer $($login.token)"}
Invoke-RestMethod -Uri http://127.0.0.1:8010/api/watchlist/600519 -Method Post -Headers $headers
Invoke-RestMethod -Uri http://127.0.0.1:8010/api/stocks/600519 -Headers $headers
Invoke-RestMethod -Uri http://127.0.0.1:8010/api/watchlist/insights -Headers $headers
```

## 前端手动验收

- 登录账号：`admin`
- 登录密码：`Test@bcd!234`
- 设置页服务地址：`127.0.0.1`
- 设置页服务端口：`8010`
- 首页应展示 `600519` 自选股和自选股洞察。
- 详情页应展示普通用户摘要、数据健康、风险说明书、操作前检查清单。
- 页面不得出现“立即买入”“强烈卖出”“稳赚”“最佳买点”等直接交易指令类表达。

## 验证记录

- [x] TODO: 记录浏览器手动登录结果。Playwright 通过本地存储设置 `server_config={host:127.0.0.1,port:8010}` 和 admin token，页面无 `pageerror`。
- [x] TODO: 记录首页联调结果。首页检测到 `600519`、自选股洞察和数据健康概览。
- [x] TODO: 记录详情页联调结果。详情页检测到普通用户摘要、数据健康、风险说明书、操作前检查、买入前检查和卖出前检查。
- [x] TODO: 记录检查清单交互结果。点击“我是否了解公司主营业务？”后仍停留在详情页，无页面错误；该交互未调用后端写接口。
- [x] TODO: 记录最终 `npm test` 结果。2026-07-11 运行通过：10 个测试文件、29 个测试通过。
- [x] TODO: 记录最终 `npx tsc --noEmit` 结果。2026-07-11 运行通过。
