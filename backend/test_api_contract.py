import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

db_file = tempfile.NamedTemporaryFile(prefix="aistock-test-", suffix=".db", delete=False)
db_file.close()

os.environ["DB_DIALECT"] = "sqlite"
os.environ["DB_NAME"] = db_file.name

from fastapi.testclient import TestClient

from backend.app.database import AuthSession, SessionLocal, User, WatchlistItem
from backend.app.main import app, validate_password_strength


def assert_stock_list(payload, label: str):
    if not isinstance(payload, list):
        raise AssertionError(f"{label}: expected a list, got {type(payload).__name__}")
    if not payload:
        raise AssertionError(f"{label}: expected at least one stock")
    for stock in payload:
        for key in ("code", "name", "price", "change_percent", "score", "signal"):
            if key not in stock:
                raise AssertionError(f"{label}: missing {key} in {stock}")


def assert_response(response, expected_status: int, label: str):
    if response.status_code != expected_status:
        raise AssertionError(
            f"{label}: expected HTTP {expected_status}, got {response.status_code}: {response.text}"
        )


def main():
    with TestClient(app) as client:
        assert_stock_list(client.get("/api/stocks").json(), "stock list")
        assert_stock_list(client.get("/api/stocks/search?q=ping").json(), "stock search")

        strategy_response = client.get("/api/stocks/600519/strategies/600519-trend-breakout")
        assert_response(strategy_response, 200, "strategy detail")
        strategy_detail = strategy_response.json()
        for key in ("strategy", "annualized_return", "sharpe_ratio", "trade_count", "rules", "trades"):
            if key not in strategy_detail:
                raise AssertionError(f"strategy detail: missing {key}")

        first_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        second_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert_response(first_login, 200, "login")
        assert_response(second_login, 200, "second login")
        if first_login.json()["token"] == second_login.json()["token"]:
            raise AssertionError("login: tokens must not be deterministic")

        generated = client.get("/api/auth/generate-password")
        assert_response(generated, 200, "generate password")
        generated_password = generated.json()["password"]
        strength = validate_password_strength(generated_password)
        if not strength["valid"]:
            raise AssertionError(f"generate password: generated weak password {generated_password!r}")

        weak_change = client.post(
            "/api/auth/change-password",
            json={"username": "admin", "old_password": "admin123", "new_password": "weak"},
        )
        assert_response(weak_change, 400, "weak password rejection")

        new_password = "Strong!234"
        strong_change = client.post(
            "/api/auth/change-password",
            json={"username": "admin", "old_password": "admin123", "new_password": new_password},
        )
        assert_response(strong_change, 200, "strong password change")

        old_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert_response(old_login, 401, "old password rejected")
        new_login = client.post("/api/auth/login", json={"username": "admin", "password": new_password})
        assert_response(new_login, 200, "new password login")

        db = SessionLocal()
        try:
            admin = db.query(User).filter(User.username == "admin").first()
            if not admin:
                raise AssertionError("password storage: admin user missing")
            if admin.password == new_password or not admin.password.startswith("pbkdf2_sha256$"):
                raise AssertionError("password storage: password must be stored as a PBKDF2 hash")
            session_count = db.query(AuthSession).filter(AuthSession.user_id == admin.id).count()
            if session_count < 3:
                raise AssertionError(f"auth sessions: expected persisted login sessions, got {session_count}")
        finally:
            db.close()

        initial_watchlist = client.get("/api/watchlist")
        assert_response(initial_watchlist, 200, "initial watchlist")
        if initial_watchlist.json()["codes"] != []:
            raise AssertionError(f"initial watchlist: expected empty list, got {initial_watchlist.json()}")

        add_response = client.post("/api/watchlist/600519")
        assert_response(add_response, 200, "watchlist add")
        added_codes = [stock["code"] for stock in add_response.json()]
        if added_codes != ["600519"]:
            raise AssertionError(f"watchlist add: expected ['600519'], got {added_codes}")

        persisted_watchlist = client.get("/api/watchlist")
        assert_response(persisted_watchlist, 200, "persisted watchlist")
        if persisted_watchlist.json()["codes"] != ["600519"]:
            raise AssertionError(f"persisted watchlist: expected ['600519'], got {persisted_watchlist.json()}")

        db = SessionLocal()
        try:
            count = db.query(WatchlistItem).count()
            if count != 1:
                raise AssertionError(f"watchlist persistence: expected 1 row, got {count}")
        finally:
            db.close()

        remove_response = client.delete("/api/watchlist/600519")
        assert_response(remove_response, 200, "watchlist remove")
        if remove_response.json() != []:
            raise AssertionError(f"watchlist remove: expected empty stock list, got {remove_response.json()}")

    try:
        os.unlink(db_file.name)
    except OSError:
        pass


if __name__ == "__main__":
    main()
