from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Callable
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.database import PricePointDB, Stock


logger = logging.getLogger("stocks")
MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class StockDataOperations:
    get_tushare_service: Callable[[], Any] | None = None
    get_realtime_quotes: Callable[[list[str]], list[dict]] | None = None


def get_price_history(db: Session, code: str) -> list[PricePointDB]:
    return db.query(PricePointDB).filter(PricePointDB.stock_code == code).order_by(PricePointDB.date).all()


def _item_value(item, key: str, default=None):
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def _format_date(value) -> str:
    text = str(value or "").strip()
    return f"{text[:4]}-{text[4:6]}-{text[6:]}" if len(text) == 8 and text.isdigit() else text


def _stock_ts_code(stock: Stock) -> str:
    return getattr(stock, "ts_code", None) or f"{stock.code}{'.SH' if stock.code.startswith(('5', '6', '9')) else '.SZ'}"


def update_stock_realtime_quote(db: Session, stock: Stock, operations: StockDataOperations) -> None:
    try:
        quotes = operations.get_realtime_quotes([stock.code])
        if not quotes:
            return
        quote = quotes[0]
        stock.price = quote.get("price", stock.price or 0)
        stock.change_percent = quote.get("change_percent", stock.change_percent or 0)
        stock.name = quote.get("name", stock.name)
        stock.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(stock)
    except Exception as exc:
        logger.error("Failed to update realtime quote for stock %s: %s", stock.code, exc)
        db.rollback()


def is_trading_time() -> bool:
    now = datetime.now(MARKET_TIMEZONE).replace(tzinfo=None)
    if now.weekday() >= 5:
        return False
    hour, minute = now.hour, now.minute
    return (
        (hour == 9 and minute >= 30)
        or hour == 10
        or (hour == 11 and minute < 30)
        or hour in (13, 14)
    )


def is_morning_break_time() -> bool:
    now = datetime.now(MARKET_TIMEZONE).replace(tzinfo=None)
    if now.weekday() >= 5:
        return False
    return (now.hour == 11 and now.minute >= 30) or now.hour == 12


def _previous_weekday(value: datetime) -> datetime:
    previous = value - timedelta(days=1)
    while previous.weekday() >= 5:
        previous -= timedelta(days=1)
    return previous


def last_market_session_end_time(*, morning_break_time: Callable[[], bool] = is_morning_break_time) -> datetime:
    now = datetime.now(MARKET_TIMEZONE).replace(tzinfo=None)
    today = now.date()
    if now.weekday() < 5:
        if now.hour >= 15:
            return datetime.combine(today, datetime.min.time()).replace(hour=15)
        if morning_break_time():
            return datetime.combine(today, datetime.min.time()).replace(hour=11, minute=30)
        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            previous = _previous_weekday(now)
            return datetime.combine(previous.date(), datetime.min.time()).replace(hour=15)
    previous = _previous_weekday(now)
    return datetime.combine(previous.date(), datetime.min.time()).replace(hour=15)


def history_needs_refresh(
    history: list[PricePointDB],
    stock: Stock,
    *,
    is_trading_time: Callable[[], bool] = is_trading_time,
    last_market_session_end_time: Callable[[], datetime] = last_market_session_end_time,
) -> bool:
    if not history:
        return True
    latest = max(history, key=lambda price: price.date)
    try:
        latest_date = datetime.strptime(latest.date, "%Y-%m-%d").date()
    except ValueError:
        return True
    if stock.updated_at is None:
        return True
    last_update = stock.updated_at
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)
    last_update = last_update.astimezone(MARKET_TIMEZONE).replace(tzinfo=None)
    now = datetime.now(MARKET_TIMEZONE).replace(tzinfo=None)
    if is_trading_time():
        return (now - last_update).total_seconds() / 60 > 5
    last_session_end = last_market_session_end_time()
    return latest_date < last_session_end.date() or last_update < last_session_end


def ensure_price_history(
    db: Session,
    stock: Stock,
    operations: StockDataOperations,
    *,
    needs_refresh: Callable[[list[PricePointDB], Stock], bool],
) -> list[PricePointDB]:
    history = get_price_history(db, stock.code)
    if not needs_refresh(history, stock):
        return history
    try:
        end_date = datetime.now().strftime("%Y%m%d")
        if history:
            latest_date = max(point.date for point in history)
            start_date = latest_date.replace("-", "")
        else:
            start_date = (datetime.now() - timedelta(days=720)).strftime("%Y%m%d")
        daily_data = operations.get_tushare_service().get_daily_price(_stock_ts_code(stock), start_date, end_date)
        if not daily_data:
            stock.data_status = "partial" if not history else stock.data_status
            db.commit()
            return history
        for item in daily_data:
            date = _format_date(_item_value(item, "date") or _item_value(item, "trade_date"))
            close = float(_item_value(item, "close", 0) or 0)
            if not date or close <= 0:
                continue
            existing = db.query(PricePointDB).filter(
                PricePointDB.stock_code == stock.code,
                PricePointDB.date == date,
            ).first()
            values = {
                "open": float(_item_value(item, "open", close) or close),
                "high": float(_item_value(item, "high", close) or close),
                "low": float(_item_value(item, "low", close) or close),
                "close": close,
                "volume": int(_item_value(item, "volume", _item_value(item, "vol", 0)) or 0),
            }
            if existing:
                for key, value in values.items():
                    setattr(existing, key, value)
            else:
                db.add(PricePointDB(stock_code=stock.code, date=date, **values))
        stock.data_status = "normal"
        stock.updated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        logger.error("Failed to ensure price history for stock %s: %s", stock.code, exc)
        db.rollback()
        return history
    return sorted(get_price_history(db, stock.code), key=lambda price: price.date)
