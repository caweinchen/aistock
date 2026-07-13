# Watchlist Risk and Recent Change Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `GET /api/watchlist/insights` with a backward-compatible portfolio risk overview, industry concentration, and stable per-stock recent-change data.

**Architecture:** Keep all existing response fields and add optional nested models under `intelligence`. Compute portfolio aggregation in the pure watchlist intelligence module, while the router owns authenticated database reads and upserts a per-user/per-stock published baseline. A reversible SQL migration mirrors the SQLAlchemy model and startup schema compatibility path.

**Tech Stack:** Python 3, FastAPI, Pydantic, SQLAlchemy, unittest, SQLite/MySQL-compatible SQL.

## Global Constraints

- Preserve every existing `WatchlistInsights` response field and authentication behavior.
- Insufficient data must return an explicit `insufficient_data` state and null change values, never deterministic trading advice.
- Reuse locally loaded stock data; this read endpoint must not refresh records that are present and current.
- Migration must have an explicit rollback.
- Work only on `feature/backend/MUL-12-watchlist-risk`; publish Gitee first, verify SHA, then GitHub.

---

### Task 1: Risk aggregation and recent-change domain contract

**Files:**
- Modify: `backend/app/watchlist_intelligence.py`
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_watchlist_intelligence.py`

**Interfaces:**
- Consumes: stock contexts with `stock.industry`, current `summary.score`, `risk_score`, completeness, and optional baseline values/timestamp.
- Produces: `risk_overview`, `industry_concentration`, and insight-level `recent_change` objects; `sort_watchlist_insights(..., "recent_change")` orders known absolute score changes before insufficient baselines.

- [ ] **Step 1: Write failing tests** for empty results, insufficient baselines, high-risk counts, industry concentration, and recent-change sorting using real dataclass results.
- [ ] **Step 2: Verify RED** with `$env:PYTHONPATH='.;backend'; python -m unittest backend.tests.test_watchlist_intelligence -v`; expect missing fields/assertion failures.
- [ ] **Step 3: Implement minimal dataclasses and Pydantic models** with additive defaults, calculate concentration as the largest non-empty industry share, classify high risk at `risk_score >= 45`, and expose score/risk deltas only when both baseline and current data are sufficient.
- [ ] **Step 4: Verify GREEN** with the same unittest command; expect all watchlist intelligence tests to pass.

### Task 2: Persistent published baseline and authenticated endpoint integration

**Files:**
- Modify: `backend/app/database.py`
- Modify: `backend/app/routers/watchlist.py`
- Modify: `backend/init_db.sql`
- Create: `db/migrations/20260712_watchlist_insight_baselines_up.sql`
- Create: `db/migrations/20260712_watchlist_insight_baselines_down.sql`
- Test: `backend/tests/test_database_schema.py`
- Test: `backend/tests/test_user_admin_and_watchlist.py`

**Interfaces:**
- Produces: `WatchlistInsightBaselineDB(user_id, stock_code, score, risk_score, data_completeness, published_at, updated_at)` with a unique `(user_id, stock_code)` constraint.
- Router passes the previous published baseline into each stock context, returns the computed response, then upserts the current publishable values for the next request.

- [ ] **Step 1: Write failing schema and API tests** proving unique baseline identity, empty-watchlist behavior, additive legacy fields, authenticated access, aggregation, and baseline-based recent changes.
- [ ] **Step 2: Verify RED** with targeted unittest modules; expect missing model/table/response fields.
- [ ] **Step 3: Implement the minimal model, startup schema support, reversible migrations, router query and upsert** without adding network refreshes to the insights GET path.
- [ ] **Step 4: Verify GREEN** with targeted tests; expect all endpoint and schema tests to pass.

### Task 3: Contract, roadmap, and release verification

**Files:**
- Modify: `docs/contracts/watchlist.md`
- Modify: `docs/superpowers/roadmaps/current-project-board.md`

**Interfaces:**
- Documents exact field names, nullable semantics, thresholds, sorting behavior, cache/baseline lifecycle, authentication, compatibility, and rollback commands.

- [ ] **Step 1: Update the contract example and field table** to match `/openapi.json`, including `insufficient_data` and null delta semantics.
- [ ] **Step 2: Replace the active roadmap TODO** with the Stage 2C backend slice state and handoff requirements.
- [ ] **Step 3: Run focused and complete backend regression** using `$env:PYTHONPATH='.;backend'; python -m unittest discover -s backend/tests -v`, plus `git diff --check`; expect zero failures.
- [ ] **Step 4: Inspect generated OpenAPI** and assert the new schema properties exist while all old `WatchlistInsights` properties remain.
- [ ] **Step 5: Commit, push Gitee first and verify remote SHA, then push GitHub and verify identical SHA.**

