# Stock Detail Backtest Design

## Scope

Build the first complete stock-detail backtest path for the existing AIStock app.
This scope uses the existing TuShare-backed daily price history and keeps the
current UI shape. It does not add the full custom strategy builder parameter set
yet.

The goal is to replace simulated strategy details with explainable backtest
results generated from historical OHLCV data.

## Current State

- `GET /api/stocks/{code}` loads stock detail, history, factors, strategies, and
  alerts.
- TuShare daily prices are already fetched into `price_history` when local data
  is missing or stale.
- `GET /api/stocks/{code}/strategies/{strategy_id}` exists, but its detail
  output is simplified and creates artificial trades.
- The frontend `useStockData.loadStrategyDetail` does not call the backend
  strategy detail endpoint. It builds a local mock `StrategyDetail` from the
  strategy summary and price history.
- `POST /api/backtests` exists, but custom backtest output is also based on
  simplified return bias logic.

## Approach

Use a backend backtest engine as the source of truth. The frontend should fetch
strategy detail from the backend and render the returned result.

This approach is preferred because it makes the current detail page real without
expanding into the larger custom strategy builder scope.

## Backend Design

Create a focused backtest calculation module that accepts normalized historical
price bars and a strategy template. It returns:

- Strategy summary metrics: total return, max drawdown, win rate, risk, period,
  and summary text.
- Strategy detail metrics: annualized return, Sharpe ratio, trade count, rule
  descriptions, and trade list.
- Trades with date, action, price, quantity, and reason.

The engine should use real `price_history` rows. If local history is missing,
the existing detail load path can continue using TuShare to populate it before
strategy calculation.

### Data Normalization

Historical bars should be sorted ascending by date before calculation. The
engine needs at least close price and date. It should use open, high, low, and
volume when available, but tolerate older sample rows that only have close and
volume.

Invalid or insufficient data should not crash the API. For fewer than 30 bars,
strategy summaries can be empty or return a clear 400-style response for detail
requests, depending on the existing endpoint behavior being exercised.

### Strategy Rules

`trend-breakout`

- Buy when close crosses above a moving average.
- Sell when close falls below the moving average or a stop-loss threshold is hit.
- Use volume expansion as an explanatory reason when available.

`low-valuation-reversal`

- Treat price near the recent range low as a valuation proxy.
- Buy after low-range price action starts to recover.
- Sell when price returns toward the recent midpoint/high range or a stop-loss
  threshold is hit.

`dividend-defense`

- Use a defensive proxy because dividend data is not in the current local model.
- Prefer periods with lower realized volatility and positive trend filter.
- Exit when volatility rises materially, trend weakens, or stop-loss is hit.

### Metrics

Return rate should be based on simulated equity change over the selected history.
Max drawdown should be calculated from the equity curve. Win rate should be based
on completed sell trades with positive versus negative realized PnL. Annualized
return should be scaled by elapsed calendar days. Sharpe ratio should be
estimated from daily equity returns.

Use simple long-only position sizing for this phase. A fixed initial cash value
and 100-share lots are acceptable as long as results are deterministic.

### Persistence

Generated strategy summaries should continue using the existing `strategies`
table and `StrategyResultDB` model. Detail trades do not need a new persistence
table in this phase; they can be recomputed from history on detail request.

If storing custom backtest summaries creates duplicate primary keys, IDs should
remain unique and deterministic enough for the current request.

## Frontend Design

Update `useStockData.loadStrategyDetail` so it calls:

`getStrategyDetail(selectedCode, strategyId)`

The hook should cache the returned backend detail by `code:strategyId`, keep the
existing loading and error states, and stop building local mock trades.

`StrategyCard` can keep the current layout. It already supports annualized
return, Sharpe ratio, trade count, rules, and trades.

`createCustomBacktest` should continue calling `POST /api/backtests`; the
returned detail should be cached so the created strategy expands immediately.

## API Compatibility

Keep the existing response shapes:

- `StrategyResult`
- `BacktestTrade`
- `StrategyDetail`
- `BacktestRequest`

This avoids broad TypeScript and UI changes.

## Error Handling

- If a strategy ID is unknown, return 404 as today.
- If historical data is insufficient, return a clear error rather than fake
  trades.
- If TuShare refresh fails but local usable history exists, use local history.
- If no usable history exists, return an API error and let the frontend show the
  existing error panel.

## Testing

Backend tests should cover the backtest engine directly:

- A rising breakout sequence produces a buy trade and positive return.
- A falling sequence exits or stays defensive and limits drawdown.
- Insufficient history returns no summaries or a clear detail error.
- Max drawdown, win rate, and annualized return are calculated from equity and
  trades, not from fixed bias values.

Frontend or service-level tests should cover:

- `loadStrategyDetail` calls the backend `getStrategyDetail` path.
- Returned strategy detail is cached under the selected stock and strategy ID.
- Custom backtest detail is inserted into the local cache after creation.

## Out Of Scope

- User-configurable MA windows, stop-loss, fees, slippage, benchmark comparison,
  and exported reports.
- New database tables for backtest trades.
- A full portfolio or multi-strategy research platform.
