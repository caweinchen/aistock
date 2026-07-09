# Watchlist Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build phase 2A and 2B of watchlist intelligence by adding explainable watchlist-pool insights to the existing watchlist insights API and home page.

**Architecture:** Add a focused backend product-rule module that converts per-stock summaries, data health, and risk factors into watchlist-level radar, observations, and stock insight records. Keep `/api/watchlist/insights` backward compatible by adding an optional `intelligence` object and preserving existing fields. Extend frontend types first, then progressively render radar and observation content inside the existing Home screen insight panel.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest/unittest, Expo 56, React Native 0.85, TypeScript, Vitest.

## Global Constraints

- Do not implement membership, subscription, payment, management backend, report export, professional edition, full holding-position management, or an independent watchlist insights page in this plan.
- Do not output direct trading commands such as `立即买入`, `强烈卖出`, `必涨`, `稳赚`, `最佳买点`, `今日牛股`, or `必买股票`.
- All new watchlist intelligence copy must remain learning/reference oriented and must not imply deterministic returns or buy/sell instructions.
- Keep existing API fields compatible: `total`, `groups`, `risk_overview`, `data_updated_at`, `disclaimer`, and `data_health_overview` remain available.
- New API fields must be optional or have defaults so older cached responses do not break the frontend.
- Before modifying frontend code, read Expo 56 versioned docs at `https://docs.expo.dev/versions/v56.0.0/`.
- Use TDD for backend and frontend behavior changes.
- Commit after each task.

---

## File Structure

- Create `backend/app/watchlist_intelligence.py`: pure product-rule module; no database access.
- Create `backend/tests/test_watchlist_intelligence.py`: unit tests for watchlist classification, radar, observations, and sorting.
- Modify `backend/app/main.py`: Pydantic response models, converters, and `/api/watchlist/insights` integration.
- Modify `backend/tests/test_user_admin_and_watchlist.py`: API contract tests for `intelligence` and corrected data-health counting.
- Modify `frontend/src/types/index.ts`: TypeScript interfaces for the new response object.
- Modify `frontend/src/services/api.test.ts`: API compatibility test data and assertions.
- Modify `frontend/src/pages/HomeScreen.tsx`: lightweight rendering inside the existing watchlist insights panel.
- Modify `frontend/src/i18n/locales/zh.ts`, `zh-Hant.ts`, `en.ts`: labels for radar and observations.
- Modify `docs/PRODUCT_COMMERCIALIZATION_ROADMAP.md`: mark phase 2 first slice progress after verification.
- Modify this plan file as tasks complete by checking boxes.

---

### Task 1: Backend Watchlist Intelligence Rule Module

**Files:**
- Create: `backend/app/watchlist_intelligence.py`
- Test: `backend/tests/test_watchlist_intelligence.py`

**Interfaces:**
- Consumes: stock-like context objects with `stock`, `summary`, `data_health`, `support_factors`, and `risk_factors` attributes.
- Produces:
  - `build_watchlist_intelligence(stock_contexts) -> WatchlistIntelligenceResult`
  - `sort_watchlist_insights(insights, mode: WatchlistSortMode) -> list[WatchlistStockInsightResult]`
  - dataclasses `WatchlistStockInsightResult`, `WatchlistRadarResult`, `WatchlistObservationResult`, `WatchlistIntelligenceResult`

- [x] **Step 1: Add failing rule tests**

Create `backend/tests/test_watchlist_intelligence.py`:

```python
import unittest
from datetime import datetime
from types import SimpleNamespace

from backend.app.watchlist_intelligence import build_watchlist_intelligence, sort_watchlist_insights


def make_context(
    code,
    name,
    score,
    reference_status,
    completeness="complete",
    support_factors=None,
    risk_factors=None,
    updated_at=None,
):
    stock = SimpleNamespace(code=code, name=name, score=score, updated_at=updated_at)
    summary = SimpleNamespace(
        code=code,
        name=name,
        score=score,
        reference_status=reference_status,
        primary_support=(support_factors or ["基本面相对稳定"])[0],
        primary_risk=(risk_factors or ["暂无集中风险"])[0],
    )
    data_health = SimpleNamespace(completeness=completeness, updated_at=updated_at)
    return SimpleNamespace(
        stock=stock,
        summary=summary,
        data_health=data_health,
        support_factors=support_factors or [],
        risk_factors=risk_factors or [],
    )


class WatchlistIntelligenceTests(unittest.TestCase):
    def test_builds_priority_cautious_and_insufficient_insights(self):
        contexts = [
            make_context("600001", "优质样本", 82, "positive", support_factors=["评分较高", "趋势较稳"]),
            make_context("600002", "风险样本", 38, "cautious", risk_factors=["估值风险", "波动较高"]),
            make_context("600003", "缺数样本", 60, "watch", completeness="insufficient"),
        ]

        result = build_watchlist_intelligence(contexts)

        by_code = {item.code: item for item in result.insights}
        self.assertEqual(by_code["600001"].focus_level, "priority")
        self.assertEqual(by_code["600002"].focus_level, "cautious")
        self.assertEqual(by_code["600003"].focus_level, "insufficient_data")
        self.assertEqual(result.radar.priority_count, 1)
        self.assertEqual(result.radar.cautious_count, 1)
        self.assertEqual(result.radar.insufficient_count, 1)
        self.assertTrue(result.observations)
        self.assertIn("观察", result.radar.summary)

    def test_sort_watchlist_insights_by_risk_and_data_health(self):
        contexts = [
            make_context("600001", "低风险", 80, "positive", completeness="complete", risk_factors=[]),
            make_context("600002", "高风险", 45, "cautious", completeness="complete", risk_factors=["估值风险", "波动风险"]),
            make_context("600003", "缺数据", 70, "watch", completeness="insufficient", risk_factors=[]),
        ]
        result = build_watchlist_intelligence(contexts)

        risk_sorted = sort_watchlist_insights(result.insights, "risk")
        data_sorted = sort_watchlist_insights(result.insights, "data_health")

        self.assertEqual(risk_sorted[0].code, "600002")
        self.assertEqual(data_sorted[0].code, "600003")


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run failing tests**

Run:

```powershell
python -m pytest backend/tests/test_watchlist_intelligence.py -q
```

Expected: fails because `backend.app.watchlist_intelligence` does not exist.

- [x] **Step 3: Implement the rule module**

Create `backend/app/watchlist_intelligence.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


WatchlistFocusLevel = Literal["priority", "watch", "cautious", "insufficient_data"]
WatchlistSortMode = Literal["overall", "risk", "data_health", "recent_change"]
ObservationType = Literal["priority", "risk", "data_quality", "refresh", "balanced"]


@dataclass
class WatchlistStockInsightResult:
    code: str
    name: str
    focus_level: WatchlistFocusLevel
    focus_label: str
    focus_reason: str
    support_points: list[str] = field(default_factory=list)
    risk_points: list[str] = field(default_factory=list)
    data_completeness: str = "incomplete"
    score: int | None = None
    risk_score: int = 0
    priority_score: int = 0
    updated_at: datetime | None = None


@dataclass
class WatchlistRadarResult:
    title: str
    summary: str
    priority_count: int = 0
    cautious_count: int = 0
    insufficient_count: int = 0
    average_score: float | None = None


@dataclass
class WatchlistObservationResult:
    type: ObservationType
    title: str
    description: str
    stock_codes: list[str] = field(default_factory=list)


@dataclass
class WatchlistIntelligenceResult:
    radar: WatchlistRadarResult
    observations: list[WatchlistObservationResult] = field(default_factory=list)
    insights: list[WatchlistStockInsightResult] = field(default_factory=list)
    sort_modes: list[WatchlistSortMode] = field(default_factory=lambda: ["overall", "risk", "data_health", "recent_change"])


def _as_list(value) -> list[str]:
    return [str(item) for item in (value or []) if str(item).strip()]


def _data_completeness(context) -> str:
    data_health = getattr(context, "data_health", None)
    return getattr(data_health, "completeness", "incomplete")


def _updated_at(context):
    data_health = getattr(context, "data_health", None)
    stock = getattr(context, "stock", None)
    return getattr(data_health, "updated_at", None) or getattr(stock, "updated_at", None)


def _risk_score(risk_points: list[str], completeness: str, score: int | None) -> int:
    value = len(risk_points) * 20
    if completeness == "insufficient":
        value += 40
    elif completeness == "incomplete":
        value += 20
    if score is not None and score < 45:
        value += 25
    return min(value, 100)


def _priority_score(support_points: list[str], risk_score: int, score: int | None, completeness: str) -> int:
    value = len(support_points) * 15
    if score is not None:
        value += max(score - 50, 0)
    value -= risk_score // 2
    if completeness == "insufficient":
        value -= 50
    return max(min(value, 100), 0)


def _focus_for(summary, completeness: str, risk_score: int, priority_score: int) -> tuple[WatchlistFocusLevel, str, str]:
    reference_status = getattr(summary, "reference_status", "watch")
    if completeness == "insufficient":
        return "insufficient_data", "数据不足", "关键数据不足，相关结论只能弱参考。"
    if reference_status == "cautious" or risk_score >= 45:
        return "cautious", "谨慎关注", "风险因素较多，适合先查看风险解释和数据来源。"
    if reference_status == "positive" and priority_score >= 35:
        return "priority", "重点观察", "支撑因素相对更集中，可优先查看详情页确认依据。"
    return "watch", "继续观察", "当前适合保持观察，结合后续数据变化再复查。"


def _build_observations(insights: list[WatchlistStockInsightResult]) -> list[WatchlistObservationResult]:
    observations: list[WatchlistObservationResult] = []
    priority = [item.code for item in insights if item.focus_level == "priority"][:3]
    cautious = [item.code for item in insights if item.focus_level == "cautious"][:3]
    insufficient = [item.code for item in insights if item.focus_level == "insufficient_data"][:3]

    if priority:
        observations.append(WatchlistObservationResult(
            type="priority",
            title="优先复查重点观察股",
            description="这些自选股的支撑因素相对更集中，建议先查看详情页确认依据。",
            stock_codes=priority,
        ))
    if cautious:
        observations.append(WatchlistObservationResult(
            type="risk",
            title="先看风险较多的自选股",
            description="这些自选股存在较多风险因素，适合优先查看风险解释。",
            stock_codes=cautious,
        ))
    if insufficient:
        observations.append(WatchlistObservationResult(
            type="data_quality",
            title="补充数据不足的自选股",
            description="这些自选股关键数据不足，相关判断已降级为弱参考。",
            stock_codes=insufficient,
        ))
    if not observations:
        observations.append(WatchlistObservationResult(
            type="balanced",
            title="保持定期复查",
            description="当前自选股未出现集中风险或明显数据缺口，可按详情页逐只复查。",
            stock_codes=[],
        ))
    return observations


def build_watchlist_intelligence(stock_contexts) -> WatchlistIntelligenceResult:
    insights: list[WatchlistStockInsightResult] = []
    scores: list[int] = []

    for context in stock_contexts or []:
        stock = getattr(context, "stock", None)
        summary = getattr(context, "summary", None)
        if stock is None or summary is None:
            continue

        support_points = _as_list(getattr(context, "support_factors", None))
        if not support_points:
            primary_support = getattr(summary, "primary_support", None)
            support_points = _as_list([primary_support] if primary_support else [])

        risk_points = _as_list(getattr(context, "risk_factors", None))
        if not risk_points:
            primary_risk = getattr(summary, "primary_risk", None)
            risk_points = _as_list([primary_risk] if primary_risk else [])

        score = getattr(summary, "score", None)
        if isinstance(score, int):
            scores.append(score)

        completeness = _data_completeness(context)
        risk_score = _risk_score(risk_points, completeness, score)
        priority_score = _priority_score(support_points, risk_score, score, completeness)
        focus_level, focus_label, focus_reason = _focus_for(summary, completeness, risk_score, priority_score)

        insights.append(WatchlistStockInsightResult(
            code=getattr(stock, "code", getattr(summary, "code", "")),
            name=getattr(stock, "name", getattr(summary, "name", "")),
            focus_level=focus_level,
            focus_label=focus_label,
            focus_reason=focus_reason,
            support_points=support_points[:3],
            risk_points=risk_points[:3],
            data_completeness=completeness,
            score=score,
            risk_score=risk_score,
            priority_score=priority_score,
            updated_at=_updated_at(context),
        ))

    insights = sort_watchlist_insights(insights, "overall")
    priority_count = sum(1 for item in insights if item.focus_level == "priority")
    cautious_count = sum(1 for item in insights if item.focus_level == "cautious")
    insufficient_count = sum(1 for item in insights if item.focus_level == "insufficient_data")
    average_score = round(sum(scores) / len(scores), 1) if scores else None

    if insufficient_count:
        summary = f"今日自选股中有 {insufficient_count} 只数据不足，建议先补充数据后再参考。"
    elif cautious_count:
        summary = f"今日自选股中有 {cautious_count} 只风险较多，适合优先查看风险解释。"
    elif priority_count:
        summary = f"今日自选股中有 {priority_count} 只可重点观察，仍需结合详情页依据。"
    else:
        summary = "今日自选股整体适合继续观察，暂未出现集中风险或明显机会。"

    return WatchlistIntelligenceResult(
        radar=WatchlistRadarResult(
            title="自选股机会雷达",
            summary=summary,
            priority_count=priority_count,
            cautious_count=cautious_count,
            insufficient_count=insufficient_count,
            average_score=average_score,
        ),
        observations=_build_observations(insights),
        insights=insights,
    )


def sort_watchlist_insights(insights, mode: WatchlistSortMode) -> list[WatchlistStockInsightResult]:
    items = list(insights or [])
    if mode == "risk":
        return sorted(items, key=lambda item: (item.risk_score, item.priority_score), reverse=True)
    if mode == "data_health":
        order = {"insufficient": 0, "incomplete": 1, "mostly_complete": 2, "complete": 3}
        return sorted(items, key=lambda item: (order.get(item.data_completeness, 1), -item.priority_score))
    if mode == "recent_change":
        return sorted(items, key=lambda item: item.updated_at or datetime.min, reverse=True)
    return sorted(items, key=lambda item: (item.priority_score, -item.risk_score), reverse=True)
```

- [x] **Step 4: Run rule tests**

Run:

```powershell
python -m pytest backend/tests/test_watchlist_intelligence.py -q
```

Expected: 2 passed.

- [x] **Step 5: Commit**

```powershell
git add backend/app/watchlist_intelligence.py backend/tests/test_watchlist_intelligence.py docs/superpowers/plans/2026-07-10-watchlist-intelligence.md
git commit -m "feat: add watchlist intelligence rules"
```

---

### Task 2: Watchlist Insights API Integration

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_user_admin_and_watchlist.py`

**Interfaces:**
- Consumes: `build_watchlist_intelligence(stock_contexts) -> WatchlistIntelligenceResult`
- Produces: `WatchlistInsights.intelligence: WatchlistIntelligence | None`

- [x] **Step 1: Add failing API tests**

Append this test method to `UserAdminAndWatchlistTest` in `backend/tests/test_user_admin_and_watchlist.py`:

```python
    def test_watchlist_insights_returns_intelligence(self):
      self.db.add_all([
          Stock(code="600101", name="重点样本", price=10.0, change_percent=1.2, score=82, signal="buy", data_status="normal", updated_at=datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)),
          Stock(code="600102", name="谨慎样本", price=8.0, change_percent=-2.1, score=38, signal="sell", data_status="normal", updated_at=datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)),
          WatchlistItem(user_id=self.user_a.id, stock_code="600101", created_at=datetime.now(timezone.utc)),
          WatchlistItem(user_id=self.user_a.id, stock_code="600102", created_at=datetime.now(timezone.utc)),
      ])
      self.db.commit()

      alice_token = self._login("alice", "Alice@123!")
      response = self.client.get("/api/watchlist/insights", headers={"Authorization": f"Bearer {alice_token}"})

      self.assertEqual(response.status_code, 200, response.text)
      payload = response.json()
      self.assertIn("intelligence", payload)
      intelligence = payload["intelligence"]
      self.assertIn("radar", intelligence)
      self.assertIn("observations", intelligence)
      self.assertIn("insights", intelligence)
      self.assertGreaterEqual(len(intelligence["insights"]), 2)
      self.assertIn("观察", intelligence["radar"]["summary"])
      self.assertTrue(any(item["focus_level"] in ["priority", "cautious", "watch", "insufficient_data"] for item in intelligence["insights"]))
```

Update `test_watchlist_insights_returns_data_health_overview` to guard the corrected count with the existing partial stock:

```python
      overview = response.json()["data_health_overview"]
      self.assertEqual(overview["total"], 1)
      self.assertGreaterEqual(overview["insufficient_count"], 1)
      self.assertIn("数据", overview["message"])
```

If the file currently contains mojibake string literals for `"数据"`, keep the existing local literal style used in that file.

- [x] **Step 2: Run failing API test**

Run:

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_watchlist_insights_returns_intelligence -q
```

Expected: fails because `intelligence` is not present.

- [x] **Step 3: Add backend imports and models**

In `backend/app/main.py`, extend the existing ordinary-user import block:

```python
from app.watchlist_intelligence import (
    build_watchlist_intelligence,
)
```

Add these Pydantic models near `WatchlistDataHealthOverview`:

```python
WatchlistFocusLevel = Literal["priority", "watch", "cautious", "insufficient_data"]
WatchlistSortMode = Literal["overall", "risk", "data_health", "recent_change"]
ObservationType = Literal["priority", "risk", "data_quality", "refresh", "balanced"]


class WatchlistStockInsight(BaseModel):
    code: str
    name: str
    focus_level: WatchlistFocusLevel
    focus_label: str
    focus_reason: str
    support_points: list[str] = Field(default_factory=list)
    risk_points: list[str] = Field(default_factory=list)
    data_completeness: DataCompleteness = "incomplete"
    score: int | None = None
    risk_score: int = 0
    priority_score: int = 0
    updated_at: datetime | None = None


class WatchlistRadar(BaseModel):
    title: str = "自选股机会雷达"
    summary: str = "当前自选股适合继续观察。"
    priority_count: int = 0
    cautious_count: int = 0
    insufficient_count: int = 0
    average_score: float | None = None


class WatchlistObservation(BaseModel):
    type: ObservationType
    title: str
    description: str
    stock_codes: list[str] = Field(default_factory=list)


class WatchlistIntelligence(BaseModel):
    radar: WatchlistRadar
    observations: list[WatchlistObservation] = Field(default_factory=list)
    insights: list[WatchlistStockInsight] = Field(default_factory=list)
    sort_modes: list[WatchlistSortMode] = Field(default_factory=lambda: ["overall", "risk", "data_health", "recent_change"])
```

Extend `WatchlistInsights`:

```python
class WatchlistInsights(BaseModel):
    total: int
    groups: dict[ReferenceStatus, list[StockSummary]]
    risk_overview: str
    data_updated_at: datetime | None = None
    disclaimer: str = "仅供学习和分析参考，不构成投资建议。"
    data_health_overview: WatchlistDataHealthOverview | None = None
    intelligence: WatchlistIntelligence | None = None
```

If the current file uses mojibake string literals for the disclaimer, keep the existing literal unchanged and add only `intelligence`.

- [x] **Step 4: Add converters**

Add these helpers near the existing ordinary-user converters:

```python
def watchlist_intelligence_to_model(result) -> WatchlistIntelligence:
    return WatchlistIntelligence(
        radar=WatchlistRadar(**result.radar.__dict__),
        observations=[WatchlistObservation(**item.__dict__) for item in result.observations],
        insights=[WatchlistStockInsight(**item.__dict__) for item in result.insights],
        sort_modes=result.sort_modes,
    )
```

- [x] **Step 5: Integrate in `get_watchlist_insights`**

Inside `get_watchlist_insights`, replace the single `insufficient_count` variable with explicit counters and collect contexts:

```python
    latest_updated_at = None
    data_insufficient_count = 0
    data_incomplete_count = 0
    stock_contexts = []
```

Inside the stock loop, after `summary = stock_to_summary(stock)`:

```python
        data_health_result = build_data_health(stock)
        if data_health_result.completeness == "insufficient":
            data_insufficient_count += 1
        if data_health_result.completeness == "incomplete":
            data_incomplete_count += 1
        stock_contexts.append(SimpleNamespace(
            stock=stock,
            summary=summary,
            data_health=data_health_result,
            support_factors=summary.support_reasons,
            risk_factors=summary.risk_reasons,
        ))
```

If `SimpleNamespace` is not already imported, add:

```python
from types import SimpleNamespace
```

Keep:

```python
        groups[summary.reference_status].append(summary)
```

After the loop, use group count separately:

```python
    cautious_count = len(groups["cautious"])
    group_insufficient_count = len(groups["insufficient_data"])
```

Use `group_insufficient_count` for `risk_overview`, and use `data_insufficient_count` / `data_incomplete_count` for `health_message`.

Before the return:

```python
    intelligence_result = build_watchlist_intelligence(stock_contexts)
```

Add to `WatchlistInsights(...)`:

```python
        intelligence=watchlist_intelligence_to_model(intelligence_result),
```

Use the corrected data-health overview:

```python
        data_health_overview=WatchlistDataHealthOverview(
            total=len(stocks),
            insufficient_count=data_insufficient_count,
            incomplete_count=data_incomplete_count,
            latest_updated_at=latest_updated_at,
            message=health_message,
        ),
```

- [x] **Step 6: Run API tests**

Run:

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_watchlist_insights_returns_intelligence backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTests::test_watchlist_insights_returns_data_health_overview -q
```

Expected: 2 passed.

- [x] **Step 7: Run backend regression**

Run:

```powershell
python -m pytest backend/tests -q
```

Expected: all backend tests pass.

- [x] **Step 8: Commit**

```powershell
git add backend/app/main.py backend/tests/test_user_admin_and_watchlist.py docs/superpowers/plans/2026-07-10-watchlist-intelligence.md
git commit -m "feat: expose watchlist intelligence insights"
```

---

### Task 3: Frontend Types and API Compatibility

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.test.ts`

**Interfaces:**
- Consumes: backend `WatchlistInsights.intelligence`
- Produces: frontend `WatchlistIntelligence` types

- [ ] **Step 1: Read Expo 56 docs before frontend changes**

Open:

```text
https://docs.expo.dev/versions/v56.0.0/
```

Confirm this task only changes TypeScript types and Vitest API tests; no Expo runtime API changes are needed.

- [ ] **Step 2: Extend frontend types**

In `frontend/src/types/index.ts`, add near the existing watchlist types:

```ts
export type WatchlistFocusLevel = 'priority' | 'watch' | 'cautious' | 'insufficient_data';
export type WatchlistSortMode = 'overall' | 'risk' | 'data_health' | 'recent_change';
export type ObservationType = 'priority' | 'risk' | 'data_quality' | 'refresh' | 'balanced';

export interface WatchlistStockInsight {
  code: string;
  name: string;
  focus_level: WatchlistFocusLevel;
  focus_label: string;
  focus_reason: string;
  support_points: string[];
  risk_points: string[];
  data_completeness: DataCompleteness;
  score?: number | null;
  risk_score: number;
  priority_score: number;
  updated_at?: string | null;
}

export interface WatchlistRadar {
  title: string;
  summary: string;
  priority_count: number;
  cautious_count: number;
  insufficient_count: number;
  average_score?: number | null;
}

export interface WatchlistObservation {
  type: ObservationType;
  title: string;
  description: string;
  stock_codes: string[];
}

export interface WatchlistIntelligence {
  radar: WatchlistRadar;
  observations: WatchlistObservation[];
  insights: WatchlistStockInsight[];
  sort_modes: WatchlistSortMode[];
}
```

Extend `WatchlistInsights`:

```ts
export interface WatchlistInsights {
  total: number;
  groups: Record<ReferenceStatus, StockSummary[]>;
  risk_overview: string;
  data_updated_at?: string | null;
  disclaimer: string;
  data_health_overview?: WatchlistDataHealthOverview | null;
  intelligence?: WatchlistIntelligence | null;
}
```

- [ ] **Step 3: Extend API test fixture**

In `frontend/src/services/api.test.ts`, add `intelligence` to the `watchlistInsights` fixture:

```ts
  intelligence: {
    radar: {
      title: '自选股机会雷达',
      summary: '今日自选股中有 1 只可重点观察，仍需结合详情页依据。',
      priority_count: 1,
      cautious_count: 0,
      insufficient_count: 0,
      average_score: 80,
    },
    observations: [
      {
        type: 'priority',
        title: '优先复查重点观察股',
        description: '这些自选股的支撑因素相对更集中，建议先查看详情页确认依据。',
        stock_codes: ['600519'],
      },
    ],
    insights: [
      {
        code: '600519',
        name: '贵州茅台',
        focus_level: 'priority',
        focus_label: '重点观察',
        focus_reason: '支撑因素相对更集中，可优先查看详情页确认依据。',
        support_points: ['评分较高'],
        risk_points: [],
        data_completeness: 'complete',
        score: 80,
        risk_score: 0,
        priority_score: 45,
        updated_at: '2026-07-09T10:00:00',
      },
    ],
    sort_modes: ['overall', 'risk', 'data_health', 'recent_change'],
  },
```

Add assertions in the `getWatchlistInsights` test:

```ts
expect(result.intelligence?.radar.title).toBe('自选股机会雷达');
expect(result.intelligence?.observations[0]?.type).toBe('priority');
expect(result.intelligence?.insights[0]?.focus_level).toBe('priority');
```

- [ ] **Step 4: Run frontend API tests**

Run:

```powershell
cd frontend
npm test -- --run src/services/api.test.ts
```

Expected: API tests pass.

- [ ] **Step 5: Run TypeScript**

Run:

```powershell
cd frontend
npx tsc --noEmit
```

Expected: TypeScript passes.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/types/index.ts frontend/src/services/api.test.ts docs/superpowers/plans/2026-07-10-watchlist-intelligence.md
git commit -m "feat: add watchlist intelligence client types"
```

---

### Task 4: Home Page Watchlist Intelligence UI

**Files:**
- Modify: `frontend/src/pages/HomeScreen.tsx`
- Modify: `frontend/src/i18n/locales/zh.ts`
- Modify: `frontend/src/i18n/locales/zh-Hant.ts`
- Modify: `frontend/src/i18n/locales/en.ts`

**Interfaces:**
- Consumes: `WatchlistInsights.intelligence`
- Produces: radar and read-only observations in the existing home watchlist insights panel

- [ ] **Step 1: Read Expo 56 docs before frontend changes**

Open:

```text
https://docs.expo.dev/versions/v56.0.0/
```

Confirm this task uses only React Native core components already present in the app: `View`, `Text`, `Pressable`, and `ActivityIndicator`.

- [ ] **Step 2: Add i18n labels**

In each locale under `home`, add:

```ts
watchlistRadar: '自选股机会雷达',
todayObservations: '今日观察建议',
relatedStocks: '相关自选股',
```

For English:

```ts
watchlistRadar: 'Watchlist radar',
todayObservations: 'Today observations',
relatedStocks: 'Related stocks',
```

For Traditional Chinese:

```ts
watchlistRadar: '自選股機會雷達',
todayObservations: '今日觀察建議',
relatedStocks: '相關自選股',
```

If the file currently displays mojibake in the local console, add the keys using the same object structure and do not rewrite unrelated locale content.

- [ ] **Step 3: Render radar after data health overview**

In `frontend/src/pages/HomeScreen.tsx`, inside the existing `watchlistInsights && (...)` block and after the `data_health_overview` block, add:

```tsx
              {watchlistInsights.intelligence?.radar && (
                <View style={styles.watchlistRadarCard}>
                  <Text style={styles.dataHealthTitle}>{t.home.watchlistRadar}</Text>
                  <Text style={styles.subtleText}>{watchlistInsights.intelligence.radar.summary}</Text>
                  <View style={styles.radarStatsRow}>
                    <Text style={styles.radarStatText}>
                      {watchlistInsights.intelligence.radar.priority_count} {groupTitle('positive', t)}
                    </Text>
                    <Text style={styles.radarStatText}>
                      {watchlistInsights.intelligence.radar.cautious_count} {groupTitle('cautious', t)}
                    </Text>
                    <Text style={styles.radarStatText}>
                      {watchlistInsights.intelligence.radar.insufficient_count} {groupTitle('insufficient_data', t)}
                    </Text>
                  </View>
                </View>
              )}
```

- [ ] **Step 4: Render observations after radar**

Below the radar block, add:

```tsx
              {Boolean(watchlistInsights.intelligence?.observations?.length) && (
                <View style={styles.observationBlock}>
                  <Text style={styles.dataHealthTitle}>{t.home.todayObservations}</Text>
                  {watchlistInsights.intelligence!.observations.slice(0, 3).map((observation) => (
                    <View key={`${observation.type}-${observation.title}`} style={styles.observationItem}>
                      <Text style={styles.insightName}>{observation.title}</Text>
                      <Text style={styles.insightReason}>{observation.description}</Text>
                      {Boolean(observation.stock_codes.length) && (
                        <Text style={styles.disclaimerText}>
                          {t.home.relatedStocks}: {observation.stock_codes.join(', ')}
                        </Text>
                      )}
                    </View>
                  ))}
                </View>
              )}
```

- [ ] **Step 5: Add styles**

Add to `StyleSheet.create`:

```ts
watchlistRadarCard: {
  backgroundColor: '#F8FAFC',
  borderColor: '#D1D5DB',
  borderRadius: 8,
  borderWidth: 1,
  gap: 8,
  padding: 12,
},
radarStatsRow: {
  flexDirection: 'row',
  flexWrap: 'wrap',
  gap: 8,
},
radarStatText: {
  backgroundColor: '#FFFFFF',
  borderColor: '#E5E7EB',
  borderRadius: 8,
  borderWidth: 1,
  color: '#374151',
  fontSize: 12,
  fontWeight: '700',
  paddingHorizontal: 8,
  paddingVertical: 5,
},
observationBlock: {
  gap: 8,
},
observationItem: {
  backgroundColor: '#FFFFFF',
  borderColor: '#E5E7EB',
  borderRadius: 8,
  borderWidth: 1,
  gap: 6,
  padding: 12,
},
```

- [ ] **Step 6: Run frontend tests and TypeScript**

Run:

```powershell
cd frontend
npm test -- --run
npx tsc --noEmit
```

Expected: tests and TypeScript pass.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/pages/HomeScreen.tsx frontend/src/i18n/locales/zh.ts frontend/src/i18n/locales/zh-Hant.ts frontend/src/i18n/locales/en.ts docs/superpowers/plans/2026-07-10-watchlist-intelligence.md
git commit -m "feat: show watchlist intelligence on home"
```

---

### Task 5: Verification, Roadmap, and Smoke Checks

**Files:**
- Modify: `docs/PRODUCT_COMMERCIALIZATION_ROADMAP.md`
- Modify: `docs/superpowers/plans/2026-07-10-watchlist-intelligence.md`

**Interfaces:**
- Verifies: all backend and frontend work from Tasks 1-4
- Produces: updated roadmap status for phase 2 first slice

- [ ] **Step 1: Run backend tests**

Run:

```powershell
python -m pytest backend/tests -q
```

Expected: all backend tests pass.

- [ ] **Step 2: Run frontend tests**

Run:

```powershell
cd frontend
npm test -- --run
```

Expected: all frontend tests pass.

- [ ] **Step 3: Run TypeScript**

Run:

```powershell
cd frontend
npx tsc --noEmit
```

Expected: TypeScript passes.

- [ ] **Step 4: Scan forbidden copy**

Run:

```powershell
rg -n "立即买入|强烈卖出|必涨|稳赚|最佳买点|今日牛股|必买股票" backend frontend docs --glob "!docs/superpowers/specs/2026-07-10-watchlist-intelligence-design.md" --glob "!docs/superpowers/plans/2026-07-10-watchlist-intelligence.md"
```

Expected: no user-facing implementation copy contains these phrases.

- [ ] **Step 5: Run API smoke**

Start backend if it is not running:

```powershell
python backend/start.py
```

In another shell:

```powershell
$login = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/auth/login -Method Post -ContentType 'application/json' -Body (@{ username = 'admin'; password = 'Test@bcd!234' } | ConvertTo-Json)
$headers = @{ Authorization = "Bearer $($login.token)" }
$insights = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/watchlist/insights -Headers $headers
$insights.intelligence.radar
$insights.intelligence.observations | Select-Object -First 1
$insights.intelligence.insights | Select-Object -First 1
```

Expected:

- `intelligence.radar` exists.
- `intelligence.observations` exists.
- `intelligence.insights` exists.
- Existing `groups` and `data_health_overview` still exist.

- [ ] **Step 6: Run web smoke**

Start web if it is not running:

```powershell
cd frontend
npm run web -- --port 8083
```

Open:

```text
http://localhost:8083
```

Expected:

- Home page still loads.
- Existing watchlist insights still appear.
- Data health overview still appears when present.
- Watchlist radar appears when `intelligence.radar` is present.
- Today observations appear when `intelligence.observations` is present.
- Clicking a stock still opens the existing stock detail page.

- [ ] **Step 7: Update roadmap**

In `docs/PRODUCT_COMMERCIALIZATION_ROADMAP.md`, update phase 2 status to show the first slice is in progress or partially complete. Use the existing encoding/style of the file and avoid rewriting unrelated sections. The semantic target is:

```markdown
- [ ] TODO 第 2 阶段：自选股智能参考增强（2A/2B 已完成）
```

In the phase 2 section heading, preserve TODO if 2C/2D are not complete, but add first-slice completion wording:

```markdown
## 5. 第 2 阶段：自选股智能参考增强（TODO，2A/2B 已完成）
```

- [ ] **Step 8: Commit verification and roadmap**

```powershell
git add docs/PRODUCT_COMMERCIALIZATION_ROADMAP.md docs/superpowers/plans/2026-07-10-watchlist-intelligence.md
git commit -m "docs: record watchlist intelligence first slice"
```

---

## Self-Review

### Spec Coverage

- 2A rule layer: Task 1.
- 2B API and home light enhancement: Tasks 2, 3, and 4.
- Backward compatible `/api/watchlist/insights`: Task 2.
- Data-health count fix: Task 2.
- No membership/payment/independent page/full holdings: Global Constraints.
- Expo 56 check before frontend changes: Tasks 3 and 4.
- Testing and smoke checks: Task 5.

### Placeholder Scan

This plan contains no TBD placeholders. Every task has concrete files, interfaces, commands, expected results, and code snippets.

### Type Consistency

- Backend dataclass `WatchlistIntelligenceResult` maps to Pydantic `WatchlistIntelligence`.
- Backend `WatchlistStockInsightResult.focus_level` maps to frontend `WatchlistStockInsight.focus_level`.
- Backend `WatchlistObservationResult.stock_codes` maps to frontend `WatchlistObservation.stock_codes`.
- `WatchlistInsights.intelligence` is optional on both backend and frontend.
