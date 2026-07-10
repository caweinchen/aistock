# 股票行情数据服务拆分设计

## 背景

`backend/app/routers/stocks.py` 已拆出个股详情 assembler，但仍同时承担实时行情更新、交易时段判断、历史行情缓存和增量刷新逻辑。这些职责不属于 HTTP 路由层，并且被个股详情、回测和关联数据计算共享。

## 目标

- 新增独立的行情数据 service，统一承担实时行情和历史行情刷新。
- 缩小 `routers/stocks.py` 的职责，保留路由、参数、鉴权、调用和响应。
- 保持现有 API 路径、响应模型、数据刷新时机和错误回退行为。
- 保持 `main.py`、回测模块和现有测试使用的兼容导出。

## 非目标

- 不拆分因子计算、风险生成、AI 摘要、新闻、分红或股东数据。
- 不修改数据库 schema。
- 不修改前端代码、前端类型或 API 契约。
- 不引入新的外部数据源。

## 模块边界

### `backend/app/stock_data_service.py`

负责：

- 调用 EastMoney 实时行情并更新 `Stock`。
- 读取本地 `PricePointDB` 历史行情。
- 判断当前是否处于交易时段、午间休市或非交易时段。
- 计算最近已结束交易时段。
- 根据更新时间和最新行情日期判断是否需要刷新。
- 从 TuShare 获取增量日线，更新或插入本地记录并返回排序后结果。

不负责：

- HTTP 鉴权、路由参数和响应序列化。
- 因子、风险、策略或摘要生成。

### `backend/app/routers/stocks.py`

- 保留原有函数名作为兼容入口。
- 兼容入口委托 `stock_data_service` 执行实际逻辑。
- 路由层不复制 service 内部的时间和刷新判断。

## 数据流

1. router 或 assembler 调用兼容入口。
2. 兼容入口将数据库会话、股票和数据源依赖交给 service。
3. service 先读取本地历史，根据交易时间和最后更新时间决定是否请求远端。
4. 不需刷新时直接返回本地记录。
5. 需要刷新时执行增量拉取和 upsert，提交后重新读取并排序。

## 错误处理

- 实时行情更新失败时回滚当前事务，记录错误，不改变现有调用方的容错行为。
- 历史行情拉取失败时回滚，返回刷新前的本地历史。
- 远程返回空列表时保留本地历史，并沿用现有 `data_status` 降级行为。
- 无历史数据时使用现有回溯窗口；有历史数据时从最新日期增量请求。

## 兼容策略

- `GET /api/stocks/{code}`、`GET /api/stocks/{code}/history` 和刷新类 API 路径不变。
- `stocks.py` 保留 `get_price_history`、`ensure_price_history`、`update_stock_realtime_quote`、`_history_needs_refresh` 等导出名称。
- 现有测试对 `app.routers.stocks.*` 的 patch 路径保持有效。
- service 通过显式依赖参数调用 TuShare/EastMoney，避免反向依赖 router。

## 测试策略

- 先增加 router 兼容入口委托 service 的边界测试。
- 保留并运行现有交易时段、历史刷新和 TuShare 集成测试。
- 增加不需刷新、增量刷新、远程空结果和异常回退测试。
- 全量运行 `python -m pytest backend/tests -q`；加密测试使用临时后端服务。

## 成功标准

- `stocks.py` 不再包含历史行情刷新的实际实现。
- router 兼容入口只委托 service，不复制业务判断。
- 现有 API 契约和 patch 路径保持稳定。
- 新增和现有后端测试全部通过。
- 差异中不包含任何前端文件。
