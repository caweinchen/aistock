import unittest
from datetime import datetime
from types import SimpleNamespace

from backend.app.ordinary_user import (
    build_data_health,
    build_pre_trade_checklist,
    build_risk_explanations,
)
from backend.app.schemas import ChecklistItem, DataHealth, PreTradeChecklist, RiskExplanation


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

        result = build_data_health(
            stock,
            history=history,
            factors=factors,
            alerts=[],
            holders=[SimpleNamespace(change_amount=10)],
            dividends=[SimpleNamespace(cash_dividend=1)],
        )

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

    def test_data_health_covers_all_four_completeness_levels(self):
        stock = SimpleNamespace(data_status="normal", updated_at=datetime(2026, 7, 9, 10, 0))
        history = [SimpleNamespace(date=str(index)) for index in range(20)]
        factors = [SimpleNamespace(key=f"factor-{index}") for index in range(4)]
        cases = [
            ("complete", factors, [SimpleNamespace(change_amount=10)], [SimpleNamespace(cash_dividend=1)], "normal"),
            ("mostly_complete", factors, [], [], "normal"),
            ("incomplete", factors[:2], [], [], "normal"),
        ]

        for expected, case_factors, holders, dividends, data_status in cases:
            with self.subTest(expected=expected):
                case_stock = SimpleNamespace(data_status=data_status, updated_at=stock.updated_at)
                result = build_data_health(case_stock, history, case_factors, [], holders, dividends)
                self.assertEqual(result.completeness, expected)

        insufficient = build_data_health(
            SimpleNamespace(data_status="partial", updated_at=None),
            history[:1],
            [],
            [],
            [],
            [],
        )
        self.assertEqual(insufficient.completeness, "insufficient")

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
        stock = SimpleNamespace(score=70, signal="buy", data_status="partial", updated_at=None)
        data_health = build_data_health(stock, history=[], factors=[])

        risks = build_risk_explanations(stock, factors=[], alerts=[], holders=[], dividends=[], data_health=data_health)

        self.assertTrue(any(risk.type == "data_quality" for risk in risks))
        self.assertTrue(any("数据不足" in risk.title for risk in risks))

    def test_risk_explanations_cover_fundamentals_holder_change_and_dividend_inputs(self):
        stock = SimpleNamespace(data_status="normal", updated_at=datetime(2026, 7, 9, 10, 0))
        factors = [SimpleNamespace(key="profitability", value=30, description="盈利质量偏弱。")]
        holders = [SimpleNamespace(change_amount=-100)]

        risks = build_risk_explanations(stock, factors=factors, holders=holders, dividends=[])

        self.assertIn("fundamentals", {risk.type for risk in risks})
        self.assertIn("holder_change", {risk.type for risk in risks})
        self.assertIn("dividend", {risk.type for risk in risks})

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
        stock = SimpleNamespace(score=70, signal="neutral", data_status="normal", updated_at=datetime(2026, 7, 9, 10, 0))
        data_health = build_data_health(
            stock,
            history=[SimpleNamespace(date=str(i)) for i in range(30)],
            factors=[SimpleNamespace(key="valuation", value=65)] * 4,
        )

        checklist = build_pre_trade_checklist(stock, [], data_health, mode="sell")

        self.assertEqual(checklist.mode, "sell")
        self.assertTrue(any(item.key == "avoid_panic" for item in checklist.items))

    def test_schema_defaults_remain_backward_compatible(self):
        data_health = DataHealth()
        risk = RiskExplanation(
            type="valuation",
            level="low",
            title="估值风险",
            what_it_means="估值信息",
            why_it_matters="影响说明",
        )
        item = ChecklistItem(key="confirm", label="确认", status="user_confirm", explanation="请确认")
        checklist = PreTradeChecklist(mode="buy", title="买入前检查", completion_hint="请逐项检查")

        self.assertEqual(data_health.completeness, "incomplete")
        self.assertEqual(data_health.source_summary, [])
        self.assertEqual(risk.evidence, [])
        self.assertFalse(item.user_confirm_required)
        self.assertEqual(checklist.items, [])

    def test_checklist_models_preserve_buy_and_sell_response_structure(self):
        stock = SimpleNamespace(data_status="normal", updated_at=datetime(2026, 7, 9, 10, 0))
        health = build_data_health(
            stock,
            history=[SimpleNamespace(date=str(index)) for index in range(20)],
            factors=[SimpleNamespace(key=f"factor-{index}") for index in range(4)],
            holders=[SimpleNamespace(change_amount=10)],
            dividends=[SimpleNamespace(cash_dividend=1)],
        )

        for mode in ("buy", "sell"):
            with self.subTest(mode=mode):
                result = build_pre_trade_checklist(stock, [], health, mode=mode)
                model = PreTradeChecklist(
                    mode=result.mode,
                    title=result.title,
                    completion_hint=result.completion_hint,
                    items=[ChecklistItem(**item.__dict__) for item in result.items],
                )
                payload = model.model_dump()
                self.assertEqual(payload["mode"], mode)
                self.assertTrue(payload["title"])
                self.assertTrue(payload["completion_hint"])
                self.assertTrue(payload["items"])
                self.assertTrue({"key", "label", "status", "explanation", "user_confirm_required"} <= payload["items"][0].keys())


if __name__ == "__main__":
    unittest.main()
