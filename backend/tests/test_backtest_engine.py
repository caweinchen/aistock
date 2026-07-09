import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from backend.app.backtest_engine import build_strategy_summaries, normalize_price_bars, run_backtest
from backend.app.database import PricePointDB
from backend.app.main import (
    PricePoint,
    StockDetail,
    StockSummary,
    StrategyResult,
    build_strategy_detail,
    engine_result_to_detail,
    engine_result_to_strategy,
    ensure_price_history,
    _history_needs_refresh,
)


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

    def test_custom_strategy_detail_reuses_saved_lookback(self):
        prices = [10 + i * 0.2 for i in range(120)]
        history = [
            PricePoint(
                date=make_bar(i + 1, price)["date"],
                open=price - 0.2,
                high=price + 0.5,
                low=price - 0.5,
                close=price,
                volume=1000 + i * 10,
            )
            for i, price in enumerate(prices)
        ]
        detail = StockDetail(
            stock=StockSummary(
                code="600519",
                name="Kweichow Moutai",
                price=prices[-1],
                change_percent=1.2,
                score=80,
                signal="buy",
            ),
            factors=[],
            strategies=[],
            alerts=[],
            history=history,
            ai_summary="",
            data_status="normal",
            updated_at="2024-05-01T00:00:00Z",
        )
        strategy = StrategyResult(
            id="custom-trend-breakout-90-1710000000",
            name="Saved Breakout",
            period="Last 90 days",
            return_rate=0,
            max_drawdown=0,
            win_rate=0,
            risk="medium",
            summary="",
        )

        expected = run_backtest(
            "trend-breakout",
            history,
            name=strategy.name,
            lookback_days=90,
            risk=strategy.risk,
        )
        assert expected is not None

        result = build_strategy_detail(detail, strategy)

        self.assertEqual(result.strategy.id, strategy.id)
        self.assertEqual(result.strategy.period, strategy.period)
        self.assertEqual(result.trade_count, expected.trade_count)
        self.assertEqual(result.annualized_return, expected.annualized_return)

    def test_ensure_price_history_loads_tushare_when_local_history_empty(self):
        class FakeQuery:
            def __init__(self, rows):
                self.rows = rows

            def filter(self, *_args):
                return self

            def order_by(self, *_args):
                return self

            def all(self):
                return self.rows

            def first(self):
                return None

            def delete(self):
                self.rows.clear()

        class FakeDb:
            def __init__(self):
                self.rows = []
                self.commits = 0

            def query(self, _model):
                return FakeQuery(self.rows)

            def add(self, row):
                self.rows.append(row)

            def commit(self):
                self.commits += 1

            def rollback(self):
                raise AssertionError("rollback should not be called")

        db = FakeDb()
        stock = Mock(code="600519")
        tushare = Mock()
        tushare.get_daily_price.return_value = [
            {"trade_date": "20240102", "close": 10.2, "vol": 1200},
            {"trade_date": "20240101", "close": 10.0, "vol": 1000},
        ]

        with patch("backend.app.main.tushare_config.enabled", True), patch(
            "backend.app.main.get_tushare_service", return_value=tushare
        ):
            history = ensure_price_history(db, stock)

        tushare.get_daily_price.assert_called_once()
        self.assertEqual([row.date for row in history], ["2024-01-01", "2024-01-02"])
        self.assertEqual([row.close for row in history], [10.0, 10.2])
        self.assertEqual(db.commits, 1)

    def test_history_does_not_refresh_after_latest_market_close_update(self):
        history = [PricePointDB(
            stock_code="600519",
            date="2024-01-02",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1200,
        )]
        stock = Mock(updated_at=datetime(2024, 1, 2, 7, 1, tzinfo=timezone.utc))

        with patch("backend.app.main._is_trading_time", return_value=False), patch(
            "backend.app.main._last_market_session_end_time",
            return_value=datetime(2024, 1, 2, 15, 0),
        ):
            self.assertFalse(_history_needs_refresh(history, stock))

    def test_history_does_not_refresh_during_midday_break_after_morning_close_update(self):
        history = [PricePointDB(
            stock_code="600519",
            date="2024-01-02",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1200,
        )]
        stock = Mock(updated_at=datetime(2024, 1, 2, 3, 31, tzinfo=timezone.utc))

        with patch("backend.app.main._is_trading_time", return_value=False), patch(
            "backend.app.main._last_market_session_end_time",
            return_value=datetime(2024, 1, 2, 11, 30),
        ):
            self.assertFalse(_history_needs_refresh(history, stock))

    def test_history_does_not_refresh_during_trading_when_updated_within_five_minutes(self):
        history = [PricePointDB(
            stock_code="600519",
            date=datetime.now().strftime("%Y-%m-%d"),
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1200,
        )]
        stock = Mock(updated_at=datetime.now(timezone.utc) - timedelta(minutes=4))

        with patch("backend.app.main._is_trading_time", return_value=True):
            self.assertFalse(_history_needs_refresh(history, stock))

    def test_history_refresh_decision_does_not_call_tushare_calendar_when_history_exists(self):
        history = [PricePointDB(
            stock_code="600519",
            date="2026-07-03",
            open=1190.0,
            high=1200.0,
            low=1188.0,
            close=1194.45,
            volume=1000,
        )]
        stock = Mock(updated_at=datetime(2026, 7, 4, 19, 41, 32))

        with patch("backend.app.main._is_trading_time", return_value=False), patch(
            "backend.app.main._last_market_session_end_time",
            return_value=datetime(2026, 7, 4, 15, 0),
        ), patch(
            "backend.app.main.get_initialized_tushare_service",
            side_effect=AssertionError("refresh decision should not call TuShare calendar"),
        ):
            self.assertFalse(_history_needs_refresh(history, stock))


if __name__ == "__main__":
    unittest.main()
