from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import sqrt
from statistics import pstdev
from typing import Any


VALID_TEMPLATES = ("trend-breakout", "low-valuation-reversal", "dividend-defense")


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


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    if len(text) >= 10:
        return text[:10]
    return text


def normalize_price_bars(items: list[Any]) -> list[PriceBar]:
    bars: list[PriceBar] = []
    for item in items:
        bar_date = _format_date(_get_value(item, "date") or _get_value(item, "trade_date"))
        close = _coerce_float(_get_value(item, "close"))
        if not bar_date or close <= 0:
            continue

        open_price = _coerce_float(_get_value(item, "open"), close)
        high = _coerce_float(_get_value(item, "high"), max(open_price, close))
        low = _coerce_float(_get_value(item, "low"), min(open_price, close))
        volume = _coerce_int(_get_value(item, "volume", _get_value(item, "vol")), 0)

        bars.append(
            PriceBar(
                date=bar_date,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )

    return sorted(bars, key=lambda bar: bar.date)


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            drawdown = (peak - equity) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
    return -round(max_drawdown, 2)


def _annualized_return(total_return: float, first_date: str, last_date: str) -> float:
    try:
        start = datetime.strptime(first_date, "%Y-%m-%d")
        end = datetime.strptime(last_date, "%Y-%m-%d")
    except ValueError:
        return round(total_return, 2)

    elapsed_days = max((end - start).days, 1)
    return round(total_return * 365 / elapsed_days, 2)


def _sharpe_ratio(equity_curve: list[float]) -> float:
    daily_returns = [
        (equity_curve[index] - equity_curve[index - 1]) / equity_curve[index - 1]
        for index in range(1, len(equity_curve))
        if equity_curve[index - 1] > 0
    ]
    if len(daily_returns) < 2:
        return 0.0

    volatility = pstdev(daily_returns)
    if volatility == 0:
        return 0.0
    return round((_average(daily_returns) / volatility) * sqrt(252), 2)


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


def _resolve_template(strategy_id: str) -> str:
    if strategy_id in VALID_TEMPLATES:
        return strategy_id
    for template in VALID_TEMPLATES:
        if template in strategy_id:
            return template
    return strategy_id


def _moving_average(bars: list[PriceBar]) -> float:
    return _average([bar.close for bar in bars])


def _signal(template: str, bars: list[PriceBar], index: int, in_position: bool, entry_price: float) -> tuple[str | None, str]:
    close = bars[index].close
    ma_window = bars[max(0, index - 19) : index + 1]
    ma20 = _moving_average(ma_window)

    recent = bars[max(0, index - 29) : index + 1]
    recent_low = min(bar.close for bar in recent)
    recent_high = max(bar.close for bar in recent)
    range_width = max(recent_high - recent_low, 0.01)
    range_position = (close - recent_low) / range_width

    volatility_window = bars[max(0, index - 9) : index + 1]
    daily_moves = [
        abs(volatility_window[i].close - volatility_window[i - 1].close) / volatility_window[i - 1].close
        for i in range(1, len(volatility_window))
        if volatility_window[i - 1].close > 0
    ]
    volatility = _average(daily_moves)
    stop_loss_hit = in_position and entry_price > 0 and close <= entry_price * 0.92

    if template == "trend-breakout":
        previous_close = bars[index - 1].close if index > 0 else close
        previous_ma = _moving_average(bars[max(0, index - 20) : index]) if index > 0 else ma20
        if not in_position and previous_close <= previous_ma and close > ma20:
            return "buy", "Close crossed above the 20-day moving average."
        if in_position and (close < ma20 or stop_loss_hit):
            return "sell", "Close fell below the 20-day moving average or stop-loss was hit."
    elif template == "low-valuation-reversal":
        previous_close = bars[index - 1].close if index > 0 else close
        if not in_position and range_position < 0.35 and close > previous_close:
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
    template = _resolve_template(strategy_id)
    if template not in VALID_TEMPLATES:
        return None

    bars = normalize_price_bars(items)
    if lookback_days is not None:
        bars = bars[-lookback_days:]
    if len(bars) < 30:
        return None

    initial_cash = 1_000_000.0
    cash = initial_cash
    quantity = 0
    entry_price = 0.0
    entry_cost = 0.0
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
                entry_cost = quantity * bar.close
                trades.append(BacktestTradeRecord(bar.date, "buy", round(bar.close, 2), quantity, reason))
        elif action == "sell" and quantity > 0:
            proceeds = quantity * bar.close
            cash += proceeds
            if proceeds >= entry_cost:
                wins += 1
            else:
                losses += 1
            trades.append(BacktestTradeRecord(bar.date, "sell", round(bar.close, 2), quantity, reason))
            quantity = 0
            entry_price = 0.0
            entry_cost = 0.0

        equity_curve.append(cash + quantity * bar.close)

    if quantity > 0:
        last_bar = bars[-1]
        proceeds = quantity * last_bar.close
        cash += proceeds
        if proceeds >= entry_cost:
            wins += 1
        else:
            losses += 1
        trades.append(
            BacktestTradeRecord(
                last_bar.date,
                "sell",
                round(last_bar.close, 2),
                quantity,
                "Closed open position at the end of the backtest.",
            )
        )
        equity_curve[-1] = cash

    final_equity = equity_curve[-1] if equity_curve else initial_cash
    total_return = (final_equity - initial_cash) / initial_cash * 100
    completed_trades = wins + losses
    win_rate = wins / completed_trades * 100 if completed_trades else 0.0
    display_name = name or {
        "trend-breakout": "Trend Breakout",
        "low-valuation-reversal": "Low Valuation Reversal",
        "dividend-defense": "Dividend Defense",
    }[template]
    risk_value = risk or (
        "high"
        if template == "trend-breakout" and abs(_drawdown(equity_curve)) > 12
        else "low"
        if template == "dividend-defense"
        else "medium"
    )

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
    for template in VALID_TEMPLATES:
        result = run_backtest(template, items)
        if result is not None:
            results.append(result)
    return results
