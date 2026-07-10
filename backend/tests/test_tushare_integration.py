import unittest
from unittest.mock import Mock, patch

import pandas as pd
from fastapi import HTTPException

from backend.app.database import Stock
from backend.app.main import (
    get_stock_adj_factor,
    get_stock_dividend,
    get_stock_inst_hold,
    get_stock_news,
)
from backend.app.tushare_service import TuShareService


class FakeQuery:
    def __init__(self, stock):
        self.stock = stock

    def filter(self, *_args):
        return self

    def first(self):
        return self.stock


class FakeDb:
    def __init__(self, stock):
        self.stock = stock

    def query(self, _model):
        return FakeQuery(self.stock)


class StockTsCodeRouteTests(unittest.TestCase):
    def setUp(self):
        self.stock = Stock(code="600519", name="Kweichow Moutai", ts_code="")
        self.db = FakeDb(self.stock)
        self.user = Mock()
        self.service = Mock()

    def test_dividend_route_uses_ts_code_fallback_when_database_value_is_empty(self):
        self.service.get_dividend.return_value = []

        with patch("app.routers.stocks.tushare_config.enabled", True), patch(
            "app.routers.stocks.get_tushare_service", return_value=self.service
        ):
            get_stock_dividend("600519", self.db, self.user)

        self.service.get_dividend.assert_called_once_with("600519.SH")

    def test_news_route_uses_ts_code_fallback_when_database_value_is_empty(self):
        self.service.get_stock_news.return_value = []

        with patch("app.routers.stocks.tushare_config.enabled", True), patch(
            "app.routers.stocks.get_tushare_service", return_value=self.service
        ):
            get_stock_news("600519", self.db, self.user)

        self.service.get_stock_news.assert_called_once_with("600519.SH")

    def test_adj_factor_route_uses_ts_code_fallback_when_database_value_is_empty(self):
        self.service.get_adj_factor.return_value = []

        with patch("app.routers.stocks.tushare_config.enabled", True), patch(
            "app.routers.stocks.get_tushare_service", return_value=self.service
        ):
            get_stock_adj_factor("600519", self.db, self.user)

        self.service.get_adj_factor.assert_called_once_with("600519.SH")

    def test_inst_hold_route_uses_ts_code_fallback_when_database_value_is_empty(self):
        self.service.get_inst_hold.return_value = []

        with patch("app.routers.stocks.tushare_config.enabled", True), patch(
            "app.routers.stocks.get_tushare_service", return_value=self.service
        ):
            get_stock_inst_hold("600519", self.db, self.user)

        self.service.get_inst_hold.assert_called_once_with("600519.SH")

    def test_route_returns_diagnostic_error_when_tushare_call_failed(self):
        self.service.get_dividend.return_value = []
        self.service.last_error = {
            "api": "dividend",
            "ts_code": "600519.SH",
            "message": "每分钟最多访问该接口1次",
        }

        with patch("app.routers.stocks.tushare_config.enabled", True), patch(
            "app.routers.stocks.get_tushare_service", return_value=self.service
        ):
            with self.assertRaises(HTTPException) as raised:
                get_stock_dividend("600519", self.db, self.user)

        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail["api"], "dividend")
        self.assertIn("每分钟", raised.exception.detail["message"])


class TuShareServiceApiNameTests(unittest.TestCase):
    def test_stock_news_uses_documented_news_api(self):
        service = TuShareService()
        service.pro = Mock()
        service.pro.news.return_value = pd.DataFrame(
            [
                {
                    "datetime": "2024-01-02 09:30:00",
                    "title": "Market update",
                    "content": "Ping An Bank mentioned in market news",
                    "channels": "stock",
                }
            ]
        )

        news = service.get_stock_news("000001.SZ", start_date="20240101", end_date="20240102")

        service.pro.news.assert_called_once()
        self.assertEqual(news[0]["ts_code"], "000001.SZ")
        self.assertEqual(news[0]["pub_time"], "2024-01-02 09:30:00")

    def test_daily_price_free_mode_falls_back_when_legacy_tushare_breaks(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return (
                    b'{"data":{"klines":["2026-07-10,36.55,36.88,37.01,36.40,123456,0,0,0,0,0"]}}'
                )

        service = TuShareService()

        with patch("backend.app.tushare_service.ts.get_k_data", side_effect=AttributeError("'DataFrame' object has no attribute 'append'")), patch(
            "backend.app.tushare_service.urlopen",
            return_value=FakeResponse(),
            create=True,
        ):
            rows = service.get_daily_price("600036.SH", start_date="20260703", end_date="20260710")

        self.assertEqual(rows, [{
            "date": "2026-07-10",
            "open": 36.55,
            "close": 36.88,
            "high": 37.01,
            "low": 36.4,
            "volume": 123456,
        }])

    def test_inst_hold_uses_top10_holders_api(self):
        service = TuShareService()
        service.pro = Mock()
        service.pro.top10_holders.return_value = pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "ann_date": "20240430",
                    "end_date": "20240331",
                    "holder_name": "Central Huijin",
                    "hold_amount": 1000,
                    "hold_ratio": 2.5,
                    "hold_float_ratio": 2.0,
                    "hold_change": 10,
                    "holder_type": "机构",
                }
            ]
        )

        holders = service.get_inst_hold("000001.SZ", start_date="20240101", end_date="20240630")

        service.pro.top10_holders.assert_called_once()
        self.assertEqual(holders[0]["holder_name"], "Central Huijin")
        self.assertEqual(holders[0]["trade_date"], "20240331")


if __name__ == "__main__":
    unittest.main()
