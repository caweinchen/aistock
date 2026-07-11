# API Contract: 自定义回测

## 创建回测

- Method: `POST`
- Path: `/api/backtests`
- Auth: `Authorization: Bearer <token>`
- Content-Type: `application/json`

请求使用 `BacktestRequest`：

```json
{
  "code": "600519",
  "name": "Custom Strategy",
  "template": "trend-breakout",
  "lookback_days": 180,
  "risk": "medium"
}
```

`template` 当前取值为 `trend-breakout`、`low-valuation-reversal`、`dividend-defense`；`lookback_days` 范围为 30 至 720；`risk` 为 `low`、`medium`、`high`。默认值和完整限制以 `backend/app/schemas.py` 的 `BacktestRequest` 和 `/openapi.json` 为准。

成功返回 `StrategyDetail`，包含策略元数据、回测指标、交易记录及收益曲线；同时将结果持久化到当前用户的策略记录。

## 错误

- `401/403`：认证失败或账户不可用。
- `404`：股票代码不存在。
- `422`：策略类型或参数不符合 `BacktestRequest`。
- `500`：历史数据、计算或持久化失败。

## 兼容性说明

- 回测是基于历史数据的模拟结果，不代表未来收益。
- 新增可选指标是向后兼容；改变指标计算语义、策略参数默认值或收益单位必须更新本契约。
