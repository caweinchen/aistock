# API Contract: 自选股

所有接口均使用 Bearer token，数据按当前用户隔离。

## 接口

| 方法 | 路径 | 成功响应 |
|---|---|---|
| GET | `/api/watchlist` | `{ "codes": string[] }` |
| GET | `/api/watchlist/insights` | `WatchlistInsights` |
| POST | `/api/watchlist/{code}` | 更新后的 `StockSummary[]` |
| DELETE | `/api/watchlist/{code}` | 更新后的 `StockSummary[]` |

添加已存在的代码和删除未加入的代码均按幂等操作处理。添加时若本地没有该股票，后端会尝试从数据源建立股票记录。

## WatchlistInsights

```json
{
  "total": 1,
  "groups": {
    "positive": [],
    "watch": [],
    "cautious": [],
    "insufficient_data": []
  },
  "risk_overview": "string",
  "data_updated_at": "2026-07-11T00:00:00Z",
  "data_health_overview": {
    "total": 1,
    "insufficient_count": 0,
    "incomplete_count": 0,
    "latest_updated_at": "2026-07-11T00:00:00Z",
    "message": "string"
  },
  "intelligence": {
    "radar": {},
    "observations": [],
    "insights": [],
    "sort_modes": []
  }
}
```

`groups` 的四个键固定存在，值为 `StockSummary[]`。`intelligence` 承载自选股雷达、观察项、逐股洞察和可用排序模式；其完整字段以 `WatchlistInsights` 相关 Pydantic 模型和 `/openapi.json` 为准。

## 特定错误

- `404 Stock not found`：添加时外部数据源也无法识别代码，或删除时股票记录不存在。
- `500 Failed to load watchlist`、`Failed to add to watchlist`、`Failed to remove from watchlist`：数据库或上游失败。
- `401/403`：认证失败或账户不可用。

## 兼容性说明

- 洞察中的新增可选字段应由前端渐进增强；未知字段必须忽略。
- `data_health_overview` 用于组合层面的数据质量提示，不能替代单股 `data_health`。
