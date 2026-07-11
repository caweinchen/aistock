# 核心 API 契约补齐设计

## 目标

为前端已经使用的 `auth`、`stocks`、`watchlist`、`backtests` 四个核心域建立可维护的接口契约，使两台开发机器可以在不修改对方代码的前提下独立开发和联调。

## 范围与约束

- 本次只修改 `docs/contracts/`、本规格书、实施计划和协作看板。
- 不修改后端运行时代码，不修改任何 `frontend/**` 文件。
- 契约描述当前已实现行为，不改变 API 路径、认证、错误码、字段或数据语义。
- FastAPI 生成的 `/openapi.json` 是字段类型的权威机器可读来源；Markdown 契约负责记录稳定语义、兼容要求和典型错误。

## 文档结构

- `docs/contracts/README.md`：契约总则、认证约定、错误格式、索引和维护流程。
- `docs/contracts/auth.md`：登录、注册、令牌校验、公钥和密码相关接口。
- `docs/contracts/stocks.md`：股票列表、搜索、详情、刷新、策略及附属数据接口。
- `docs/contracts/watchlist.md`：自选股读取、增删和洞察接口。
- `docs/contracts/backtests.md`：自定义回测创建接口。

## 兼容性规则

- 受保护接口统一使用 `Authorization: Bearer <token>`。
- FastAPI 错误体统一按 `{ "detail": string | array }` 消费；前端不得依赖未列入契约的日志文本。
- 新增可选响应字段属于向后兼容；删除字段、改名、收紧可空性、改变枚举或状态码属于契约变更。
- `StockDetail`、`StockSummary`、`WatchlistInsights` 和 `StrategyDetail` 的完整字段以 `backend/app/schemas.py` 与 `/openapi.json` 为准，契约额外标记前端当前依赖的关键字段。

## 验证

- 从 FastAPI 应用导出 OpenAPI，确认四个契约中列出的路径均存在。
- 检查前端 `frontend/src/services/api.ts` 的核心调用均可映射到契约文档。
- 运行文档链接和工作区范围检查，确认没有前端修改。
