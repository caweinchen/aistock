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
