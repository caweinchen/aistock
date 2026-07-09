# Backend Main Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce `backend/app/main.py` by extracting API schemas, stock summary helpers, and auth/watchlist routers while preserving all existing API behavior.

**Architecture:** Move shared Pydantic models and `Literal` API types into `backend/app/schemas.py`. Move stock-summary helper functions into `backend/app/stock_summary.py` so routers do not import back from `main.py`. Move auth and watchlist endpoints into dedicated FastAPI routers under `backend/app/routers/`, then register them from `main.py`. Keep business behavior unchanged; this is a structural refactor only.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest/unittest.

## Global Constraints

- This plan only covers the first decomposition slice: `schemas.py`, `stock_summary.py`, `routers/auth.py`, and `routers/watchlist.py`.
- Do not change API paths, request models, response models, response fields, auth behavior, or frontend calls.
- Keep `main.py` responsible for app initialization, middleware, startup, health check, and routes not yet extracted.
- All planning documents must use explicit `TODO` tracking and completed work must be marked in the same change set.
- Keep documents focused and split large follow-up work into separate specs/plans.
- Commit after each task.

---

## TODO Tracking

- [x] Task 1: Add structural route tests
- [x] Task 2: Extract API schemas
- [ ] Task 3: Extract stock summary helpers
- [ ] Task 4: Extract auth router
- [ ] Task 5: Extract watchlist router
- [ ] Task 6: Verify, update docs, and record completion

---

## File Structure

- Create `backend/app/schemas.py`: shared API schemas and `Literal` types currently defined in `main.py`.
- Create `backend/app/stock_summary.py`: `stock_to_summary` and supporting pure helper functions currently defined in `main.py`.
- Create `backend/app/routers/__init__.py`: router package marker.
- Create `backend/app/routers/auth.py`: `/api/auth/*` routes plus auth dependencies.
- Create `backend/app/routers/watchlist.py`: `/api/watchlist*` routes.
- Modify `backend/app/main.py`: import schemas/routers and remove extracted route definitions.
- Modify `backend/tests/test_user_admin_and_watchlist.py`: add route compatibility assertions.
- Modify `docs/superpowers/specs/2026-07-10-backend-main-decomposition-design.md`: mark first slice completion after verification.
- Modify this plan file: check off completed steps and TODO items.

---

### Task 1: Structural Route Coverage

**Files:**
- Modify: `backend/tests/test_user_admin_and_watchlist.py`

**Interfaces:**
- Consumes: existing FastAPI `app` from `backend.app.main`.
- Produces: route registration tests that prove auth and watchlist routes remain present after extraction.

- [x] **Step 1: Add route compatibility test**

Add this test method to `UserAdminAndWatchlistTests`:

```python
    def test_auth_and_watchlist_routes_remain_registered(self):
      routes = {(route.path, ",".join(sorted(route.methods))) for route in self.client.app.routes if hasattr(route, "methods")}

      expected = {
          ("/api/auth/public-key", "GET"),
          ("/api/auth/login", "POST"),
          ("/api/auth/register", "POST"),
          ("/api/auth/change-password", "POST"),
          ("/api/auth/validate-password", "POST"),
          ("/api/auth/verify", "GET"),
          ("/api/auth/generate-password", "GET"),
          ("/api/watchlist", "GET"),
          ("/api/watchlist/insights", "GET"),
          ("/api/watchlist/{code}", "POST"),
          ("/api/watchlist/{code}", "DELETE"),
      }

      self.assertTrue(expected.issubset(routes))
```

- [x] **Step 2: Run route test**

Run:

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_auth_and_watchlist_routes_remain_registered -q
```

Expected: passes before refactor, then continues to guard route registration.

- [x] **Step 3: Commit**

```powershell
git add backend/tests/test_user_admin_and_watchlist.py docs/superpowers/plans/2026-07-10-backend-main-decomposition.md
git commit -m "test: cover auth and watchlist route registration"
```

---

### Task 2: Extract API Schemas

**Files:**
- Create: `backend/app/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: all API schema names currently used by `main.py`, `routers/auth.py`, and `routers/watchlist.py`.
- Keeps names unchanged: `StockSummary`, `WatchlistInsights`, `LoginRequest`, `LoginResponse`, `UserResponse`, `Signal`, `ReferenceStatus`, `DataCompleteness`, and related models.

- [x] **Step 1: Move schema definitions**

Create `backend/app/schemas.py` by moving these definitions out of `main.py` unchanged:

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Signal = Literal["neutral", "buy", "sell"]
ReferenceStatus = Literal["positive", "watch", "cautious", "insufficient_data"]
DataCompleteness = Literal["complete", "mostly_complete", "incomplete", "insufficient"]
RiskLevel = Literal["low", "medium", "high"]
RiskType = Literal["valuation", "volatility", "fundamentals", "holder_change", "dividend", "data_quality"]
ChecklistMode = Literal["buy", "sell"]
ChecklistStatus = Literal["pass", "attention", "user_confirm", "insufficient_data"]
WatchlistFocusLevel = Literal["priority", "watch", "cautious", "insufficient_data"]
WatchlistSortMode = Literal["overall", "risk", "data_health", "recent_change"]
ObservationType = Literal["priority", "risk", "data_quality", "refresh", "balanced"]
TradeAction = Literal["buy", "sell"]
StrategyTemplate = Literal["trend-breakout", "low-valuation-reversal", "dividend-defense"]
```

Then include the existing `BaseModel` classes from `main.py` in the same file.

- [x] **Step 2: Import schemas in `main.py`**

In `backend/app/main.py`, replace local schema/type definitions with:

```python
from app.schemas import (
    AlertItem,
    BacktestRequest,
    BacktestTrade,
    ChangePasswordRequest,
    ChecklistItem,
    ChecklistMode,
    ChecklistStatus,
    DataCompleteness,
    DataHealth,
    FactorScore,
    LoginRequest,
    LoginResponse,
    ObservationType,
    PasswordStrengthResponse,
    PreTradeChecklist,
    PricePoint,
    ReferenceStatus,
    RegisterRequest,
    RiskExplanation,
    RiskLevel,
    RiskType,
    Signal,
    StockDetail,
    StockSummary,
    StrategyDetail,
    StrategyResult,
    StrategyTemplate,
    TradeAction,
    UpdateUserRequest,
    UserResponse,
    WatchlistDataHealthOverview,
    WatchlistFocusLevel,
    WatchlistInsights,
    WatchlistIntelligence,
    WatchlistObservation,
    WatchlistRadar,
    WatchlistSortMode,
    WatchlistStockInsight,
)
```

Remove now-unused `BaseModel`, `Field`, and `Literal` imports from `main.py` if no longer needed there.

- [x] **Step 3: Run schema-dependent tests**

Run:

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py backend/tests/test_ordinary_user.py backend/tests/test_watchlist_intelligence.py -q
```

Expected: all selected tests pass.

- [x] **Step 4: Commit**

```powershell
git add backend/app/schemas.py backend/app/main.py docs/superpowers/plans/2026-07-10-backend-main-decomposition.md
git commit -m "refactor: extract api schemas from main"
```

---

### Task 3: Extract Stock Summary Helpers

**Files:**
- Create: `backend/app/stock_summary.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `stock_to_summary(stock, history=None, factors=None, alerts=None) -> StockSummary`
- Produces: `determine_data_completeness(...)`, `determine_reference_status(...)`, `reference_label(...)`, `build_primary_support(...)`, `build_primary_risk(...)`
- Consumes: schemas from `app.schemas`.

- [ ] **Step 1: Create helper module**

Create `backend/app/stock_summary.py` and move these pure helper functions out of `main.py` unchanged:

- `determine_data_completeness`
- `determine_reference_status`
- `reference_label`
- `build_primary_support`
- `build_primary_risk`
- `stock_to_summary`

Import required schema names from `app.schemas` and database model classes only for type hints.

- [ ] **Step 2: Import helpers in `main.py`**

In `backend/app/main.py`, import:

```python
from app.stock_summary import (
    build_primary_risk,
    build_primary_support,
    determine_data_completeness,
    determine_reference_status,
    reference_label,
    stock_to_summary,
)
```

Remove the moved function definitions from `main.py`.

- [ ] **Step 3: Run stock summary dependent tests**

Run:

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_watchlist_insights_returns_intelligence backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_stock_detail_returns_data_health_risk_explanations_and_checklists -q
```

Expected: selected tests pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/stock_summary.py backend/app/main.py docs/superpowers/plans/2026-07-10-backend-main-decomposition.md
git commit -m "refactor: extract stock summary helpers from main"
```

---

### Task 4: Extract Auth Router

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `router = APIRouter(prefix="/api/auth")`
- Produces dependencies: `get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User`, `get_admin_user(user: User = Depends(get_current_user)) -> User`
- Consumes schemas from `app.schemas`.

- [ ] **Step 1: Create router package and auth router**

Create `backend/app/routers/__init__.py` as an empty package marker.

Create `backend/app/routers/auth.py` and move these unchanged from `main.py`:

- `oauth2_scheme`
- `get_current_user`
- `get_admin_user`
- `/public-key`
- `/login`
- `/register`
- `/change-password`
- `/validate-password`
- `/verify`
- `/generate-password`

Use:

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import AuthSession, User, get_db
from app.rsa_utils import get_rsa_utils
from app.schemas import ChangePasswordRequest, LoginRequest, LoginResponse, PasswordStrengthResponse, RegisterRequest, UserResponse
from app.security import generate_auth_token, hash_password, hash_token, is_password_hash, validate_password_strength, verify_password

router = APIRouter(prefix="/api/auth")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
```

For moved decorators, replace `@app.get("/api/auth/public-key")` with `@router.get("/public-key")`, and similarly remove the `/api/auth` prefix from other auth paths.

- [ ] **Step 2: Register auth router**

In `backend/app/main.py`, import:

```python
from app.routers.auth import get_admin_user, get_current_user, router as auth_router
```

Register after middleware setup:

```python
app.include_router(auth_router)
```

Remove the moved auth route definitions from `main.py`.

- [ ] **Step 3: Run auth and route tests**

Run:

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_auth_and_watchlist_routes_remain_registered backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_user_login_and_admin_listing -q
```

Expected: selected tests pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/main.py backend/app/routers/__init__.py backend/app/routers/auth.py docs/superpowers/plans/2026-07-10-backend-main-decomposition.md
git commit -m "refactor: extract auth router from main"
```

---

### Task 5: Extract Watchlist Router

**Files:**
- Create: `backend/app/routers/watchlist.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `router = APIRouter(prefix="/api/watchlist")`
- Consumes: `get_current_user` from `app.routers.auth`
- Consumes schema and helper functions moved or imported from `main.py`.

- [ ] **Step 1: Create watchlist router**

Create `backend/app/routers/watchlist.py` and move these routes from `main.py`:

- `GET /api/watchlist`
- `GET /api/watchlist/insights`
- `POST /api/watchlist/{code}`
- `DELETE /api/watchlist/{code}`

Use:

```python
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import Stock, WatchlistItem, get_db
from app.ordinary_user import build_data_health
from app.routers.auth import get_current_user
from app.schemas import ReferenceStatus, StockSummary, WatchlistDataHealthOverview, WatchlistInsights
from app.watchlist_intelligence import build_watchlist_intelligence
```

Import helper functions from `app.stock_summary`:

```python
from app.stock_summary import stock_to_summary
```

Move `watchlist_intelligence_to_model` into `routers/watchlist.py` with the route because it is only used there after extraction.

- [ ] **Step 2: Register watchlist router**

In `backend/app/main.py`, import:

```python
from app.routers.watchlist import router as watchlist_router
```

Register:

```python
app.include_router(watchlist_router)
```

Remove the moved watchlist route definitions from `main.py`.

- [ ] **Step 3: Run watchlist tests**

Run:

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_watchlist_insights_returns_intelligence backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_watchlist_insights_groups_user_stocks backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_auth_and_watchlist_routes_remain_registered -q
```

Expected: selected tests pass.

- [ ] **Step 4: Commit**

```powershell
git add backend/app/main.py backend/app/routers/watchlist.py docs/superpowers/plans/2026-07-10-backend-main-decomposition.md
git commit -m "refactor: extract watchlist router from main"
```

---

### Task 6: Verification and Documentation

**Files:**
- Modify: `docs/superpowers/specs/2026-07-10-backend-main-decomposition-design.md`
- Modify: `docs/superpowers/plans/2026-07-10-backend-main-decomposition.md`

**Interfaces:**
- Verifies: full backend behavior after decomposition.
- Produces: completed TODO tracking for first slice.

- [ ] **Step 1: Start temporary backend server for encryption tests**

Run:

```powershell
$p = Start-Process -FilePath python -ArgumentList 'backend/start.py' -WorkingDirectory (Get-Location) -WindowStyle Hidden -PassThru
$p.Id | Set-Content .backend-test-server.pid
```

Wait until:

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/auth/public-key -UseBasicParsing
```

returns HTTP 200.

- [ ] **Step 2: Run backend tests**

Run:

```powershell
python -m pytest backend/tests -q
```

Expected: all backend tests pass.

- [ ] **Step 3: Stop temporary backend server**

Run:

```powershell
if (Test-Path .backend-test-server.pid) {
  $pidValue = Get-Content .backend-test-server.pid
  Stop-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
  Remove-Item .backend-test-server.pid -ErrorAction SilentlyContinue
}
```

- [ ] **Step 4: Check `main.py` size**

Run:

```powershell
(Get-Content backend/app/main.py).Count
rg -n "^@app\\.(get|post|patch|delete)" backend/app/main.py
```

Expected: line count decreases from the baseline of about 2280, and auth/watchlist decorators are no longer in `main.py`.

- [ ] **Step 5: Mark design TODO completed**

In `docs/superpowers/specs/2026-07-10-backend-main-decomposition-design.md`, change:

```markdown
- [ ] 第一轮：拆出 `schemas.py`、`stock_summary.py`、`routers/auth.py`、`routers/watchlist.py`
```

to:

```markdown
- [x] 第一轮：拆出 `schemas.py`、`stock_summary.py`、`routers/auth.py`、`routers/watchlist.py`
```

- [ ] **Step 6: Commit verification docs**

```powershell
git add docs/superpowers/specs/2026-07-10-backend-main-decomposition-design.md docs/superpowers/plans/2026-07-10-backend-main-decomposition.md
git commit -m "docs: complete backend main decomposition first slice"
```

---

## Self-Review

### Spec Coverage

- `schemas.py`: Task 2.
- `stock_summary.py`: Task 3.
- `routers/auth.py`: Task 4.
- `routers/watchlist.py`: Task 5.
- API compatibility: Tasks 1, 4, 5, and 6.
- TODO tracking and document updates: Task 6.
- No oversized follow-up scope: later router/service splits remain TODOs in the spec.

### Placeholder Scan

This plan uses `TODO` only as required tracking. It contains no TBD placeholders or unspecified implementation steps.

### Type Consistency

Schema names remain unchanged from `main.py`; routers import the same names from `app.schemas`. Auth dependencies remain named `get_current_user` and `get_admin_user`.
