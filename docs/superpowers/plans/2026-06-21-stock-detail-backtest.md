# Stock Detail Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace simulated stock-detail strategy results with deterministic, explainable backtests generated from TuShare-backed OHLCV history.

**Architecture:** Add a focused backend backtest engine that normalizes price bars, generates long-only trades for the three existing templates, and computes metrics from the equity curve. Wire existing FastAPI strategy summary/detail/custom backtest endpoints to that engine. Update the React Native hook so strategy expansion fetches backend detail instead of building mock detail locally.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, standard-library `unittest`, Expo SDK 56, React Native 0.85.3, React 19.2.3, TypeScript 6.0.3.

## Global Constraints

- Expo code must follow SDK 56 constraints from `https://docs.expo.dev/versions/v56.0.0/`.
- Do not add new Expo or React Native packages unless required; if required, install with `npx expo install`.
- Preserve existing API response shapes: `StrategyResult`, `BacktestTrade`, `StrategyDetail`, and `BacktestRequest`.
- Do not add database tables for detailed trades in this phase.
- Use existing `price_history` data and existing TuShare refresh path before backtest calculation.
- Keep the first phase long-only, deterministic, and explainable.
- Existing unrelated modified files in the working tree must not be reverted.

---

## File Structure

- Create `backend/app/backtest_engine.py`: pure backtest domain logic with no FastAPI or database dependency.
- Create `backend/tests/test_backtest_engine.py`: standard-library unit tests for the engine.
- Modify `backend/app/main.py`: convert DB price rows to engine bars and use engine output in strategy endpoints.
- Modify `src/hooks/useStockData.ts`: call `getStrategyDetail` and cache backend details.
- No frontend component layout changes are required for this phase.

---

### Task 1: Backend Backtest Engine

**Files:**
- Create: `backend/app/backtest_engine.py`
- Create: `backend/tests/test_backtest_engine.py`

**Interfaces:**
- Produces: `PriceBar`, `BacktestTradeRecord`, `BacktestResult`, `normalize_price_bars(items: list[object]) -> list[PriceBar]`, `run_backtest(strategy_id: str, items: list[object], name: str | None = None, lookback_days: int | None = None, risk: str | None = None) -> BacktestResult | None`, `build_strategy_summaries(items: list[object]) -> list[BacktestResult]`
- Consumes: input objects with `date` or `trade_date`, `open`, `high`, `low`, `close`, and `volume` attributes or dict keys.

- [ ] **Step 1: Write failing engine tests**

Create `backend/tests/test_backtest_engine.py`:

```python
import unittest

from backend.app.backtest_engine import build_strategy_summaries, normalize_price_bars, run_backtest


def make_bar(day: int, close: float, volume: int = 1000) -> dict:
    date = f"2024-01-{day:02d}" if day <= 31 else f"2024-02-{day - 31:02d}"
    return {
        "date": date,
        "open": close - 0.2,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": volume,
    }


class BacktestEngineTests(unittest.TestCase):
    def test_normalize_price_bars_sorts_ascending_and_uses_trade_date(self):
        bars = normalize_price_bars([
            {"trade_date": "20240103", "close": 11, "vol": 300},
            {"trade_date": "20240101", "close": 10, "vol": 100},
        ])

        self.assertEqual([bar.date for bar in bars], ["2024-01-01", "2024-01-03"])
        self.assertEqual(bars[0].volume, 100)

    def test_trend_breakout_generates_real_trade_and_positive_return(self):
        prices = [10] * 20 + [10.5, 11, 11.8, 12.5, 13.4, 14.2, 15, 15.8, 16.3, 17.0, 17.8, 18.4]
        result = run_backtest("trend-breakout", [make_bar(i + 1, price, 1500 + i * 10) for i, price in enumerate(prices)])

        self.assertIsNotNone(result)
        assert result is not None
        self.assertGreater(result.return_rate, 0)
        self.assertGreaterEqual(result.trade_count, 1)
        self.assertTrue(any(trade.action == "buy" for trade in result.trades))
        self.assertIn("moving average", " ".join(result.rules).lower())

    def test_falling_sequence_limits_drawdown_and_does_not_fake_win_rate(self):
        prices = [20 - i * 0.25 for i in range(45)]
        result = run_backtest("dividend-defense", [make_bar(i + 1, price) for i, price in enumerate(prices)])

        self.assertIsNotNone(result)
        assert result is not None
        self.assertLessEqual(result.win_rate, 100)
        self.assertGreaterEqual(result.win_rate, 0)
        self.assertLessEqual(result.max_drawdown, 0)

    def test_insufficient_history_returns_none(self):
        result = run_backtest("trend-breakout", [make_bar(i + 1, 10 + i) for i in range(10)])

        self.assertIsNone(result)

    def test_build_strategy_summaries_returns_existing_templates(self):
        prices = [10 + i * 0.2 for i in range(60)]
        results = build_strategy_summaries([make_bar(i + 1, price) for i, price in enumerate(prices)])

        self.assertEqual({result.template for result in results}, {
            "trend-breakout",
            "low-valuation-reversal",
            "dividend-defense",
        })


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest backend.tests.test_backtest_engine -v
```

Expected: FAIL or ERROR because `backend.app.backtest_engine` does not exist.

- [ ] **Step 3: Implement minimal backtest engine**

Create `backend/app/backtest_engine.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from statistics import pstdev
from typing import Any


VALID_TEMPLATES = {"trend-breakout", "low-valuation-reversal", "dividend-defense"}


@dataclass(frozen=True)
class PriceBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class BacktestTradeRecord:
    date: str
    action: str
    price: float
    quantity: int
    reason: str


@dataclass(frozen=True)
class BacktestResult:
    template: str
    id: str
    name: str
    period: str
    return_rate: float
    max_drawdown: float
    win_rate: float
    risk: str
    summary: str
    annualized_return: float
    sharpe_ratio: float
    trade_count: int
    rules: list[str]
    trades: list[BacktestTradeRecord]


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _format_date(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def normalize_price_bars(items: list[Any]) -> list[PriceBar]:
    bars: list[PriceBar] = []
    for item in items:
        date = _format_date(_get_value(item, "date") or _get_value(item, "trade_date"))
        close = float(_get_value(item, "close", 0) or 0)
        if not date or close <= 0:
            continue
        open_price = float(_get_value(item, "open", close) or close)
        high = float(_get_value(item, "high", max(open_price, close)) or max(open_price, close))
        low = float(_get_value(item, "low", min(open_price, close)) or min(open_price, close))
        volume = int(_get_value(item, "volume", _get_value(item, "vol", 0)) or 0)
        bars.append(PriceBar(date=date, open=open_price, high=high, low=low, close=close, volume=volume))
    return sorted(bars, key=lambda bar: bar.date)


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _drawdown(equity_curve: list[float]) -> float:
    peak = equity_curve[0] if equity_curve else 0
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)
    return -round(max_drawdown, 2)


def _annualized_return(total_return: float, first_date: str, last_date: str) -> float:
    try:
        start = datetime.strptime(first_date, "%Y-%m-%d")
        end = datetime.strptime(last_date, "%Y-%m-%d")
    except ValueError:
        return round(total_return, 2)
    days = max((end - start).days, 1)
    return round(total_return * 365 / days, 2)


def _sharpe_ratio(equity_curve: list[float]) -> float:
    returns = [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] > 0
    ]
    if len(returns) < 2:
        return 0.0
    volatility = pstdev(returns)
    if volatility == 0:
        return 0.0
    return round((_average(returns) / volatility) * sqrt(252), 2)


def _base_rules(template: str) -> list[str]:
    return {
        "trend-breakout": [
            "Buy when close crosses above the 20-day moving average.",
            "Sell when close falls below the 20-day moving average or stop-loss is triggered.",
            "Volume expansion strengthens the breakout reason when available.",
        ],
        "low-valuation-reversal": [
            "Buy when price recovers from the recent low range.",
            "Sell when price reverts toward the recent high range or stop-loss is triggered.",
            "Use recent price range as a valuation proxy until valuation data is available.",
        ],
        "dividend-defense": [
            "Buy only when trend is stable and realized volatility is moderate.",
            "Sell when trend weakens, volatility rises, or stop-loss is triggered.",
            "Use defensive price behavior as a dividend proxy until dividend data is available.",
        ],
    }[template]


def _signal(template: str, bars: list[PriceBar], index: int, in_position: bool, entry_price: float) -> tuple[str | None, str]:
    close = bars[index].close
    window = bars[max(0, index - 19):index + 1]
    ma20 = _average([bar.close for bar in window])
    recent = bars[max(0, index - 29):index + 1]
    recent_low = min(bar.close for bar in recent)
    recent_high = max(bar.close for bar in recent)
    range_width = max(recent_high - recent_low, 0.01)
    range_position = (close - recent_low) / range_width
    volatility_window = bars[max(0, index - 9):index + 1]
    daily_moves = [
        abs(volatility_window[i].close - volatility_window[i - 1].close) / volatility_window[i - 1].close
        for i in range(1, len(volatility_window))
        if volatility_window[i - 1].close > 0
    ]
    volatility = _average(daily_moves)
    stop_loss_hit = in_position and entry_price > 0 and close <= entry_price * 0.92

    if template == "trend-breakout":
        previous_close = bars[index - 1].close if index > 0 else close
        previous_ma = _average([bar.close for bar in bars[max(0, index - 20):index]])
        if not in_position and previous_close <= previous_ma and close > ma20:
            return "buy", "Close crossed above the 20-day moving average."
        if in_position and (close < ma20 or stop_loss_hit):
            return "sell", "Close fell below the 20-day moving average or stop-loss was hit."
    elif template == "low-valuation-reversal":
        previous = bars[index - 1].close if index > 0 else close
        if not in_position and range_position < 0.35 and close > previous:
            return "buy", "Price recovered from the recent low range."
        if in_position and (range_position > 0.72 or stop_loss_hit):
            return "sell", "Price reverted toward the recent high range or stop-loss was hit."
    elif template == "dividend-defense":
        if not in_position and close >= ma20 and volatility <= 0.025:
            return "buy", "Trend was stable with moderate realized volatility."
        if in_position and (close < ma20 or volatility > 0.04 or stop_loss_hit):
            return "sell", "Trend weakened, volatility rose, or stop-loss was hit."
    return None, ""


def run_backtest(
    strategy_id: str,
    items: list[Any],
    name: str | None = None,
    lookback_days: int | None = None,
    risk: str | None = None,
) -> BacktestResult | None:
    template = next((candidate for candidate in VALID_TEMPLATES if candidate in strategy_id), strategy_id)
    if template not in VALID_TEMPLATES:
        return None
    bars = normalize_price_bars(items)
    if lookback_days:
        bars = bars[-lookback_days:]
    if len(bars) < 30:
        return None

    initial_cash = 100000.0
    cash = initial_cash
    quantity = 0
    entry_price = 0.0
    entry_value = 0.0
    wins = 0
    losses = 0
    trades: list[BacktestTradeRecord] = []
    equity_curve: list[float] = []

    for index, bar in enumerate(bars):
        action, reason = _signal(template, bars, index, quantity > 0, entry_price)
        if action == "buy" and quantity == 0:
            lot_quantity = int(cash // (bar.close * 100)) * 100
            if lot_quantity > 0:
                quantity = lot_quantity
                cash -= quantity * bar.close
                entry_price = bar.close
                entry_value = quantity * bar.close
                trades.append(BacktestTradeRecord(bar.date, "buy", round(bar.close, 2), quantity, reason))
        elif action == "sell" and quantity > 0:
            proceeds = quantity * bar.close
            cash += proceeds
            if proceeds >= entry_value:
                wins += 1
            else:
                losses += 1
            trades.append(BacktestTradeRecord(bar.date, "sell", round(bar.close, 2), quantity, reason))
            quantity = 0
            entry_price = 0.0
            entry_value = 0.0
        equity_curve.append(cash + quantity * bar.close)

    if quantity > 0:
        last = bars[-1]
        proceeds = quantity * last.close
        cash += proceeds
        if proceeds >= entry_value:
            wins += 1
        else:
            losses += 1
        trades.append(BacktestTradeRecord(last.date, "sell", round(last.close, 2), quantity, "Closed open position at the end of the backtest."))
        quantity = 0
        equity_curve[-1] = cash

    final_equity = equity_curve[-1] if equity_curve else initial_cash
    total_return = (final_equity - initial_cash) / initial_cash * 100
    closed_trades = wins + losses
    win_rate = wins / closed_trades * 100 if closed_trades else 0.0
    display_name = name or {
        "trend-breakout": "Trend Breakout",
        "low-valuation-reversal": "Low Valuation Reversal",
        "dividend-defense": "Dividend Defense",
    }[template]
    risk_value = risk or ("high" if template == "trend-breakout" and abs(_drawdown(equity_curve)) > 12 else "low" if template == "dividend-defense" else "medium")

    return BacktestResult(
        template=template,
        id=strategy_id,
        name=display_name,
        period=f"Last {len(bars)} bars",
        return_rate=round(total_return, 2),
        max_drawdown=_drawdown(equity_curve),
        win_rate=round(win_rate, 1),
        risk=risk_value,
        summary=f"{display_name} backtest completed from {bars[0].date} to {bars[-1].date}.",
        annualized_return=_annualized_return(total_return, bars[0].date, bars[-1].date),
        sharpe_ratio=_sharpe_ratio(equity_curve),
        trade_count=len(trades),
        rules=_base_rules(template),
        trades=trades,
    )


def build_strategy_summaries(items: list[Any]) -> list[BacktestResult]:
    results: list[BacktestResult] = []
    for template in ["trend-breakout", "low-valuation-reversal", "dividend-defense"]:
        result = run_backtest(template, items)
        if result:
            results.append(result)
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m unittest backend.tests.test_backtest_engine -v
```

Expected: PASS for all five tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/backtest_engine.py backend/tests/test_backtest_engine.py
git commit -m "feat: add stock backtest engine"
```

---

### Task 2: Wire Backend Endpoints To Engine

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_backtest_engine.py`

**Interfaces:**
- Consumes: `build_strategy_summaries(items)`, `run_backtest(strategy_id, items, name=None, lookback_days=None, risk=None)`
- Produces: existing FastAPI models `StrategyResult` and `StrategyDetail` backed by real engine results.

- [ ] **Step 1: Write failing integration-style unit tests for model conversion**

Append to `backend/tests/test_backtest_engine.py`:

```python
from backend.app.main import engine_result_to_detail, engine_result_to_strategy


class BacktestApiConversionTests(unittest.TestCase):
    def test_engine_result_converts_to_existing_strategy_models(self):
        prices = [10] * 20 + [10.5, 11, 11.8, 12.5, 13.4, 14.2, 15, 15.8, 16.3, 17.0, 17.8, 18.4]
        result = run_backtest("trend-breakout", [make_bar(i + 1, price) for i, price in enumerate(prices)])
        assert result is not None

        summary = engine_result_to_strategy(result)
        detail = engine_result_to_detail(result)

        self.assertEqual(summary.id, "trend-breakout")
        self.assertEqual(detail.strategy.id, "trend-breakout")
        self.assertEqual(detail.trade_count, len(result.trades))
        self.assertEqual(detail.trades[0].action, "buy")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m unittest backend.tests.test_backtest_engine.BacktestApiConversionTests -v
```

Expected: FAIL or ERROR because `engine_result_to_detail` and `engine_result_to_strategy` are not defined.

- [ ] **Step 3: Add conversion helpers and replace simplified backend calculations**

Modify `backend/app/main.py` imports:

```python
from backend.app.backtest_engine import BacktestResult, build_strategy_summaries, run_backtest
```

Add helpers near existing DB/model converters:

```python
def engine_result_to_strategy(result: BacktestResult) -> StrategyResult:
    return StrategyResult(
        id=result.id,
        name=result.name,
        period=result.period,
        return_rate=result.return_rate,
        max_drawdown=result.max_drawdown,
        win_rate=result.win_rate,
        risk=result.risk,
        summary=result.summary,
    )


def engine_result_to_detail(result: BacktestResult) -> StrategyDetail:
    return StrategyDetail(
        strategy=engine_result_to_strategy(result),
        annualized_return=result.annualized_return,
        sharpe_ratio=result.sharpe_ratio,
        trade_count=result.trade_count,
        rules=result.rules,
        trades=[
            BacktestTrade(
                date=trade.date,
                action=trade.action,
                price=trade.price,
                quantity=trade.quantity,
                reason=trade.reason,
            )
            for trade in result.trades
        ],
    )
```

Replace `calculate_strategies` body with:

```python
def calculate_strategies(daily_data: list) -> list:
    return [
        {
            "id": result.id,
            "name": result.name,
            "period": result.period,
            "return_rate": result.return_rate,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "risk": result.risk,
            "summary": result.summary,
        }
        for result in build_strategy_summaries(daily_data)
    ]
```

Replace `build_strategy_detail` body with:

```python
def build_strategy_detail(detail: StockDetail, strategy: StrategyResult) -> StrategyDetail:
    result = run_backtest(
        strategy.id,
        detail.history,
        name=strategy.name,
        risk=strategy.risk,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Insufficient price history for backtest")
    return engine_result_to_detail(result)
```

Replace `build_custom_backtest` body with:

```python
def build_custom_backtest(detail: StockDetail, request: BacktestRequest) -> StrategyDetail:
    strategy_id = f"custom-{request.template}-{request.lookback_days}-{int(datetime.now().timestamp())}"
    result = run_backtest(
        request.template,
        detail.history,
        name=request.name.strip() or None,
        lookback_days=request.lookback_days,
        risk=request.risk,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Insufficient price history for backtest")
    result = BacktestResult(
        template=result.template,
        id=strategy_id,
        name=result.name,
        period=f"Last {request.lookback_days} days",
        return_rate=result.return_rate,
        max_drawdown=result.max_drawdown,
        win_rate=result.win_rate,
        risk=result.risk,
        summary=result.summary,
        annualized_return=result.annualized_return,
        sharpe_ratio=result.sharpe_ratio,
        trade_count=result.trade_count,
        rules=result.rules,
        trades=result.trades,
    )
    return engine_result_to_detail(result)
```

- [ ] **Step 4: Run conversion and engine tests**

Run:

```bash
python -m unittest backend.tests.test_backtest_engine -v
```

Expected: PASS for all tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_backtest_engine.py
git commit -m "feat: use real backtests in stock strategy endpoints"
```

---

### Task 3: Frontend Strategy Detail Fetch

**Files:**
- Modify: `src/hooks/useStockData.ts`

**Interfaces:**
- Consumes: `getStrategyDetail(code: string, strategyId: string): Promise<StrategyDetail>`
- Produces: `loadStrategyDetail(strategyId: string): Promise<StrategyDetail | undefined>` that uses backend data.

- [ ] **Step 1: Identify current mock block**

Run:

```bash
rg -n "构建模拟|mock|strategyDetail: StrategyDetail|getStrategyDetail" src/hooks/useStockData.ts src/services/api.ts
```

Expected: output shows `getStrategyDetail` imported and local mock detail creation inside `src/hooks/useStockData.ts`.

- [ ] **Step 2: Replace local mock detail with backend fetch**

In `src/hooks/useStockData.ts`, replace the `try` block inside `loadStrategyDetail` with:

```typescript
    try {
      const strategyDetail = await getStrategyDetail(selectedCode, strategyId);
      strategyDetailCacheRef.current[cacheKey] = strategyDetail;
      return strategyDetail;
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'fetchStrategy';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.fetchStrategy);
      return undefined;
    }
```

Then simplify the hook dependency list from:

```typescript
  }, [selectedCode, detail, customStrategiesByCode, t]);
```

to:

```typescript
  }, [selectedCode, t]);
```

- [ ] **Step 3: Run TypeScript compile**

Run:

```bash
npx tsc --noEmit
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add src/hooks/useStockData.ts
git commit -m "fix: fetch strategy details from backend"
```

---

### Task 4: End-To-End Verification

**Files:**
- Verify: `backend/app/main.py`
- Verify: `src/hooks/useStockData.ts`

**Interfaces:**
- Consumes: completed backend and frontend changes from Tasks 1-3.
- Produces: verified working feature with backend tests and TypeScript compile passing.

- [ ] **Step 1: Run backend tests**

Run:

```bash
python -m unittest backend.tests.test_backtest_engine -v
```

Expected: PASS for all backtest tests.

- [ ] **Step 2: Run TypeScript compile**

Run:

```bash
npx tsc --noEmit
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 3: Smoke test backend startup import**

Run:

```bash
python -c "from backend.app.main import app; print(app.title)"
```

Expected output includes:

```text
AIStock API
```

- [ ] **Step 4: Inspect final diff**

Run:

```bash
git diff --stat HEAD
git status --short
```

Expected: only intentional uncommitted changes remain, or no uncommitted changes from this feature after commits. Pre-existing unrelated dirty files may still appear.

