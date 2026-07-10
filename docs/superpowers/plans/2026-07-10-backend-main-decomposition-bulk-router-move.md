# Backend Main Bulk Router Move Plan

**Goal:** Quickly reduce `backend/app/main.py` by moving the remaining business routes into focused router modules while preserving public API paths.

**Scope:** This is a structural move only. Keep runtime behavior compatible unless final verification exposes a pre-existing defect that must be fixed for tests.

## Constraints

- Keep `main.py` responsible for FastAPI app creation, middleware, startup, health check, and router registration.
- Do not change API paths, response models, authentication requirements, or frontend contracts.
- Prefer bulk mechanical moves over endpoint-by-endpoint manual edits.
- Keep compatibility re-exports in `main.py` for tests that import helper functions directly.
- Update TODO tracking in this plan and the design TODO list in the same change set.
- Run full verification after bulk moving, per user instruction.

## TODO Tracking

- [x] Move stock query/detail/data routes into `backend/app/routers/stocks.py`.
- [x] Move data source status/refresh routes into `backend/app/routers/data_sources.py`.
- [x] Move backtest route into `backend/app/routers/backtests.py`.
- [x] Move admin user routes into `backend/app/routers/admin.py`.
- [x] Register new routers from `main.py` and keep compatibility re-exports.
- [x] Update tests patch paths for moved internals where needed.
- [x] Run final backend verification.
- [x] Mark completed TODO items in this plan and the decomposition design.

## Target Modules

- `routers/stocks.py`
  - `/api/stocks*`
  - stock detail assembly helpers
  - factor, alert, price history, and AI summary helpers for now
- `routers/data_sources.py`
  - `/api/tushare/status`
  - `/api/eastmoney/status`
  - `/api/eastmoney/refresh/{code}`
- `routers/backtests.py`
  - `/api/backtests`
- `routers/admin.py`
  - `/api/admin/users*`

## Follow-Up TODO

- [ ] Split `routers/stocks.py` into service/assembler modules after the route move is stable.
- [ ] Keep each future plan focused instead of expanding this document.
