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
    industry="",
    baseline_score=None,
    baseline_risk_score=None,
    baseline_published_at=None,
    baseline_data_completeness="mostly_complete",
):
    stock = SimpleNamespace(code=code, name=name, score=score, updated_at=updated_at, industry=industry)
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
        baseline_score=baseline_score,
        baseline_risk_score=baseline_risk_score,
        baseline_published_at=baseline_published_at,
        baseline_data_completeness=baseline_data_completeness,
    )


class WatchlistIntelligenceTests(unittest.TestCase):
    def test_empty_watchlist_has_insufficient_risk_overview(self):
        result = build_watchlist_intelligence([])

        self.assertEqual(result.risk_overview.status, "insufficient_data")
        self.assertEqual(result.risk_overview.total_count, 0)
        self.assertEqual(result.industry_concentration.status, "insufficient_data")

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

    def test_aggregates_high_risk_and_industry_concentration(self):
        contexts = [
            make_context("600001", "样本一", 40, "cautious", industry="银行", risk_factors=["风险一", "风险二"]),
            make_context("600002", "样本二", 42, "cautious", industry="银行", risk_factors=["风险一", "风险二"]),
            make_context("600003", "样本三", 80, "positive", industry="医药", risk_factors=[]),
        ]

        result = build_watchlist_intelligence(contexts)

        self.assertEqual(result.risk_overview.status, "available")
        self.assertEqual(result.risk_overview.level, "high")
        self.assertEqual(result.risk_overview.high_risk_count, 2)
        self.assertEqual(result.industry_concentration.top_industry, "银行")
        self.assertEqual(result.industry_concentration.top_industry_count, 2)
        self.assertEqual(result.industry_concentration.top_industry_ratio, 0.6667)
        self.assertTrue(result.industry_concentration.is_concentrated)

    def test_recent_change_is_null_when_baseline_or_data_is_insufficient(self):
        contexts = [
            make_context("600001", "无基线", 70, "watch"),
            make_context(
                "600002", "数据不足", 70, "watch", completeness="insufficient",
                baseline_score=60, baseline_risk_score=20, baseline_published_at=datetime(2026, 7, 11),
            ),
        ]

        result = build_watchlist_intelligence(contexts)

        by_code = {item.code: item for item in result.insights}
        self.assertEqual(by_code["600001"].recent_change.status, "insufficient_data")
        self.assertIsNone(by_code["600001"].recent_change.score_change)
        self.assertEqual(by_code["600002"].recent_change.status, "insufficient_data")
        self.assertIsNone(by_code["600002"].recent_change.risk_score_change)

    def test_recent_change_is_null_when_published_baseline_was_insufficient(self):
        context = make_context(
            "600001", "当前数据充分", 70, "watch",
            baseline_score=60,
            baseline_risk_score=20,
            baseline_published_at=datetime(2026, 7, 11),
            baseline_data_completeness="insufficient",
        )

        result = build_watchlist_intelligence([context])

        self.assertEqual(result.insights[0].recent_change.status, "insufficient_data")
        self.assertIsNone(result.insights[0].recent_change.score_change)

    def test_recent_change_sort_uses_absolute_change_then_update_time(self):
        contexts = [
            make_context(
                "600001", "小变化", 72, "watch", updated_at=datetime(2026, 7, 12, 9),
                baseline_score=70, baseline_risk_score=20, baseline_published_at=datetime(2026, 7, 11),
            ),
            make_context(
                "600002", "大变化", 55, "watch", updated_at=datetime(2026, 7, 12, 8),
                baseline_score=75, baseline_risk_score=10, baseline_published_at=datetime(2026, 7, 11),
            ),
            make_context("600003", "无基线", 90, "positive", updated_at=datetime(2026, 7, 12, 10)),
        ]

        result = build_watchlist_intelligence(contexts)
        sorted_items = sort_watchlist_insights(result.insights, "recent_change")

        self.assertEqual([item.code for item in sorted_items], ["600002", "600001", "600003"])
        self.assertEqual(sorted_items[0].recent_change.score_change, -20)


if __name__ == "__main__":
    unittest.main()
