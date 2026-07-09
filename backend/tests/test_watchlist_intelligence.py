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
