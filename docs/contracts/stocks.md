# API Contract: 股票数据

除特别说明外，以下接口均使用 Bearer token。

## 核心读取接口

| 方法 | 路径 | 响应 |
|---|---|---|
| GET | `/api/stocks` | `StockSummary[]` |
| GET | `/api/stocks/search?q=<keyword>` | `StockSummary[]` |
| GET | `/api/stocks/{code}` | `StockDetail` |
| GET | `/api/stocks/{code}/strategies` | `StrategyResult[]` |
| GET | `/api/stocks/{code}/strategies/{strategy_id}` | `StrategyDetail` |
| GET | `/api/stocks/{code}/history` | `PricePoint[]` |
| GET | `/api/stocks/{code}/realtime` | 实时报价对象 |
| GET | `/api/stocks/{code}/dividend` | 分红记录数组 |
| GET | `/api/stocks/{code}/news` | 新闻记录数组 |
| GET | `/api/stocks/{code}/adj-factor` | 复权因子数组 |
| GET | `/api/stocks/{code}/inst-hold` | 机构持仓数组 |
| GET | `/api/stocks/{code}/factors` | `FactorScore[]` |
| GET | `/api/stocks/{code}/alerts` | `AlertItem[]` |

## 显式刷新接口

| 方法 | 路径 | 响应与语义 |
|---|---|---|
| GET | `/api/stocks/refresh-all` | 刷新可用行情后返回 `StockSummary[]` |
| GET | `/api/stocks/{code}/refresh` | 刷新单股数据并返回 `StockDetail` |

刷新依赖外部数据源；上游不可用时可能回退到已有缓存，无法形成有效结果时返回 `500`。

## 关键响应模型

`StockSummary` 是列表、自选股变更和洞察分组中的股票摘要。前端依赖的关键字段包括：

- 标识与行情：`code`、`name`、`price`、`change_percent`。
- 普通用户摘要：`reference_status`、`reference_label`、`summary`、`primary_support`、`primary_risk`。
- 数据健康：`data_completeness`、`data_updated_at`。

`StockDetail` 包含 `StockSummary` 的详情信息，并提供：

- `history`、`factors`、`alerts`、`strategies`、`ai_summary`。
- `data_health`、`risk_explanations`、`buy_checklist`、`sell_checklist`。
- `updated_at` 供前端缓存判断。

完整字段、枚举和可空性以 `backend/app/schemas.py` 中同名模型及 `/openapi.json` 为准。

## 特定错误

- `404`：股票代码或策略不存在。
- `401/403`：认证失败或账户不可用。
- `422`：查询参数或路径参数不符合 schema。
- `500`：数据库或外部数据源失败。

## 兼容性说明

- 前端允许缓存股票数据；缓存与离线回退是前端行为，不改变服务端响应结构。
- 普通用户参考状态当前为 `positive`、`watch`、`cautious`、`insufficient_data`。
- 风险、摘要和清单是信息参考，不表达确定性收益或交易承诺。
