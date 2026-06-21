import unittest

from backend.app.backtest_engine import build_strategy_summaries, normalize_price_bars, run_backtest
from backend.app.main import engine_result_to_detail, engine_result_to_strategy


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


if __name__ == "__main__":
    unittest.main()
