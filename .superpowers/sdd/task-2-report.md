Status: DONE

Files changed:
- `backend/app/main.py`
- `backend/tests/test_backtest_engine.py`

Commits:
- `8697a0e` - `feat: use real backtests in stock strategy endpoints`

Exact test commands run:
- `python -m unittest backend.tests.test_backtest_engine.BacktestApiConversionTests -v`
- `python -m unittest backend.tests.test_backtest_engine -v`

Expected red failure output summary:
- The targeted conversion test failed during import with `ImportError: cannot import name 'engine_result_to_detail' from 'backend.app.main'`, confirming the missing helper functions before implementation.

Green pass output summary:
- `python -m unittest backend.tests.test_backtest_engine -v` passed all 6 tests, including the new conversion test and the existing engine coverage.

Self-review notes:
- Added `engine_result_to_strategy` and `engine_result_to_detail` to preserve existing FastAPI response model shapes while sourcing values from `BacktestResult`.
- Replaced mock strategy detail and custom backtest calculations with `run_backtest(...)` results and the brief's `BacktestResult` reshaping for custom IDs/periods.
- Added `calculate_strategies(...)` in this worktree because the brief referenced it but the function was absent here; wired stock detail and strategy list reads to engine-generated standard summaries while keeping persisted `custom-*` strategies visible.

---

Review fix follow-up:

Files changed:
- `backend/app/main.py`
- `backend/tests/test_backtest_engine.py`

Root cause:
- Persisted custom strategies save ids like `custom-{template}-{lookback_days}-{timestamp}`.
- `build_strategy_detail(...)` previously passed that id straight into `run_backtest(...)` without `lookback_days`, so `run_backtest(...)` resolved the template from the id string but replayed the full available history.
- Strategy list/detail/history loading was split across multiple direct `PricePointDB` queries, which made the strategy list endpoint bypass the existing `get_stock_detail(...)` history path.

TDD evidence:
- Red command:
  - `python -m unittest backend.tests.test_backtest_engine.BacktestApiConversionTests.test_custom_strategy_detail_reuses_saved_lookback -v`
- Red output summary:
  - Failed with `AssertionError: 'Last 120 bars' != 'Last 90 days'`, proving persisted custom detail replayed full history instead of the saved 90-day window.

Implementation summary:
- Added `parse_custom_strategy_id(...)` to recover `(template, lookback_days)` from persisted custom ids without changing API shapes.
- Updated `build_strategy_detail(...)` to:
  - call `run_backtest(...)` with the parsed template and saved `lookback_days` for custom strategies,
  - preserve the persisted custom strategy id and period in the returned detail payload.
- Added `get_price_history(...)` and reused it from `get_stock_detail(...)` and `/api/stocks/{code}/history`.
- Updated `/api/stocks/{code}/strategies` to return `get_stock_detail(db, code).strategies` so strategy calculations reuse the existing stock detail/history loading path.
- Kept the existing TuShare refresh behavior unchanged because the current refresh endpoint only updates realtime quote fields on `stocks`; it does not populate `price_history`, so adding a new refresh pipeline here would have exceeded the task and app architecture.

Verification:
- Green command:
  - `python -m unittest backend.tests.test_backtest_engine.BacktestApiConversionTests.test_custom_strategy_detail_reuses_saved_lookback -v`
- Green output summary:
  - Passed.
- Covering command:
  - `python -m unittest backend.tests.test_backtest_engine -v`
- Covering output summary:
  - Passed all 7 tests.

---

Second review fix follow-up:

Files changed:
- `backend/app/main.py`
- `backend/tests/test_backtest_engine.py`

Root cause:
- The isolated worktree did not include the main checkout's uncommitted TuShare history-population logic, so backtests could still run against empty or stale `price_history` rows.

TDD evidence:
- Red command:
  - `python -m unittest backend.tests.test_backtest_engine.BacktestApiConversionTests.test_ensure_price_history_loads_tushare_when_local_history_empty -v`
- Red output summary:
  - Failed during import with `ImportError: cannot import name 'ensure_price_history' from 'backend.app.main'`, proving no pre-backtest history-load path existed.

Implementation summary:
- Added `ensure_price_history(db, stock)` to load ordered local history and, when missing or stale and TuShare is enabled, call `get_tushare_service().get_daily_price(...)` using the stock ts_code or a schema-compatible code suffix fallback.
- Persisted returned TuShare daily rows into existing `price_history` columns only: `stock_code`, `date`, `close`, `volume`.
- Updated `get_stock_detail(...)` so strategy summaries, strategy detail, and custom backtests all receive history from the ensured path through the existing detail flow.
- TuShare failures fall back to existing local rows instead of turning stock detail into a service outage.

Verification:
- Green command:
  - `python -m unittest backend.tests.test_backtest_engine.BacktestApiConversionTests.test_ensure_price_history_loads_tushare_when_local_history_empty -v`
- Green output summary:
  - Passed.
- Covering command:
  - `python -m unittest backend.tests.test_backtest_engine -v`
- Covering output summary:
  - Passed all 8 tests.
