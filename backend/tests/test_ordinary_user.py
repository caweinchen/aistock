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
