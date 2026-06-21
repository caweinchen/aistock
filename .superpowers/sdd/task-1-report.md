# Task 1 Report

Status: DONE

Files changed:
- `backend/app/backtest_engine.py`
- `backend/tests/test_backtest_engine.py`
- `backend/tests/__init__.py`

Commits:
- `dfaabfd` - `feat: add stock backtest engine`

Exact test commands run:
- `python -m unittest backend.tests.test_backtest_engine -v`

Expected red failure summary:
- Initial run failed before test execution because `backend.tests` could not be imported.

Green pass summary:
- `python -m unittest backend.tests.test_backtest_engine -v` ran all 5 tests successfully.

Self-review notes:
- The engine stays pure domain logic and only depends on standard library modules.
- `normalize_price_bars` accepts dicts or attribute objects, uses `date` or `trade_date`, and sorts ascending.
- The package marker under `backend/tests` was needed so the brief's exact unittest module path resolves cleanly.
