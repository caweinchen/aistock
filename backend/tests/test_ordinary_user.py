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


if __name__ == "__main__":
    unittest.main()
