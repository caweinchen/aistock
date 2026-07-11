import unittest
from unittest.mock import Mock, patch

from backend.app.routers import stocks
from backend.app import stock_analysis_service
from backend.app.schemas import FactorScore
from backend.app.stock_analysis_service import AnalysisOperations


class StockAnalysisServiceBoundaryTests(unittest.TestCase):
    def test_analysis_boundaries_delegate_to_service(self):
        cases = [
            ("service_ensure_factor_scores", stocks.ensure_factor_scores, (Mock(), Mock(), [])),
            ("service_ensure_alerts", stocks.ensure_alerts, (Mock(), Mock(), [], [])),
            ("service_ensure_ai_summary", stocks.ensure_ai_summary, (Mock(), Mock(), [], [], [])),
        ]
        for service_name, boundary, args in cases:
            with self.subTest(service_name=service_name):
                expected = object()
                with patch.object(stocks, service_name, return_value=expected, create=True) as delegated:
                    try:
                        result = boundary(*args)
                    except Exception:
                        result = None
                self.assertIs(result, expected)
                delegated.assert_called_once()

    def test_factor_service_falls_back_to_local_scores_after_provider_error(self):
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = []
        provider = Mock(pro=True)
        provider.get_daily_basic.side_effect = RuntimeError("provider failed")
        local = [FactorScore(key="valuation", label="Valuation", value=50, description="local")]

        stock_analysis_service.ensure_factor_scores(
            db,
            Mock(code="600000"),
            [Mock(close=1)],
            AnalysisOperations(
                get_tushare_service=lambda: provider,
                calculate_financial_factors=Mock(),
                calculate_local_factors=lambda history: local,
                factor_to_model=lambda row: row,
                item_value=lambda item, key, default=None: getattr(item, key, default),
                stock_ts_code=lambda stock: "600000.SH",
            ),
        )

        self.assertTrue(db.add.called)
        db.rollback.assert_called_once()
        db.commit.assert_called_once()

    def test_alert_and_summary_services_persist_results(self):
        db = Mock()
        stock = Mock(code="600000", ai_summary=None)
        factors = [FactorScore(key="profitability", label="Profitability", value=30, description="盈利能力较差。")]

        alerts = stock_analysis_service.ensure_alerts(db, stock, [], factors)
        summary = stock_analysis_service.ensure_ai_summary(db, stock, [], factors, alerts)

        self.assertTrue(alerts)
        self.assertTrue(summary)
        self.assertEqual(stock.ai_summary, summary)
        self.assertEqual(db.commit.call_count, 2)


if __name__ == "__main__":
    unittest.main()
