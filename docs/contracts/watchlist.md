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

## Stage 2C: portfolio risk and recent change

`GET /api/watchlist/insights` keeps every legacy top-level field. The
`intelligence` object adds the following backward-compatible fields:

- `risk_overview`: `status`, `level`, `total_count`, `high_risk_count`, and
  `insufficient_count`. When the watchlist is empty or every stock lacks enough
  data, `status` is `insufficient_data` and `level` is `insufficient_data`.
- `industry_concentration`: the largest non-empty `industry` group, its count
  and four-decimal ratio, plus `is_concentrated`. A ratio of 0.5 or greater is
  concentrated. Missing industry data returns `status: insufficient_data`.
- Each `intelligence.insights[]` item adds `industry` and `recent_change`.
  `recent_change` contains `score_change`, `risk_score_change`, `baseline_at`,
  and `current_updated_at`. Deltas are nullable and `status` remains
  `insufficient_data` until both a prior published baseline and sufficient
  current data exist.

`sort_modes` continues to include `overall`, `risk`, and `data_health`, and now
documents `recent_change`: known changes sort by absolute score delta, then by
update time; unknown changes follow known changes.

The baseline is isolated by authenticated `user_id + stock_code`. The endpoint
reads local stock/history/factor caches and does not introduce a network refresh.
After constructing a response it publishes the current baseline for the next
request. The reversible migration is
`db/migrations/20260712_watchlist_insight_baselines_up.sql`; rollback uses the
matching `_down.sql` file.
