# API Contracts

本目录是前后端协作的稳定接口契约。字段类型的机器可读权威来源是后端运行时 `/openapi.json`；这里记录业务语义、认证、错误和兼容性要求。

## 契约索引

- [认证与账户](auth.md)
- [股票数据](stocks.md)
- [自选股](watchlist.md)
- [回测](backtests.md)

## 通用约定

- 基础路径：`http://<host>:<port>`，默认端口 `8000`；联调机器可使用其他端口。
- JSON 请求必须发送 `Content-Type: application/json`。
- 除契约明确标为公开的接口外，均发送 `Authorization: Bearer <token>`。
- 时间字段使用 ISO 8601 字符串；可空字段返回 `null`。
- 股票代码 `code` 使用六位 A 股代码字符串，例如 `600519`。

## 错误格式

FastAPI HTTP 错误：

```json
{ "detail": "Human-readable message" }
```

请求校验错误的 `detail` 为数组。通用认证错误包括：

- `401`：`Not authenticated`、`Invalid token`、`Token expired`、`User not found`。
- `403`：`Account is inactive` 或权限不足。
- `422`：请求参数或 JSON 字段不符合 schema。
- `500`：服务端或上游数据源异常；前端应显示通用失败状态，不解析日志文本。

## 兼容性规则

- 新增可选响应字段是向后兼容变更。
- 删除或重命名字段、收紧可空性、改变枚举值、认证方式、状态码或数据语义是破坏性变更。
- 任何契约变更必须先更新本目录，再实现后端，并由前端机器按契约接入。
- 前端应忽略未知响应字段，并对契约中标记为可选的字段提供降级展示。

## TODO Tracking

- [x] TODO: 核心接口契约已覆盖 auth、stocks、watchlist、backtests。
- [x] TODO: 后端电脑在每次接口变更时同步更新对应契约。
