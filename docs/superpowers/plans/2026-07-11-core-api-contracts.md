# 核心 API 契约补齐实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为前端当前使用的四个核心后端域补齐稳定、可验证的 API 契约。

**Architecture:** 以 FastAPI OpenAPI 为机器可读字段源，按业务域维护 Markdown 语义契约；README 统一认证、错误和兼容规则。契约只记录当前行为，不改运行时代码。

**Tech Stack:** FastAPI OpenAPI、Markdown、PowerShell、ripgrep

## Global Constraints

- 只修改契约、规格、计划和协作看板文档。
- 不修改、格式化、暂存或提交 `frontend/**`。
- 不改变 API 路径、认证、错误码、响应字段或数据语义。
- 所有未完成事项使用显式 TODO 复选框。

---

### Task 1: 契约总则与认证域

**Files:**
- Modify: `docs/contracts/README.md`
- Create: `docs/contracts/auth.md`

- [x] **Step 1:** 在 README 记录 Bearer 认证、FastAPI 错误体、兼容性定义和四个域索引。
- [x] **Step 2:** 记录 `/api/auth/public-key`、`login`、`register`、`verify`、`change-password`、`validate-password`、`generate-password` 的请求、响应和错误。
- [x] **Step 3:** 使用 `rg -n '/api/auth/' frontend/src` 对照前端调用面。

### Task 2: 股票、自选股和回测域

**Files:**
- Create: `docs/contracts/stocks.md`
- Create: `docs/contracts/watchlist.md`
- Create: `docs/contracts/backtests.md`

- [x] **Step 1:** 记录股票列表、搜索、详情、刷新、策略、历史、实时、分红、新闻、复权和机构持仓路径。
- [x] **Step 2:** 记录自选股读取、洞察、添加、删除路径及幂等语义。
- [x] **Step 3:** 记录回测创建请求和 `StrategyDetail` 响应语义。
- [x] **Step 4:** 使用 `rg -n '/api/(stocks|watchlist|backtests)' frontend/src/services/api.ts` 对照前端调用面。

### Task 3: 自动核对与发布

**Files:**
- Modify: `docs/superpowers/roadmaps/current-project-board.md`
- Modify: `docs/superpowers/plans/2026-07-11-core-api-contracts.md`

- [x] **Step 1:** 从 `backend.app.main:app` 导出 OpenAPI 路径，并与四个契约逐项核对。
- [x] **Step 2:** 运行 `git diff --check`，确认 `git status --short` 无 `frontend/**`。
- [x] **Step 3:** 更新本计划和协作看板 TODO，提交并推送 `main`。

## 验证记录

- 2026-07-11：从 `backend.app.main:app` 生成 OpenAPI，文档列出的 26 条核心路径全部存在。
- 已对照 `frontend/src/services/api.ts`、`ProfileScreen.tsx` 和 `utils/crypto.ts` 的实际调用。
- 本次只修改文档，未修改任何 `frontend/**` 或后端运行时代码。
