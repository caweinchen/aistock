from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from backend.app.routers import stocks
from backend.app import stock_data_service
from backend.app.stock_data_service import StockDataOperations


class StockDataServiceBoundaryTests(unittest.TestCase):
    def test_history_refresh_boundary_delegates_to_service(self):
        with patch.object(
            stocks,
            "service_history_needs_refresh",
            return_value=False,
            create=True,
        ) as delegated:
            result = stocks._history_needs_refresh([], object())

        self.assertFalse(result)
        delegated.assert_called_once()


class StockDataServiceBehaviorTests(unittest.TestCase):
    def test_trading_time_covers_open_and_lunch_break(self):
        with patch.object(stock_data_service, "datetime") as mocked_datetime:
            mocked_datetime.now.return_value = datetime(2026, 7, 10, 10, 0)
            self.assertTrue(stock_data_service.is_trading_time())
            mocked_datetime.now.return_value = datetime(2026, 7, 10, 12, 0)
            self.assertFalse(stock_data_service.is_trading_time())

    def test_ensure_history_returns_cache_without_remote_call(self):
        cached = [SimpleNamespace(date="2026-07-10")]
        provider = Mock()
        with patch.object(stock_data_service, "get_price_history", return_value=cached):
            result = stock_data_service.ensure_price_history(
                Mock(),
                Mock(code="600000"),
                StockDataOperations(get_tushare_service=lambda: provider),
                needs_refresh=lambda history, stock: False,
            )
        self.assertIs(result, cached)
        provider.get_daily_price.assert_not_called()

    def test_ensure_history_updates_existing_incremental_row(self):
        cached = [SimpleNamespace(date="2026-07-10", close=1.0)]
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = cached[0]
        provider = Mock()
        provider.get_daily_price.return_value = [{"trade_date": "20260710", "close": 2, "open": 1, "high": 3, "low": 1, "vol": 9}]
        with patch.object(stock_data_service, "get_price_history", side_effect=[cached, cached]):
            result = stock_data_service.ensure_price_history(
                db,
                SimpleNamespace(code="600000", ts_code="600000.SH", data_status="normal", updated_at=None),
                StockDataOperations(get_tushare_service=lambda: provider),
                needs_refresh=lambda history, stock: True,
            )
        self.assertEqual(cached[0].close, 2.0)
        self.assertEqual(result, cached)
        db.commit.assert_called_once()

    def test_ensure_history_keeps_cache_on_empty_or_error(self):
        cached = [SimpleNamespace(date="2026-07-10")]
        for response in ([], RuntimeError("provider failed")):
            with self.subTest(response=type(response).__name__):
                db = Mock()
                provider = Mock()
                if isinstance(response, Exception):
                    provider.get_daily_price.side_effect = response
                else:
                    provider.get_daily_price.return_value = response
                with patch.object(stock_data_service, "get_price_history", return_value=cached):
                    result = stock_data_service.ensure_price_history(
                        db,
                        SimpleNamespace(code="600000", ts_code="600000.SH", data_status="normal", updated_at=None),
                        StockDataOperations(get_tushare_service=lambda: provider),
                        needs_refresh=lambda history, stock: True,
                    )
                self.assertIs(result, cached)
                if isinstance(response, Exception):
                    db.rollback.assert_called_once()

    def test_realtime_update_commits_and_rolls_back(self):
        stock = SimpleNamespace(code="600000", price=1, change_percent=0, name="old", updated_at=None)
        db = Mock()
        stock_data_service.update_stock_realtime_quote(
            db,
            stock,
            StockDataOperations(get_realtime_quotes=lambda codes: [{"price": 2, "change_percent": 1, "name": "new"}]),
        )
        self.assertEqual((stock.price, stock.change_percent, stock.name), (2, 1, "new"))
        self.assertIsNotNone(stock.updated_at)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(stock)

        failed_db = Mock()
        stock_data_service.update_stock_realtime_quote(
            failed_db,
            stock,
            StockDataOperations(get_realtime_quotes=Mock(side_effect=RuntimeError("provider failed"))),
        )
        failed_db.rollback.assert_called_once()

    def test_price_history_boundary_delegates_to_service(self):
        expected = [object()]
        with patch.object(stocks, "service_get_price_history", return_value=expected, create=True) as delegated:
            result = stocks.get_price_history(Mock(), "600000")
        self.assertIs(result, expected)
        delegated.assert_called_once()

    def test_ensure_price_history_boundary_delegates_to_service(self):
        expected = [object()]
        with patch.object(stocks, "service_ensure_price_history", return_value=expected, create=True) as delegated:
            result = stocks.ensure_price_history(Mock(), Mock())
        self.assertIs(result, expected)
        delegated.assert_called_once()

    def test_realtime_update_boundary_delegates_to_service(self):
        with patch.object(stocks, "service_update_stock_realtime_quote", create=True) as delegated:
            stocks.update_stock_realtime_quote(Mock(), Mock())
        delegated.assert_called_once()


if __name__ == "__main__":
    unittest.main()
