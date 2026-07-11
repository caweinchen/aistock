# 股票分析服务拆分实施计划

> **For agentic workers:** Use `superpowers:executing-plans` to execute task-by-task. All unfinished items use explicit TODO checkboxes.

**Goal:** 迁移因子、风险和 AI 摘要分析逻辑到后端 service，保持 API 和前端兼容。

**Global Constraints:** 只修改后端、测试和文档；不修改 frontend；不变更 API 契约；先失败测试后实现；完成后提交并推送 `main`。

## TODO Tracking

- [x] TODO: 增加 `stock_analysis_service.py` 和 router 委托边界测试。
- [x] TODO: 迁移因子计算与缓存回退。
- [x] TODO: 迁移风险提示持久化。
- [x] TODO: 迁移 AI 摘要生成与持久化。
- [x] TODO: 运行全量后端测试并记录结果。
- [x] TODO: 提交并推送 `main`。

## Task 1: 边界与因子

**Files:** `backend/app/stock_analysis_service.py`, `backend/app/routers/stocks.py`, `backend/tests/test_stock_analysis_service.py`

1. 先写 `test_ensure_factor_scores_delegates_to_service`、`test_factor_fallback_persists_local_scores`并运行确认失败。
2. 新建 `AnalysisOperations` 和 `ensure_factor_scores(db, stock, history, operations)`，保留 Pro 数据路径、本地 `calculate_factors` 回退、FactorScoreDB delete/add/commit/rollback。
3. router 中保留同名兼容口，传入原有 TuShare 与计算函数。
4. 运行 `python -m pytest backend/tests/test_stock_analysis_service.py backend/tests/test_tushare_integration.py -q`。

## Task 2: 风险与摘要

**Files:** `backend/app/stock_analysis_service.py`, `backend/app/routers/stocks.py`, `backend/tests/test_stock_analysis_service.py`

1. 先写风险持久化、AI 摘要持久化和 rollback 失败测试，观察失败。
2. 迁移 `ensure_alerts(db, stock, history, factors)` 和 `ensure_ai_summary(db, stock, history, factors, alerts)`。
3. router 兼容口委托 service，不改变调用签名。
4. 运行 `python -m pytest backend/tests/test_stock_analysis_service.py backend/tests/test_user_admin_and_watchlist.py -q`。

## Task 3: 完成验证与发布

1. 确认本次无 API 语义变更，不更新 `docs/contracts/`。
2. 运行临时 API 服务后的 `python -m pytest backend/tests -q`。
3. 将本计划 TODO 和验证结果更新为完成。
4. 提交后端变更并推送 `main`。

## 验证记录

- 2026-07-11：启动临时 API 后运行 `python -m pytest backend/tests -q`。
- 结果：74 项测试通过，0 失败，10 个子测试通过。
- 已知警告：6 条现有 SQLAlchemy/FastAPI 弃用警告。
- 契约判定：API 路径、认证、错误码、响应字段和数据语义未变，无需更新 `docs/contracts/`。
- 前端边界：本次未修改任何 `frontend/**` 文件。
