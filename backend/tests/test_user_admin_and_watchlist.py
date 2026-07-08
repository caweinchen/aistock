import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, FactorScoreDB, PricePointDB, Stock, User, WatchlistItem
from app.main import app, get_db
from app.security import hash_password


class UserAdminAndWatchlistTests(unittest.TestCase):
    def setUp(self):
      engine = create_engine(
          "sqlite://",
          connect_args={"check_same_thread": False},
          poolclass=StaticPool,
      )
      TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
      Base.metadata.create_all(bind=engine)
      self.db = TestingSessionLocal()

      self.admin = User(
          username="admin",
          password=hash_password("Admin@123!"),
          is_active=True,
          role="admin",
      )
      self.user_a = User(
          username="alice",
          password=hash_password("Alice@123!"),
          is_active=True,
          role="user",
      )
      self.user_b = User(
          username="bob",
          password=hash_password("Bob@123!"),
          is_active=True,
          role="user",
      )
      self.db.add_all([self.admin, self.user_a, self.user_b])
      self.db.commit()
      for user in [self.admin, self.user_a, self.user_b]:
          self.db.refresh(user)

      def override_get_db():
          try:
              yield self.db
          finally:
              pass

      app.dependency_overrides[get_db] = override_get_db
      self.client = TestClient(app)

    def tearDown(self):
      app.dependency_overrides.clear()
      self.db.close()

    def _login(self, username: str, password: str) -> str:
      response = self.client.post("/api/auth/login", json={"username": username, "password": password})
      self.assertEqual(response.status_code, 200, response.text)
      return response.json()["token"]

    def test_registered_user_is_inactive_and_cannot_login_until_admin_enables(self):
      register = self.client.post(
          "/api/auth/register",
          json={"username": "newuser", "password": "NewUser@123!"},
      )
      self.assertEqual(register.status_code, 200, register.text)
      self.assertEqual(register.json()["is_active"], False)
      self.assertEqual(register.json()["role"], "user")

      login_before_enable = self.client.post(
          "/api/auth/login",
          json={"username": "newuser", "password": "NewUser@123!"},
      )
      self.assertEqual(login_before_enable.status_code, 403)

      admin_token = self._login("admin", "Admin@123!")
      users = self.client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
      created_user = next(user for user in users.json() if user["username"] == "newuser")

      enable = self.client.patch(
          f"/api/admin/users/{created_user['id']}",
          headers={"Authorization": f"Bearer {admin_token}"},
          json={"is_active": True},
      )
      self.assertEqual(enable.status_code, 200, enable.text)
      self.assertEqual(enable.json()["is_active"], True)

      login_after_enable = self.client.post(
          "/api/auth/login",
          json={"username": "newuser", "password": "NewUser@123!"},
      )
      self.assertEqual(login_after_enable.status_code, 200, login_after_enable.text)

    def test_only_admin_can_manage_users_and_change_roles(self):
      user_token = self._login("alice", "Alice@123!")
      forbidden = self.client.get("/api/admin/users", headers={"Authorization": f"Bearer {user_token}"})
      self.assertEqual(forbidden.status_code, 403)

      admin_token = self._login("admin", "Admin@123!")
      promote = self.client.patch(
          f"/api/admin/users/{self.user_a.id}",
          headers={"Authorization": f"Bearer {admin_token}"},
          json={"role": "admin"},
      )
      self.assertEqual(promote.status_code, 200, promote.text)
      self.assertEqual(promote.json()["role"], "admin")

    def test_watchlist_is_isolated_by_user(self):
      self.db.add_all([
          WatchlistItem(user_id=self.user_a.id, stock_code="600519", created_at=datetime.now(timezone.utc)),
          WatchlistItem(user_id=self.user_b.id, stock_code="000001", created_at=datetime.now(timezone.utc)),
      ])
      self.db.commit()

      alice_token = self._login("alice", "Alice@123!")
      bob_token = self._login("bob", "Bob@123!")

      alice_watchlist = self.client.get("/api/watchlist", headers={"Authorization": f"Bearer {alice_token}"})
      bob_watchlist = self.client.get("/api/watchlist", headers={"Authorization": f"Bearer {bob_token}"})

      self.assertEqual(alice_watchlist.status_code, 200, alice_watchlist.text)
      self.assertEqual(bob_watchlist.status_code, 200, bob_watchlist.text)
      self.assertEqual(alice_watchlist.json(), {"codes": ["600519"]})
      self.assertEqual(bob_watchlist.json(), {"codes": ["000001"]})

    def test_stock_list_returns_ordinary_user_reference_fields(self):
      self.db.add(Stock(
          code="600519",
          name="Kweichow Moutai",
          price=1688.0,
          change_percent=1.5,
          score=82,
          signal="buy",
          data_status="normal",
          updated_at=datetime(2026, 7, 8, 9, 30, tzinfo=timezone.utc),
      ))
      self.db.add(WatchlistItem(user_id=self.user_a.id, stock_code="600519", created_at=datetime.now(timezone.utc)))
      self.db.commit()

      alice_token = self._login("alice", "Alice@123!")
      response = self.client.get("/api/stocks", headers={"Authorization": f"Bearer {alice_token}"})

      self.assertEqual(response.status_code, 200, response.text)
      item = response.json()[0]
      self.assertEqual(item["reference_status"], "positive")
      self.assertEqual(item["reference_label"], "偏积极")
      self.assertIn("重点观察", item["primary_support"])
      self.assertEqual(item["data_completeness"], "mostly_complete")
      self.assertIsNotNone(item["data_updated_at"])

    def test_stock_detail_returns_ordinary_summary_and_data_health(self):
      self.db.add(Stock(code="601398", name="ICBC", price=6.12, change_percent=1.23, score=76, signal="buy"))
      for index in range(30):
          self.db.add(PricePointDB(
              stock_code="601398",
              date=f"2026-06-{index + 1:02d}",
              open=6,
              high=6.2,
              low=5.9,
              close=6 + index * 0.01,
              volume=10000,
          ))
      self.db.add(FactorScoreDB(stock_code="601398", key="valuation", label="Valuation", value=68, description="估值处于合理区间。"))
      self.db.add(FactorScoreDB(stock_code="601398", key="momentum", label="Momentum", value=74, description="价格趋势有所改善。"))
      self.db.commit()

      alice_token = self._login("alice", "Alice@123!")
      response = self.client.get("/api/stocks/601398", headers={"Authorization": f"Bearer {alice_token}"})

      self.assertEqual(response.status_code, 200, response.text)
      payload = response.json()
      self.assertIn("ordinary_summary", payload)
      self.assertIn("data_completeness", payload)
      self.assertIn("support_factors", payload)
      self.assertIn("risk_factors", payload)
      self.assertEqual(payload["disclaimer"], "仅供学习和分析参考，不构成投资建议。")

    def test_watchlist_insights_groups_user_stocks(self):
      self.db.add_all([
          Stock(code="601398", name="ICBC", price=6.12, change_percent=1.2, score=80, signal="buy", data_status="normal"),
          Stock(code="000001", name="Ping An Bank", price=12.3, change_percent=-0.5, score=40, signal="sell", data_status="normal"),
          WatchlistItem(user_id=self.user_a.id, stock_code="601398", created_at=datetime.now(timezone.utc)),
          WatchlistItem(user_id=self.user_a.id, stock_code="000001", created_at=datetime.now(timezone.utc)),
      ])
      self.db.commit()

      alice_token = self._login("alice", "Alice@123!")
      response = self.client.get("/api/watchlist/insights", headers={"Authorization": f"Bearer {alice_token}"})

      self.assertEqual(response.status_code, 200, response.text)
      payload = response.json()
      self.assertEqual(payload["total"], 2)
      self.assertEqual(payload["disclaimer"], "仅供学习和分析参考，不构成投资建议。")
      self.assertIn("positive", payload["groups"])
      self.assertIn("cautious", payload["groups"])

    def test_add_new_watchlist_stock_fetches_realtime_price(self):
      alice_token = self._login("alice", "Alice@123!")

      class FakeEastMoney:
          def get_realtime_quote(self, codes):
              self.codes = codes
              return [{
                  "code": "601398",
                  "name": "ICBC",
                  "price": 6.12,
                  "change_percent": 1.23,
              }]

      fake_eastmoney = FakeEastMoney()
      with patch("app.eastmoney_service.get_stock_info_by_code", return_value={
          "code": "601398",
          "name": "ICBC",
          "ts_code": "601398.SH",
          "market": "SH",
      }), patch("app.main.get_eastmoney_service", return_value=fake_eastmoney):
          add_response = self.client.post(
              "/api/watchlist/601398",
              headers={"Authorization": f"Bearer {alice_token}"},
          )

      self.assertEqual(add_response.status_code, 200, add_response.text)
      payload = add_response.json()
      added_stock = next(stock for stock in payload if stock["code"] == "601398")
      self.assertEqual(added_stock["price"], 6.12)
      self.assertEqual(added_stock["change_percent"], 1.23)

      stock = self.db.query(Stock).filter(Stock.code == "601398").first()
      self.assertEqual(stock.price, 6.12)

    def test_new_watchlist_stock_without_existing_history_fetches_real_tushare_history_for_backtests(self):
      self.db.add(Stock(
          code="601398",
          name="ICBC",
          price=5.25,
          change_percent=0.2,
          score=50,
          signal="neutral",
      ))
      self.db.commit()

      alice_token = self._login("alice", "Alice@123!")
      add_response = self.client.post(
          "/api/watchlist/601398",
          headers={"Authorization": f"Bearer {alice_token}"},
      )
      self.assertEqual(add_response.status_code, 200, add_response.text)

      daily_data = [
          {
              "trade_date": f"202501{day:02d}" if day <= 31 else f"202502{day - 31:02d}",
              "open": 5.0 + day * 0.01,
              "high": 5.1 + day * 0.01,
              "low": 4.9 + day * 0.01,
              "close": 5.0 + day * 0.01,
              "vol": 100000 + day,
          }
          for day in range(1, 36)
      ]

      class FakeTuShare:
          def __init__(self):
              self.pro = None
              self.calls = []

          def get_daily_price(self, ts_code, start_date, end_date):
              self.calls.append((ts_code, start_date, end_date))
              return daily_data

      fake_tushare = FakeTuShare()
      with patch("app.main.tushare_config.token", ""), patch("app.main.get_tushare_service", return_value=fake_tushare):
          detail_response = self.client.get(
              "/api/stocks/601398",
              headers={"Authorization": f"Bearer {alice_token}"},
          )

      self.assertEqual(detail_response.status_code, 200, detail_response.text)
      payload = detail_response.json()
      self.assertEqual(fake_tushare.calls[0][0], "601398.SH")
      self.assertEqual(len(payload["history"]), len(daily_data))
      self.assertGreater(len(payload["strategies"]), 0)

    def test_new_stock_does_not_generate_temporary_history_when_tushare_has_no_data(self):
      self.db.add(Stock(
          code="601398",
          name="ICBC",
          price=5.25,
          change_percent=0.2,
          score=50,
          signal="neutral",
      ))
      self.db.commit()

      alice_token = self._login("alice", "Alice@123!")

      class EmptyTuShare:
          pro = None

          def get_daily_price(self, ts_code, start_date, end_date):
              return []

      with patch("app.main.tushare_config.token", ""), patch("app.main.get_tushare_service", return_value=EmptyTuShare()):
          detail_response = self.client.get(
              "/api/stocks/601398",
              headers={"Authorization": f"Bearer {alice_token}"},
          )

      self.assertEqual(detail_response.status_code, 200, detail_response.text)
      payload = detail_response.json()
      self.assertEqual(payload["history"], [])
      self.assertEqual(payload["strategies"], [])

    def test_missing_history_reinitializes_tushare_with_configured_token(self):
      self.db.add(Stock(
          code="601398",
          name="ICBC",
          price=5.25,
          change_percent=0.2,
          score=50,
          signal="neutral",
      ))
      self.db.commit()

      alice_token = self._login("alice", "Alice@123!")

      class NoProTuShare:
          pro = None

      class ProTuShare:
          pro = object()

          def get_daily_price(self, ts_code, start_date, end_date):
              return [
                  {
                      "trade_date": f"202503{day:02d}",
                      "open": 5.0,
                      "high": 5.1,
                      "low": 4.9,
                      "close": 5.0 + day * 0.01,
                      "vol": 100000 + day,
                  }
                  for day in range(1, 32)
              ]

      with patch("app.main.tushare_config.token", "configured-token"), \
          patch("app.main.get_tushare_service", return_value=NoProTuShare()), \
          patch("app.main.init_tushare", return_value=ProTuShare()) as init_tushare_mock:
          detail_response = self.client.get(
              "/api/stocks/601398",
              headers={"Authorization": f"Bearer {alice_token}"},
          )

      self.assertEqual(detail_response.status_code, 200, detail_response.text)
      init_tushare_mock.assert_called_once_with("configured-token")
      self.assertGreater(len(detail_response.json()["strategies"]), 0)

    def test_refresh_all_fills_missing_history_for_watchlist_backtests(self):
      self.db.add(Stock(
          code="601398",
          name="ICBC",
          price=0,
          change_percent=0,
          score=50,
          signal="neutral",
      ))
      self.db.add(WatchlistItem(
          user_id=self.user_a.id,
          stock_code="601398",
          created_at=datetime.now(timezone.utc),
      ))
      self.db.commit()

      daily_data = [
          {
              "trade_date": f"202504{day:02d}" if day <= 30 else f"202505{day - 30:02d}",
              "open": 5.0 + day * 0.01,
              "high": 5.1 + day * 0.01,
              "low": 4.9 + day * 0.01,
              "close": 5.0 + day * 0.01,
              "vol": 100000 + day,
          }
          for day in range(1, 36)
      ]

      class FakeEastMoney:
          def get_realtime_quote(self, codes):
              return [{
                  "code": "601398",
                  "name": "ICBC",
                  "price": 6.18,
                  "change_percent": 0.8,
              }]

      class FakeTuShare:
          pro = None

          def __init__(self):
              self.calls = []

          def get_daily_price(self, ts_code, start_date, end_date):
              self.calls.append((ts_code, start_date, end_date))
              return daily_data

      fake_tushare = FakeTuShare()
      alice_token = self._login("alice", "Alice@123!")
      with patch("app.main.tushare_config.token", ""), \
          patch("app.main.get_eastmoney_service", return_value=FakeEastMoney()), \
          patch("app.main.get_tushare_service", return_value=fake_tushare):
          refresh_response = self.client.get(
              "/api/stocks/refresh-all",
              headers={"Authorization": f"Bearer {alice_token}"},
          )

      self.assertEqual(refresh_response.status_code, 200, refresh_response.text)
      self.assertEqual(fake_tushare.calls[0][0], "601398.SH")
      history_rows = self.db.query(PricePointDB).filter(PricePointDB.stock_code == "601398").all()
      self.assertEqual(len(history_rows), len(daily_data))

      detail_response = self.client.get(
          "/api/stocks/601398",
          headers={"Authorization": f"Bearer {alice_token}"},
      )
      self.assertEqual(detail_response.status_code, 200, detail_response.text)
      self.assertGreater(len(detail_response.json()["strategies"]), 0)


if __name__ == "__main__":
    unittest.main()
