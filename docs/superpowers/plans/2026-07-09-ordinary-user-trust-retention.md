# Ordinary User Trust Retention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ordinary-user trust and retention phase by adding data health, risk explanations, and pre-trade checklists to the existing MVP without introducing membership or payment features.

**Architecture:** Add a focused backend rule module for ordinary-user product logic, then expose its outputs through existing stock detail and watchlist insight APIs. Extend frontend types first, then render lightweight data health on the home page and richer trust/retention panels on the stock detail page.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest/unittest, Expo 56, React Native 0.85, TypeScript, Vitest.

## Global Constraints

- Do not implement membership, subscription, payment, management backend, report export, professional edition, or complete holding-position management.
- Do not output direct trading commands such as “立即买入”, “强烈卖出”, “必涨”, “稳赚”, or “最佳买点”.
- All analysis remains learning and reference material, not investment advice.
- Keep existing API fields compatible: `data_completeness`, `data_updated_at`, `ordinary_summary`, `support_factors`, and `risk_factors` remain available.
- New API fields must be optional or have defaults so older cached responses do not break the frontend.
- Before modifying frontend code, read Expo 56 versioned docs at `https://docs.expo.dev/versions/v56.0.0/`.
- Use TDD for backend and frontend behavior changes.
- Commit after each task.

---

## Current Code Map

- `backend/app/main.py`: API models, stock detail assembly, watchlist insights, ordinary user MVP helper functions.
- `backend/tests/test_user_admin_and_watchlist.py`: Existing API tests for ordinary user fields, stock detail, and watchlist insights.
- `backend/tests/test_backtest_engine.py`: Backtest and history refresh tests; keep unrelated.
- `frontend/src/types/index.ts`: Shared frontend API types.
- `frontend/src/services/api.ts`: API client functions including `getWatchlistInsights`.
- `frontend/src/services/api.test.ts`: API service tests.
- `frontend/src/pages/HomeScreen.tsx`: Home page and watchlist insights UI.
- `frontend/src/pages/StockDetailScreen.tsx`: Stock detail page and ordinary summary UI.
- `frontend/src/i18n/locales/zh.ts`, `zh-Hant.ts`, `en.ts`: UI copy.

## Target Backend Interfaces

Create `backend/app/ordinary_user.py` with:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

DataCompleteness = Literal["complete", "mostly_complete", "incomplete", "insufficient"]
RiskLevel = Literal["low", "medium", "high"]
RiskType = Literal["valuation", "volatility", "fundamentals", "holder_change", "dividend", "data_quality"]
ChecklistMode = Literal["buy", "sell"]
ChecklistStatus = Literal["pass", "attention", "user_confirm", "insufficient_data"]


@dataclass
class DataHealthResult:
    completeness: DataCompleteness
    updated_at: datetime | None
    source_summary: list[str] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    downgrade_reasons: list[str] = field(default_factory=list)
    user_message: str = ""


@dataclass
class RiskExplanationResult:
    type: RiskType
    level: RiskLevel
    title: str
    what_it_means: str
    why_it_matters: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class ChecklistItemResult:
    key: str
    label: str
    status: ChecklistStatus
    explanation: str
    user_confirm_required: bool = False


@dataclass
class PreTradeChecklistResult:
    mode: ChecklistMode
    title: str
    completion_hint: str
    items: list[ChecklistItemResult] = field(default_factory=list)
```

Expose these functions:

```python
def build_data_health(stock, history=None, factors=None, alerts=None, holders=None, dividends=None) -> DataHealthResult: ...
def build_risk_explanations(stock, factors=None, alerts=None, holders=None, dividends=None, data_health=None) -> list[RiskExplanationResult]: ...
def build_pre_trade_checklist(stock, risk_explanations, data_health, mode: ChecklistMode) -> PreTradeChecklistResult: ...
```

In `backend/app/main.py`, add Pydantic models:

```python
RiskType = Literal["valuation", "volatility", "fundamentals", "holder_change", "dividend", "data_quality"]
ChecklistMode = Literal["buy", "sell"]
ChecklistStatus = Literal["pass", "attention", "user_confirm", "insufficient_data"]


class DataHealth(BaseModel):
    completeness: DataCompleteness = "incomplete"
    updated_at: datetime | None = None
    source_summary: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    downgrade_reasons: list[str] = Field(default_factory=list)
    user_message: str = "当前数据不完整，结论只能弱参考。"


class RiskExplanation(BaseModel):
    type: RiskType
    level: RiskLevel
    title: str
    what_it_means: str
    why_it_matters: str
    evidence: list[str] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    key: str
    label: str
    status: ChecklistStatus
    explanation: str
    user_confirm_required: bool = False


class PreTradeChecklist(BaseModel):
    mode: ChecklistMode
    title: str
    completion_hint: str
    items: list[ChecklistItem] = Field(default_factory=list)


class WatchlistDataHealthOverview(BaseModel):
    total: int = 0
    insufficient_count: int = 0
    incomplete_count: int = 0
    latest_updated_at: datetime | None = None
    message: str = "当前自选股数据健康状况可用于基础参考。"
```

Extend:

```python
class StockDetail(BaseModel):
    ...
    data_health: DataHealth | None = None
    risk_explanations: list[RiskExplanation] = Field(default_factory=list)
    buy_checklist: PreTradeChecklist | None = None
    sell_checklist: PreTradeChecklist | None = None


class WatchlistInsights(BaseModel):
    ...
    data_health_overview: WatchlistDataHealthOverview | None = None
```

## Target Frontend Interfaces

Extend `frontend/src/types/index.ts`:

```ts
export type RiskType = 'valuation' | 'volatility' | 'fundamentals' | 'holder_change' | 'dividend' | 'data_quality';
export type ChecklistMode = 'buy' | 'sell';
export type ChecklistStatus = 'pass' | 'attention' | 'user_confirm' | 'insufficient_data';

export interface DataHealth {
  completeness: DataCompleteness;
  updated_at?: string | null;
  source_summary: string[];
  missing_items: string[];
  downgrade_reasons: string[];
  user_message: string;
}

export interface RiskExplanation {
  type: RiskType;
  level: RiskLevel;
  title: string;
  what_it_means: string;
  why_it_matters: string;
  evidence: string[];
}

export interface ChecklistItem {
  key: string;
  label: string;
  status: ChecklistStatus;
  explanation: string;
  user_confirm_required: boolean;
}

export interface PreTradeChecklist {
  mode: ChecklistMode;
  title: string;
  completion_hint: string;
  items: ChecklistItem[];
}

export interface WatchlistDataHealthOverview {
  total: number;
  insufficient_count: number;
  incomplete_count: number;
  latest_updated_at?: string | null;
  message: string;
}
```

Extend:

```ts
export interface StockDetail {
  ...
  data_health?: DataHealth | null;
  risk_explanations?: RiskExplanation[];
  buy_checklist?: PreTradeChecklist | null;
  sell_checklist?: PreTradeChecklist | null;
}

export interface WatchlistInsights {
  ...
  data_health_overview?: WatchlistDataHealthOverview | null;
}
```

---

### Task 1: Backend Data Health Rule Module

**Files:**
- Create: `backend/app/ordinary_user.py`
- Test: `backend/tests/test_ordinary_user.py`

**Interfaces:**
- Produces: `DataHealthResult`, `build_data_health(stock, history=None, factors=None, alerts=None, holders=None, dividends=None) -> DataHealthResult`
- Consumed by: Task 2, Task 3, Task 4

- [x] **Step 1: Add failing data health tests**

Create `backend/tests/test_ordinary_user.py`:

```python
import unittest
from datetime import datetime
from types import SimpleNamespace

from backend.app.ordinary_user import build_data_health


class OrdinaryUserDataHealthTests(unittest.TestCase):
    def test_complete_data_health_when_core_data_present(self):
        stock = SimpleNamespace(data_status="normal", updated_at=datetime(2026, 7, 9, 10, 0))
        history = [SimpleNamespace(date=f"2026-06-{day:02d}") for day in range(1, 25)]
        factors = [
            SimpleNamespace(key="valuation"),
            SimpleNamespace(key="momentum"),
            SimpleNamespace(key="volatility"),
            SimpleNamespace(key="profitability"),
        ]

        result = build_data_health(stock, history=history, factors=factors, alerts=[], holders=[], dividends=[])

        self.assertEqual(result.completeness, "complete")
        self.assertEqual(result.updated_at, stock.updated_at)
        self.assertIn("本地历史行情", result.source_summary)
        self.assertIn("本地因子评分", result.source_summary)
        self.assertEqual(result.missing_items, [])
        self.assertIn("关键数据较完整", result.user_message)

    def test_insufficient_data_health_lists_missing_items(self):
        stock = SimpleNamespace(data_status="partial", updated_at=None)
        history = [SimpleNamespace(date="2026-06-01")]

        result = build_data_health(stock, history=history, factors=[], alerts=[], holders=[], dividends=[])

        self.assertEqual(result.completeness, "insufficient")
        self.assertIn("历史行情不足", result.missing_items)
        self.assertIn("财务和因子数据不足", result.missing_items)
        self.assertIn("数据不足", result.user_message)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run the failing tests**

Run:

```powershell
python -m pytest backend/tests/test_ordinary_user.py -q
```

Expected: fails because `backend.app.ordinary_user` does not exist.

- [x] **Step 3: Implement data health module**

Create `backend/app/ordinary_user.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

DataCompleteness = Literal["complete", "mostly_complete", "incomplete", "insufficient"]
RiskLevel = Literal["low", "medium", "high"]
RiskType = Literal["valuation", "volatility", "fundamentals", "holder_change", "dividend", "data_quality"]
ChecklistMode = Literal["buy", "sell"]
ChecklistStatus = Literal["pass", "attention", "user_confirm", "insufficient_data"]


@dataclass
class DataHealthResult:
    completeness: DataCompleteness
    updated_at: datetime | None
    source_summary: list[str] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    downgrade_reasons: list[str] = field(default_factory=list)
    user_message: str = ""


@dataclass
class RiskExplanationResult:
    type: RiskType
    level: RiskLevel
    title: str
    what_it_means: str
    why_it_matters: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class ChecklistItemResult:
    key: str
    label: str
    status: ChecklistStatus
    explanation: str
    user_confirm_required: bool = False


@dataclass
class PreTradeChecklistResult:
    mode: ChecklistMode
    title: str
    completion_hint: str
    items: list[ChecklistItemResult] = field(default_factory=list)


def _item_count(items) -> int:
    return len(items or [])


def build_data_health(stock, history=None, factors=None, alerts=None, holders=None, dividends=None) -> DataHealthResult:
    history_count = _item_count(history)
    factor_count = _item_count(factors)
    alert_count = _item_count(alerts)
    holder_count = _item_count(holders)
    dividend_count = _item_count(dividends)
    updated_at = getattr(stock, "updated_at", None)
    data_status = getattr(stock, "data_status", "normal")

    source_summary: list[str] = []
    missing_items: list[str] = []
    downgrade_reasons: list[str] = []

    if history_count >= 20:
        source_summary.append("本地历史行情")
    else:
        missing_items.append("历史行情不足")
        downgrade_reasons.append("历史行情样本少于 20 条")

    if factor_count >= 4:
        source_summary.append("本地因子评分")
    else:
        missing_items.append("财务和因子数据不足")
        downgrade_reasons.append("估值、趋势、波动或盈利因子不完整")

    if alert_count:
        source_summary.append("本地风险提示")
    if holder_count:
        source_summary.append("重要股东变动")
    else:
        missing_items.append("重要股东变动数据不足")
    if dividend_count:
        source_summary.append("分红记录")

    if data_status == "partial":
        downgrade_reasons.append("股票基础数据处于部分可用状态")
    if updated_at is None:
        missing_items.append("最近更新时间缺失")
        downgrade_reasons.append("无法确认数据新鲜度")

    if history_count < 20 or factor_count < 2 or updated_at is None:
        completeness: DataCompleteness = "insufficient"
        user_message = "当前数据不足，暂不适合形成明确判断。"
    elif data_status == "partial" or factor_count < 4:
        completeness = "incomplete"
        user_message = "当前关键数据不完整，结论只能弱参考。"
    elif holder_count == 0:
        completeness = "mostly_complete"
        user_message = "当前主要数据基本完整，但重要股东变动数据仍需补充。"
    else:
        completeness = "complete"
        user_message = "当前关键数据较完整，结论可信度相对较高。"

    return DataHealthResult(
        completeness=completeness,
        updated_at=updated_at,
        source_summary=source_summary,
        missing_items=list(dict.fromkeys(missing_items)),
        downgrade_reasons=list(dict.fromkeys(downgrade_reasons)),
        user_message=user_message,
    )
```

- [x] **Step 4: Run data health tests**

Run:

```powershell
python -m pytest backend/tests/test_ordinary_user.py -q
```

Expected: 2 passed.

- [x] **Step 5: Commit**

```powershell
git add backend/app/ordinary_user.py backend/tests/test_ordinary_user.py
git commit -m "feat: add ordinary user data health rules"
```

---

### Task 2: Backend Risk Explanation Rules

**Files:**
- Modify: `backend/app/ordinary_user.py`
- Test: `backend/tests/test_ordinary_user.py`

**Interfaces:**
- Consumes: `DataHealthResult`
- Produces: `build_risk_explanations(stock, factors=None, alerts=None, holders=None, dividends=None, data_health=None) -> list[RiskExplanationResult]`
- Consumed by: Task 3, Task 4

- [x] **Step 1: Add failing risk explanation tests**

Append to `OrdinaryUserDataHealthTests` in `backend/tests/test_ordinary_user.py`:

```python
    def test_risk_explanations_include_valuation_and_volatility(self):
        from backend.app.ordinary_user import build_risk_explanations

        stock = SimpleNamespace(score=42, signal="sell", data_status="normal", updated_at=datetime(2026, 7, 9, 10, 0))
        factors = [
            SimpleNamespace(key="valuation", label="估值", value=35, description="估值偏高。"),
            SimpleNamespace(key="volatility", label="波动", value=30, description="波动偏高。"),
        ]
        data_health = build_data_health(stock, history=[SimpleNamespace(date=str(i)) for i in range(30)], factors=factors)

        risks = build_risk_explanations(stock, factors=factors, alerts=[], holders=[], dividends=[], data_health=data_health)

        self.assertTrue(any(risk.type == "valuation" for risk in risks))
        self.assertTrue(any(risk.type == "volatility" for risk in risks))
        self.assertTrue(all(risk.what_it_means for risk in risks))
        self.assertTrue(all(risk.why_it_matters for risk in risks))

    def test_risk_explanations_include_data_quality_when_data_insufficient(self):
        from backend.app.ordinary_user import build_risk_explanations

        stock = SimpleNamespace(score=70, signal="buy", data_status="partial", updated_at=None)
        data_health = build_data_health(stock, history=[], factors=[])

        risks = build_risk_explanations(stock, factors=[], alerts=[], holders=[], dividends=[], data_health=data_health)

        self.assertTrue(any(risk.type == "data_quality" for risk in risks))
        self.assertTrue(any("数据不足" in risk.title for risk in risks))
```

- [x] **Step 2: Run the failing tests**

Run:

```powershell
python -m pytest backend/tests/test_ordinary_user.py -q
```

Expected: fails because `build_risk_explanations` is missing.

- [x] **Step 3: Implement risk explanation rules**

Append to `backend/app/ordinary_user.py`:

```python
def _factor_value(factors, key: str) -> int | None:
    for factor in factors or []:
        if getattr(factor, "key", "") == key:
            return getattr(factor, "value", None)
    return None


def _factor_description(factors, key: str) -> str | None:
    for factor in factors or []:
        if getattr(factor, "key", "") == key:
            return getattr(factor, "description", None)
    return None


def build_risk_explanations(stock, factors=None, alerts=None, holders=None, dividends=None, data_health=None) -> list[RiskExplanationResult]:
    risks: list[RiskExplanationResult] = []
    factors = factors or []
    alerts = alerts or []
    holders = holders or []
    dividends = dividends or []

    valuation = _factor_value(factors, "valuation")
    if valuation is not None and valuation < 45:
        risks.append(RiskExplanationResult(
            type="valuation",
            level="high" if valuation < 35 else "medium",
            title="估值风险",
            what_it_means="当前估值指标偏弱，价格可能已经反映较多乐观预期。",
            why_it_matters="如果后续业绩增长跟不上，股价可能承压。",
            evidence=[_factor_description(factors, "valuation") or f"估值因子为 {valuation} 分"],
        ))

    volatility = _factor_value(factors, "volatility")
    if volatility is not None and volatility < 45:
        risks.append(RiskExplanationResult(
            type="volatility",
            level="high" if volatility < 35 else "medium",
            title="波动风险",
            what_it_means="近期价格波动偏高，短期回撤可能超出普通用户预期。",
            why_it_matters="波动较大时，用户更容易因短期涨跌做出情绪化决策。",
            evidence=[_factor_description(factors, "volatility") or f"波动因子为 {volatility} 分"],
        ))

    profitability = _factor_value(factors, "profitability")
    if profitability is not None and profitability < 45:
        risks.append(RiskExplanationResult(
            type="fundamentals",
            level="medium",
            title="业绩质量风险",
            what_it_means="盈利质量或基本面因子偏弱。",
            why_it_matters="基本面偏弱时，价格上涨更依赖情绪或短期资金推动。",
            evidence=[_factor_description(factors, "profitability") or f"盈利因子为 {profitability} 分"],
        ))

    negative_holder_changes = [
        holder for holder in holders
        if getattr(holder, "change_amount", 0) is not None and getattr(holder, "change_amount", 0) < 0
    ]
    if negative_holder_changes:
        risks.append(RiskExplanationResult(
            type="holder_change",
            level="medium",
            title="重要股东变动风险",
            what_it_means="重要持有人出现减持迹象。",
            why_it_matters="连续或明显减持可能带来筹码压力，需要结合公告和价格表现继续观察。",
            evidence=[f"发现 {len(negative_holder_changes)} 条重要股东减持记录"],
        ))

    if not dividends:
        risks.append(RiskExplanationResult(
            type="dividend",
            level="low",
            title="分红稳定性信息不足",
            what_it_means="当前缺少可用于判断分红稳定性的记录。",
            why_it_matters="分红记录不足时，不能把长期持有回报作为强支撑因素。",
            evidence=["未读取到分红记录"],
        ))

    high_alerts = [alert for alert in alerts if getattr(alert, "level", "") == "high"]
    for alert in high_alerts[:2]:
        risks.append(RiskExplanationResult(
            type="fundamentals",
            level="high",
            title=getattr(alert, "title", "高风险提示"),
            what_it_means=getattr(alert, "message", "系统发现高风险提示。"),
            why_it_matters="高风险提示可能影响普通用户的风险承受判断。",
            evidence=[getattr(alert, "message", "高风险提示")],
        ))

    if data_health and data_health.completeness in ("insufficient", "incomplete"):
        risks.insert(0, RiskExplanationResult(
            type="data_quality",
            level="high" if data_health.completeness == "insufficient" else "medium",
            title="数据不足风险",
            what_it_means=data_health.user_message,
            why_it_matters="数据不足时，系统不应形成过强结论，用户需要先补充或刷新数据。",
            evidence=data_health.missing_items or data_health.downgrade_reasons,
        ))

    return risks[:6]
```

- [x] **Step 4: Run risk explanation tests**

Run:

```powershell
python -m pytest backend/tests/test_ordinary_user.py -q
```

Expected: all tests pass.

- [x] **Step 5: Commit**

```powershell
git add backend/app/ordinary_user.py backend/tests/test_ordinary_user.py
git commit -m "feat: add ordinary user risk explanations"
```

---

### Task 3: Backend Pre-Trade Checklist Rules

**Files:**
- Modify: `backend/app/ordinary_user.py`
- Test: `backend/tests/test_ordinary_user.py`

**Interfaces:**
- Consumes: `RiskExplanationResult`, `DataHealthResult`
- Produces: `build_pre_trade_checklist(stock, risk_explanations, data_health, mode: ChecklistMode) -> PreTradeChecklistResult`
- Consumed by: Task 4

- [x] **Step 1: Add failing checklist tests**

Append to `OrdinaryUserDataHealthTests`:

```python
    def test_buy_checklist_contains_system_and_user_confirmation_items(self):
        from backend.app.ordinary_user import build_pre_trade_checklist, build_risk_explanations

        stock = SimpleNamespace(score=42, signal="sell", data_status="normal", updated_at=datetime(2026, 7, 9, 10, 0))
        factors = [SimpleNamespace(key="valuation", label="估值", value=35, description="估值偏高。")]
        data_health = build_data_health(stock, history=[SimpleNamespace(date=str(i)) for i in range(30)], factors=factors)
        risks = build_risk_explanations(stock, factors=factors, data_health=data_health)

        checklist = build_pre_trade_checklist(stock, risks, data_health, mode="buy")

        self.assertEqual(checklist.mode, "buy")
        self.assertTrue(any(item.key == "understand_business" and item.user_confirm_required for item in checklist.items))
        self.assertTrue(any(item.key == "valuation_risk" and item.status == "attention" for item in checklist.items))
        self.assertIn("检查", checklist.completion_hint)

    def test_sell_checklist_contains_panic_check(self):
        from backend.app.ordinary_user import build_pre_trade_checklist

        stock = SimpleNamespace(score=70, signal="neutral", data_status="normal", updated_at=datetime(2026, 7, 9, 10, 0))
        data_health = build_data_health(stock, history=[SimpleNamespace(date=str(i)) for i in range(30)], factors=[SimpleNamespace(key="valuation", value=65)] * 4)

        checklist = build_pre_trade_checklist(stock, [], data_health, mode="sell")

        self.assertEqual(checklist.mode, "sell")
        self.assertTrue(any(item.key == "avoid_panic" for item in checklist.items))
```

- [x] **Step 2: Run failing checklist tests**

Run:

```powershell
python -m pytest backend/tests/test_ordinary_user.py -q
```

Expected: fails because `build_pre_trade_checklist` is missing.

- [x] **Step 3: Implement checklist rules**

Append to `backend/app/ordinary_user.py`:

```python
def _has_risk(risks: list[RiskExplanationResult], risk_type: RiskType) -> bool:
    return any(risk.type == risk_type for risk in risks)


def _risk_status(risks: list[RiskExplanationResult], risk_type: RiskType) -> ChecklistStatus:
    return "attention" if _has_risk(risks, risk_type) else "pass"


def build_pre_trade_checklist(stock, risk_explanations, data_health, mode: ChecklistMode) -> PreTradeChecklistResult:
    risks = risk_explanations or []
    data_status: ChecklistStatus = "insufficient_data" if data_health.completeness in ("insufficient", "incomplete") else "pass"

    if mode == "buy":
        items = [
            ChecklistItemResult(
                key="understand_business",
                label="我是否了解公司主营业务？",
                status="user_confirm",
                explanation="如果不了解公司靠什么赚钱，就不适合只凭短期涨跌做判断。",
                user_confirm_required=True,
            ),
            ChecklistItemResult(
                key="valuation_risk",
                label="当前估值是否偏高？",
                status=_risk_status(risks, "valuation"),
                explanation="估值偏高时，需要确认未来业绩增长是否能支撑当前价格。",
            ),
            ChecklistItemResult(
                key="holder_change",
                label="是否存在重要股东明显减持？",
                status=_risk_status(risks, "holder_change"),
                explanation="重要股东减持可能带来筹码压力，需要继续观察公告和价格表现。",
            ),
            ChecklistItemResult(
                key="drawdown_tolerance",
                label="如果下跌 10%-20%，我是否能接受？",
                status="user_confirm",
                explanation="普通用户需要先确认自己能否承受可能回撤，再考虑后续动作。",
                user_confirm_required=True,
            ),
            ChecklistItemResult(
                key="data_quality",
                label="当前数据是否足够形成判断？",
                status=data_status,
                explanation=data_health.user_message,
            ),
        ]
        return PreTradeChecklistResult(
            mode="buy",
            title="买入前检查",
            completion_hint="完成这些检查后，再结合仓位和个人风险承受能力判断。",
            items=items,
        )

    items = [
        ChecklistItemResult(
            key="thesis_invalid",
            label="买入逻辑是否已经失效？",
            status="user_confirm",
            explanation="先确认原来的关注理由是否改变，避免只因短期波动做决定。",
            user_confirm_required=True,
        ),
        ChecklistItemResult(
            key="fundamental_risk",
            label="业绩或基本面是否明显恶化？",
            status=_risk_status(risks, "fundamentals"),
            explanation="如果基本面风险变高，需要重新评估继续持有的理由。",
        ),
        ChecklistItemResult(
            key="valuation_risk",
            label="估值是否已经过高？",
            status=_risk_status(risks, "valuation"),
            explanation="估值过高时，后续收益更依赖业绩继续超预期。",
        ),
        ChecklistItemResult(
            key="avoid_panic",
            label="是否只是因为短期波动而恐慌？",
            status="user_confirm",
            explanation="短期波动不一定代表长期逻辑失效，需要和风险证据一起看。",
            user_confirm_required=True,
        ),
        ChecklistItemResult(
            key="data_quality",
            label="当前数据是否足够支持判断？",
            status=data_status,
            explanation=data_health.user_message,
        ),
    ]
    return PreTradeChecklistResult(
        mode="sell",
        title="卖出前检查",
        completion_hint="先区分逻辑失效和短期波动，再决定是否继续观察。",
        items=items,
    )
```

- [x] **Step 4: Run checklist tests**

Run:

```powershell
python -m pytest backend/tests/test_ordinary_user.py -q
```

Expected: all tests pass.

- [x] **Step 5: Commit**

```powershell
git add backend/app/ordinary_user.py backend/tests/test_ordinary_user.py
git commit -m "feat: add ordinary user pre-trade checklists"
```

---

### Task 4: Integrate Backend API Responses

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_user_admin_and_watchlist.py`

**Interfaces:**
- Consumes: `build_data_health`, `build_risk_explanations`, `build_pre_trade_checklist`
- Produces: `StockDetail.data_health`, `StockDetail.risk_explanations`, `StockDetail.buy_checklist`, `StockDetail.sell_checklist`, `WatchlistInsights.data_health_overview`

- [x] **Step 1: Add failing API tests**

In `backend/tests/test_user_admin_and_watchlist.py`, add:

```python
    def test_stock_detail_returns_data_health_risk_explanations_and_checklists(self):
        self.db.add(Stock(code="600000", name="浦发银行", price=8.1, change_percent=-1.2, score=42, signal="sell", data_status="normal"))
        for index in range(30):
            self.db.add(PricePointDB(stock_code="600000", date=f"2026-06-{index + 1:02d}", open=8, high=8.3, low=7.9, close=8.0, volume=10000))
        self.db.add(FactorScoreDB(stock_code="600000", key="valuation", label="估值", value=35, description="估值偏高。"))
        self.db.add(FactorScoreDB(stock_code="600000", key="volatility", label="波动", value=30, description="波动偏高。"))
        self.db.commit()

        alice_token = self._login("alice", "Alice@123!")
        response = self.client.get("/api/stocks/600000", headers={"Authorization": f"Bearer {alice_token}"})

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertIn("data_health", payload)
        self.assertIn("risk_explanations", payload)
        self.assertIn("buy_checklist", payload)
        self.assertIn("sell_checklist", payload)
        self.assertTrue(payload["risk_explanations"])
        self.assertEqual(payload["buy_checklist"]["mode"], "buy")
        self.assertEqual(payload["sell_checklist"]["mode"], "sell")

    def test_watchlist_insights_returns_data_health_overview(self):
        self.db.add_all([
            Stock(code="600010", name="包钢股份", price=1.2, change_percent=0.1, score=50, signal="neutral", data_status="partial"),
            WatchlistItem(user_id=self.user_a.id, stock_code="600010", created_at=datetime.now(timezone.utc)),
        ])
        self.db.commit()

        alice_token = self._login("alice", "Alice@123!")
        response = self.client.get("/api/watchlist/insights", headers={"Authorization": f"Bearer {alice_token}"})

        self.assertEqual(response.status_code, 200, response.text)
        overview = response.json()["data_health_overview"]
        self.assertEqual(overview["total"], 1)
        self.assertGreaterEqual(overview["insufficient_count"], 1)
        self.assertIn("数据", overview["message"])
```

- [x] **Step 2: Run failing API tests**

Run:

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_stock_detail_returns_data_health_risk_explanations_and_checklists backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_watchlist_insights_returns_data_health_overview -q
```

Expected: fails because new API fields are absent.

- [x] **Step 3: Add Pydantic models and converters**

In `backend/app/main.py`, import:

```python
from app.ordinary_user import (
    ChecklistMode,
    ChecklistStatus,
    RiskType,
    build_data_health,
    build_pre_trade_checklist,
    build_risk_explanations,
)
```

Add models after `PricePoint`:

```python
class DataHealth(BaseModel):
    completeness: DataCompleteness = "incomplete"
    updated_at: datetime | None = None
    source_summary: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    downgrade_reasons: list[str] = Field(default_factory=list)
    user_message: str = "当前数据不完整，结论只能弱参考。"


class RiskExplanation(BaseModel):
    type: RiskType
    level: RiskLevel
    title: str
    what_it_means: str
    why_it_matters: str
    evidence: list[str] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    key: str
    label: str
    status: ChecklistStatus
    explanation: str
    user_confirm_required: bool = False


class PreTradeChecklist(BaseModel):
    mode: ChecklistMode
    title: str
    completion_hint: str
    items: list[ChecklistItem] = Field(default_factory=list)


class WatchlistDataHealthOverview(BaseModel):
    total: int = 0
    insufficient_count: int = 0
    incomplete_count: int = 0
    latest_updated_at: datetime | None = None
    message: str = "当前自选股数据健康状况可用于基础参考。"
```

Extend `StockDetail` and `WatchlistInsights` as specified in Target Backend Interfaces.

Add converters near `stock_to_summary`:

```python
def data_health_to_model(result) -> DataHealth:
    return DataHealth(**result.__dict__)


def risk_explanation_to_model(result) -> RiskExplanation:
    return RiskExplanation(**result.__dict__)


def checklist_to_model(result) -> PreTradeChecklist:
    return PreTradeChecklist(
        mode=result.mode,
        title=result.title,
        completion_hint=result.completion_hint,
        items=[ChecklistItem(**item.__dict__) for item in result.items],
    )
```

- [x] **Step 4: Integrate into stock detail**

In `get_stock_detail`, after `alert_models`:

```python
    holder_rows = db.query(InstHoldDB).filter(InstHoldDB.stock_code == code).all()
    dividend_rows = db.query(DividendDB).filter(DividendDB.ts_code == _stock_ts_code(stock)).all()
    data_health_result = build_data_health(stock, history, factor_models, alert_models, holder_rows, dividend_rows)
    risk_results = build_risk_explanations(stock, factor_models, alert_models, holder_rows, dividend_rows, data_health_result)
    buy_checklist_result = build_pre_trade_checklist(stock, risk_results, data_health_result, mode="buy")
    sell_checklist_result = build_pre_trade_checklist(stock, risk_results, data_health_result, mode="sell")
```

In `StockDetail(...)`, add:

```python
        data_health=data_health_to_model(data_health_result),
        risk_explanations=[risk_explanation_to_model(result) for result in risk_results],
        buy_checklist=checklist_to_model(buy_checklist_result),
        sell_checklist=checklist_to_model(sell_checklist_result),
```

- [x] **Step 5: Integrate into watchlist insights**

In `get_watchlist_insights`, before the stock loop:

```python
    insufficient_count = 0
    incomplete_count = 0
```

Inside the stock loop after `summary = stock_to_summary(stock)`:

```python
        data_health_result = build_data_health(stock)
        if data_health_result.completeness == "insufficient":
            insufficient_count += 1
        if data_health_result.completeness == "incomplete":
            incomplete_count += 1
```

Before return:

```python
    if insufficient_count:
        health_message = f"当前自选股中有 {insufficient_count} 只数据不足，相关结论已降级。"
    elif incomplete_count:
        health_message = f"当前自选股中有 {incomplete_count} 只数据不完整，建议结合详情页继续查看。"
    else:
        health_message = "当前自选股数据健康状况可用于基础参考。"
```

Add to `WatchlistInsights(...)`:

```python
        data_health_overview=WatchlistDataHealthOverview(
            total=len(stocks),
            insufficient_count=insufficient_count,
            incomplete_count=incomplete_count,
            latest_updated_at=latest_updated_at,
            message=health_message,
        ),
```

- [x] **Step 6: Run API tests**

Run:

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_stock_detail_returns_data_health_risk_explanations_and_checklists backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_watchlist_insights_returns_data_health_overview -q
```

Expected: both pass.

- [x] **Step 7: Run backend regression**

Run:

```powershell
python -m pytest backend/tests -q
```

Expected: all backend tests pass.

- [x] **Step 8: Commit**

```powershell
git add backend/app/main.py backend/tests/test_user_admin_and_watchlist.py
git commit -m "feat: expose ordinary user trust signals"
```

---

### Task 5: Frontend Types and API Compatibility

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.test.ts`

**Interfaces:**
- Consumes: backend `data_health`, `risk_explanations`, `buy_checklist`, `sell_checklist`, `data_health_overview`
- Produces: TypeScript types for UI tasks

- [x] **Step 1: Read Expo 56 docs before frontend changes**

Open:

```text
https://docs.expo.dev/versions/v56.0.0/
```

Confirm this task only changes TypeScript types and tests; no Expo runtime API changes are needed.

- [x] **Step 2: Extend frontend types**

In `frontend/src/types/index.ts`, add the target frontend interfaces from the Target Frontend Interfaces section.

Extend `StockDetail` and `WatchlistInsights` with:

```ts
  data_health?: DataHealth | null;
  risk_explanations?: RiskExplanation[];
  buy_checklist?: PreTradeChecklist | null;
  sell_checklist?: PreTradeChecklist | null;
```

and:

```ts
  data_health_overview?: WatchlistDataHealthOverview | null;
```

- [x] **Step 3: Extend API tests**

In `frontend/src/services/api.test.ts`, update the `getWatchlistInsights` mock response to include:

```ts
data_health_overview: {
  total: 1,
  insufficient_count: 0,
  incomplete_count: 0,
  latest_updated_at: '2026-07-09T10:00:00',
  message: '当前自选股数据健康状况可用于基础参考。',
},
```

Add an assertion:

```ts
expect(result.data_health_overview?.message).toContain('数据健康');
```

If the current exact message does not contain `数据健康`, assert the exact expected string:

```ts
expect(result.data_health_overview?.message).toBe('当前自选股数据健康状况可用于基础参考。');
```

- [x] **Step 4: Run frontend API tests**

Run:

```powershell
cd frontend
npm test -- --run src/services/api.test.ts
```

Expected: API tests pass.

- [x] **Step 5: Run TypeScript**

Run:

```powershell
cd frontend
npx tsc --noEmit
```

Expected: TypeScript passes.

- [x] **Step 6: Commit**

```powershell
git add frontend/src/types/index.ts frontend/src/services/api.test.ts
git commit -m "feat: add ordinary user trust client types"
```

---

### Task 6: Home Page Data Health Overview

**Files:**
- Modify: `frontend/src/pages/HomeScreen.tsx`
- Modify: `frontend/src/i18n/locales/zh.ts`
- Modify: `frontend/src/i18n/locales/zh-Hant.ts`
- Modify: `frontend/src/i18n/locales/en.ts`

**Interfaces:**
- Consumes: `WatchlistInsights.data_health_overview`
- Produces: Home page data health message under watchlist insights

- [x] **Step 1: Read Expo 56 docs before frontend changes**

Open:

```text
https://docs.expo.dev/versions/v56.0.0/
```

Confirm this task uses only React Native core components already present in the app: `View`, `Text`, and `ActivityIndicator`.

- [x] **Step 2: Add i18n labels**

In each locale under `home`, add equivalent labels:

```ts
dataHealthOverview: '数据健康概览',
dataUpdatedAt: '数据更新时间',
```

English:

```ts
dataHealthOverview: 'Data health overview',
dataUpdatedAt: 'Data updated at',
```

- [x] **Step 3: Render overview in HomeScreen**

In `frontend/src/pages/HomeScreen.tsx`, inside the existing `watchlistInsights && (...)` block, render after `risk_overview`:

```tsx
{watchlistInsights.data_health_overview && (
  <View style={styles.dataHealthStrip}>
    <Text style={styles.dataHealthTitle}>{t.home.dataHealthOverview}</Text>
    <Text style={styles.subtleText}>{watchlistInsights.data_health_overview.message}</Text>
    {watchlistInsights.data_health_overview.latest_updated_at && (
      <Text style={styles.disclaimerText}>
        {t.home.dataUpdatedAt}: {formatUpdatedAt(
          watchlistInsights.data_health_overview.latest_updated_at,
          locale === 'zh' ? 'zh-CN' : locale === 'zh-Hant' ? 'zh-TW' : 'en-US',
          t.formatter.updated,
        )}
      </Text>
    )}
  </View>
)}
```

Use the existing `formatUpdatedAt` import if it is already imported. If not, import it from `../utils/formatters` using the existing local path pattern.

- [x] **Step 4: Add styles**

Add to `StyleSheet.create`:

```ts
dataHealthStrip: {
  backgroundColor: '#F8FAFC',
  borderColor: '#E5E7EB',
  borderRadius: 8,
  borderWidth: 1,
  gap: 6,
  padding: 12,
},
dataHealthTitle: {
  color: '#162033',
  fontSize: 13,
  fontWeight: '700',
},
```

- [x] **Step 5: Run frontend tests and TypeScript**

Run:

```powershell
cd frontend
npm test -- --run
npx tsc --noEmit
```

Expected: tests and TypeScript pass.

- [x] **Step 6: Commit**

```powershell
git add frontend/src/pages/HomeScreen.tsx frontend/src/i18n/locales/zh.ts frontend/src/i18n/locales/zh-Hant.ts frontend/src/i18n/locales/en.ts
git commit -m "feat: show watchlist data health overview"
```

---

### Task 7: Stock Detail Risk Explanation and Checklist UI

**Files:**
- Modify: `frontend/src/pages/StockDetailScreen.tsx`
- Modify: `frontend/src/i18n/locales/zh.ts`
- Modify: `frontend/src/i18n/locales/zh-Hant.ts`
- Modify: `frontend/src/i18n/locales/en.ts`

**Interfaces:**
- Consumes: `StockDetail.data_health`, `risk_explanations`, `buy_checklist`, `sell_checklist`
- Produces: Detail page panels for data health, risk explanation, and pre-trade checklist

- [x] **Step 1: Read Expo 56 docs before frontend changes**

Open:

```text
https://docs.expo.dev/versions/v56.0.0/
```

Confirm this task uses `View`, `Text`, `Pressable`, and local component state only.

- [x] **Step 2: Add i18n labels**

In each locale under `detail`, add equivalent labels:

```ts
riskExplanation: '风险说明书',
whatItMeans: '风险是什么',
whyItMatters: '为什么重要',
evidence: '当前证据',
preTradeChecklist: '操作前检查',
buyChecklist: '买入前检查',
sellChecklist: '卖出前检查',
checklistHint: '检查提示',
missingData: '缺失数据',
conclusionDowngraded: '结论降级原因',
```

English:

```ts
riskExplanation: 'Risk explanation',
whatItMeans: 'What it means',
whyItMatters: 'Why it matters',
evidence: 'Evidence',
preTradeChecklist: 'Pre-trade checklist',
buyChecklist: 'Before buying',
sellChecklist: 'Before selling',
checklistHint: 'Checklist note',
missingData: 'Missing data',
conclusionDowngraded: 'Downgrade reasons',
```

- [x] **Step 3: Add checklist tab state**

In `StockDetailScreen.tsx`, add:

```tsx
const [activeChecklistMode, setActiveChecklistMode] = useState<'buy' | 'sell'>('buy');
```

Place it with other state declarations.

- [x] **Step 4: Render richer data health panel**

Replace the current single data health row inside `summaryPanel` with:

```tsx
<View style={styles.dataHealthBlock}>
  <View style={styles.dataHealthRow}>
    <Text style={styles.dataHealthLabel}>{t.detail.dataHealth}</Text>
    <Text style={styles.dataHealthValue}>{detail.data_health?.completeness ?? detail.data_completeness ?? detail.data_status}</Text>
  </View>
  {detail.data_health?.user_message && (
    <Text style={styles.summaryText}>{detail.data_health.user_message}</Text>
  )}
  {Boolean(detail.data_health?.missing_items?.length) && (
    <Text style={styles.disclaimerText}>
      {t.detail.missingData}: {detail.data_health!.missing_items.join('、')}
    </Text>
  )}
  {Boolean(detail.data_health?.downgrade_reasons?.length) && (
    <Text style={styles.disclaimerText}>
      {t.detail.conclusionDowngraded}: {detail.data_health!.downgrade_reasons.join('、')}
    </Text>
  )}
</View>
```

- [x] **Step 5: Render risk explanations before factor section**

Add before the existing factor section:

```tsx
{Boolean(detail.risk_explanations?.length) && (
  <View style={styles.reasonPanel}>
    <Text style={styles.sectionTitle}>{t.detail.riskExplanation}</Text>
    {detail.risk_explanations!.map((risk) => (
      <View key={`${risk.type}-${risk.title}`} style={styles.riskExplanationCard}>
        <Text style={styles.riskTitle}>{risk.title}</Text>
        <Text style={styles.reasonText}>{t.detail.whatItMeans}: {risk.what_it_means}</Text>
        <Text style={styles.reasonText}>{t.detail.whyItMatters}: {risk.why_it_matters}</Text>
        {Boolean(risk.evidence.length) && (
          <Text style={styles.disclaimerText}>{t.detail.evidence}: {risk.evidence.join('、')}</Text>
        )}
      </View>
    ))}
  </View>
)}
```

- [x] **Step 6: Render checklist panel**

Add after risk explanations:

```tsx
{(detail.buy_checklist || detail.sell_checklist) && (
  <View style={styles.reasonPanel}>
    <Text style={styles.sectionTitle}>{t.detail.preTradeChecklist}</Text>
    <View style={styles.checklistTabs}>
      <Pressable
        style={[styles.checklistTab, activeChecklistMode === 'buy' && styles.checklistTabActive]}
        onPress={() => setActiveChecklistMode('buy')}
      >
        <Text style={[styles.checklistTabText, activeChecklistMode === 'buy' && styles.checklistTabTextActive]}>
          {t.detail.buyChecklist}
        </Text>
      </Pressable>
      <Pressable
        style={[styles.checklistTab, activeChecklistMode === 'sell' && styles.checklistTabActive]}
        onPress={() => setActiveChecklistMode('sell')}
      >
        <Text style={[styles.checklistTabText, activeChecklistMode === 'sell' && styles.checklistTabTextActive]}>
          {t.detail.sellChecklist}
        </Text>
      </Pressable>
    </View>
    {(() => {
      const checklist = activeChecklistMode === 'buy' ? detail.buy_checklist : detail.sell_checklist;
      if (!checklist) return null;
      return (
        <View style={styles.checklistBody}>
          <Text style={styles.summaryText}>{checklist.completion_hint}</Text>
          {checklist.items.map((item) => (
            <View key={item.key} style={styles.checklistItem}>
              <Text style={styles.riskTitle}>{item.label}</Text>
              <Text style={styles.reasonText}>{item.explanation}</Text>
            </View>
          ))}
        </View>
      );
    })()}
  </View>
)}
```

- [x] **Step 7: Add styles**

Add to `StyleSheet.create`:

```ts
dataHealthBlock: {
  gap: 8,
},
riskExplanationCard: {
  backgroundColor: '#F8FAFC',
  borderColor: '#E5E7EB',
  borderRadius: 8,
  borderWidth: 1,
  gap: 8,
  padding: 12,
},
riskTitle: {
  color: '#162033',
  fontSize: 14,
  fontWeight: '700',
},
checklistTabs: {
  flexDirection: 'row',
  gap: 8,
},
checklistTab: {
  alignItems: 'center',
  borderColor: '#E5E7EB',
  borderRadius: 8,
  borderWidth: 1,
  flex: 1,
  paddingVertical: 10,
},
checklistTabActive: {
  backgroundColor: '#E9FBF7',
  borderColor: '#0F8B8D',
},
checklistTabText: {
  color: '#6B7280',
  fontSize: 13,
  fontWeight: '700',
},
checklistTabTextActive: {
  color: '#0F8B8D',
},
checklistBody: {
  gap: 10,
},
checklistItem: {
  backgroundColor: '#FFFFFF',
  borderColor: '#E5E7EB',
  borderRadius: 8,
  borderWidth: 1,
  gap: 6,
  padding: 12,
},
```

- [x] **Step 8: Run frontend tests and TypeScript**

Run:

```powershell
cd frontend
npm test -- --run
npx tsc --noEmit
```

Expected: tests and TypeScript pass.

- [x] **Step 9: Commit**

```powershell
git add frontend/src/pages/StockDetailScreen.tsx frontend/src/i18n/locales/zh.ts frontend/src/i18n/locales/zh-Hant.ts frontend/src/i18n/locales/en.ts
git commit -m "feat: show ordinary user risk and checklist panels"
```

---

### Task 8: Verification, Roadmap Status, and Smoke Checks

**Files:**
- Modify: `docs/PRODUCT_COMMERCIALIZATION_ROADMAP.md`
- Modify if needed: `docs/superpowers/plans/2026-07-09-ordinary-user-trust-retention.md`

**Interfaces:**
- Verifies: all backend and frontend work from Tasks 1-7
- Produces: updated roadmap status only if all verification passes

- [x] **Step 1: Run backend tests**

Run:

```powershell
python -m pytest backend/tests -q
```

Expected: all backend tests pass.

- [x] **Step 2: Run frontend tests**

Run:

```powershell
cd frontend
npm test -- --run
```

Expected: all frontend tests pass.

- [x] **Step 3: Run TypeScript**

Run:

```powershell
cd frontend
npx tsc --noEmit
```

Expected: TypeScript passes.

- [x] **Step 4: Run API smoke**

Start backend if it is not running:

```powershell
python backend/start.py
```

In another shell:

```powershell
$login = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/auth/login -Method Post -ContentType 'application/json' -Body (@{ username = 'admin'; password = 'Test@bcd!234' } | ConvertTo-Json)
$headers = @{ Authorization = "Bearer $($login.token)" }
$insights = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/watchlist/insights -Headers $headers
$detail = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/stocks/600519 -Headers $headers
$insights.data_health_overview
$detail.data_health
$detail.risk_explanations | Select-Object -First 1
$detail.buy_checklist
```

Expected:

- `data_health_overview` exists.
- `data_health` exists.
- `risk_explanations` contains at least one item when data or risk conditions exist.
- `buy_checklist.mode` is `buy`.
- `sell_checklist.mode` is `sell`.

- [x] **Step 5: Run Web smoke**

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
- “今日自选股参考” still appears for authenticated data.
- Data health overview appears when `data_health_overview` is present.
- Stock detail shows ordinary summary, data health, risk explanation, and checklist panels.
- No page text contains “立即买入”, “强烈卖出”, “必涨”, “稳赚”, or “最佳买点”.

- [x] **Step 6: Mark roadmap stage 1 complete only after verification passes**

In `docs/PRODUCT_COMMERCIALIZATION_ROADMAP.md`, change the unchecked stage 1 roadmap item to:

```markdown
- [x] 第 1 阶段：普通用户可信度与留存增强
```

Change the stage 1 heading to:

```markdown
## 4. 第 1 阶段：普通用户可信度与留存增强（已完成）
```

- [x] **Step 7: Commit verification and roadmap**

```powershell
git add docs/PRODUCT_COMMERCIALIZATION_ROADMAP.md docs/superpowers/plans/2026-07-09-ordinary-user-trust-retention.md
git commit -m "docs: complete ordinary user trust retention phase"
```

---

## Self-Review

### Spec Coverage

- MVP validation: Task 8.
- Data health center v1: Tasks 1, 4, 5, 6, 7.
- Risk explanation v1: Tasks 2, 4, 5, 7.
- Pre-trade checklist v1: Tasks 3, 4, 5, 7.
- API compatibility: Tasks 4 and 5 keep existing fields and add optional frontend fields.
- No membership/payment/professional scope: Global Constraints.
- Expo 56 requirement: Tasks 5, 6, and 7 include explicit documentation checks before frontend code changes.

### Placeholder Scan

This plan contains no placeholder implementation steps. Every task has exact files, function names, code snippets, commands, and expected results.

### Type Consistency

Backend dataclass result names map to Pydantic response names:

- `DataHealthResult` -> `DataHealth`
- `RiskExplanationResult` -> `RiskExplanation`
- `ChecklistItemResult` -> `ChecklistItem`
- `PreTradeChecklistResult` -> `PreTradeChecklist`

Frontend interfaces use the same JSON field names as backend Pydantic models.
