# 股票分析服务拆分设计

## 目标

将 `backend/app/routers/stocks.py` 中的因子计算、风险提示和 AI 摘要生成逻辑迁移到 `backend/app/stock_analysis_service.py`，保持现有 API 、数据库行为和测试 patch 路径。

## 范围

- 迁移 `ensure_factor_scores` 、基于财务数据的因子计算和本地因子回退。
- 迁移 `ensure_alerts` 和 `ensure_ai_summary`。
- router 保留同名兼容入口，通过显式依赖委托 service。
- 不修改 API 路径、response model、认证和前端文件。

## 错误处理

- TuShare 财务数据失败时回退本地因子，并执行 rollback。
- 风险写库或摘要写库失败时执行 rollback，保持现有调用方容错行为。

## 验证

- 新增 service 边界、因子回退、风险持久化和摘要生成测试。
- 运行完整 `python -m pytest backend/tests -q`。
- 本次无 API 契约变更，无需更新 `docs/contracts/`。
