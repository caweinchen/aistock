from datetime import datetime, timezone, timedelta
import logging
import re
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.backtest_engine import BacktestResult, build_strategy_summaries, run_backtest
from app.config import tushare_config
from app.database import (
    AlertItemDB,
    DividendDB,
    FactorScoreDB,
    InstHoldDB,
    PricePointDB,
    Stock,
    StockNewsDB,
    StrategyResultDB,
    User,
    WatchlistItem,
    get_db,
)
from app.eastmoney_service import get_eastmoney_service
from app.ordinary_user import (
    build_data_health,
    build_pre_trade_checklist,
    build_risk_explanations,
)
from app.routers.auth import get_current_user
from app.schemas import (
    AlertItem,
    BacktestRequest,
    BacktestTrade,
    ChecklistItem,
    DataCompleteness,
    DataHealth,
    FactorScore,
    PreTradeChecklist,
    PricePoint,
    RiskExplanation,
    StockDetail,
    StockSummary,
    StrategyDetail,
    StrategyResult,
)
from app.security import hash_password
from app.stock_summary import (
    build_primary_risk,
    build_primary_support,
    determine_data_completeness,
    determine_reference_status,
    stock_to_summary,
)
from app.tushare_service import get_tushare_service, init_tushare

logger = logging.getLogger("stocks")
MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")
router = APIRouter(prefix="/api/stocks")

def build_ordinary_stock_summary(
    stock: Stock,
    factors: list[FactorScore],
    alerts: list[AlertItem],
    data_completeness: DataCompleteness,
) -> tuple[str, list[str], list[str]]:
    support_factors = [f"{factor.label}: {factor.description}" for factor in factors if factor.value >= 65][:3]
    risk_factors = [alert.message for alert in alerts[:3]]

    if data_completeness in ("insufficient", "incomplete"):
        return (
            "当前数据不足，暂不适合形成明确判断。建议补充数据后再分析。",
            support_factors,
            risk_factors or ["关键数据不完整，结论只能弱参考。"],
        )

    status = determine_reference_status(stock.score or 50, stock.signal or "neutral", data_completeness, alerts)
    if status == "positive":
        summary = "当前整体偏积极，适合加入重点观察，但仍需自行评估风险与仓位。"
    elif status == "cautious":
        summary = "当前风险项较多，建议谨慎关注，并先完成操作前检查。"
    else:
        summary = "当前整体偏中性，适合继续观察后续业绩、资金和价格趋势变化。"

    if not support_factors:
        support_factors = [build_primary_support(stock.score or 50, status)]
    if not risk_factors:
        risk_factors = [build_primary_risk(status, data_completeness)]

    return summary, support_factors, risk_factors



def data_health_to_model(result) -> DataHealth:
    return DataHealth(**result.__dict__)


def risk_explanation_to_model(result) -> RiskExplanation:
    return RiskExplanation(**result.__dict__)


def checklist_to_model(result) -> PreTradeChecklist:
    return PreTradeChecklist(
        mode=result.mode,
        title=result.title,
        completion_hint=result.completion_hint,
        items=[ChecklistItem(**item.__dict__) for item in result.items],
    )

def update_stock_realtime_quote(db: Session, stock: Stock) -> None:
    try:
        quotes = get_eastmoney_service().get_realtime_quote([stock.code])
        if not quotes:
            return
        quote = quotes[0]
        stock.price = quote.get("price", stock.price or 0)
        stock.change_percent = quote.get("change_percent", stock.change_percent or 0)
        stock.name = quote.get("name", stock.name)
        stock.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(stock)
    except Exception as e:
        logger.error(f"Failed to update realtime quote for stock {stock.code}: {e}")
        db.rollback()


def db_factor_to_model(factor: FactorScoreDB) -> FactorScore:
    return FactorScore(
        key=factor.key,
        label=factor.label,
        value=factor.value,
        description=factor.description,
    )


def db_strategy_to_model(strategy: StrategyResultDB) -> StrategyResult:
    return StrategyResult(
        id=strategy.id,
        name=strategy.name,
        period=strategy.period,
        return_rate=strategy.return_rate,
        max_drawdown=strategy.max_drawdown,
        win_rate=strategy.win_rate,
        risk=strategy.risk,
        summary=strategy.summary,
    )


def engine_result_to_strategy(result: BacktestResult) -> StrategyResult:
    return StrategyResult(
        id=result.id,
        name=result.name,
        period=result.period,
        return_rate=result.return_rate,
        max_drawdown=result.max_drawdown,
        win_rate=result.win_rate,
        risk=result.risk,
        summary=result.summary,
    )


def engine_result_to_detail(result: BacktestResult) -> StrategyDetail:
    return StrategyDetail(
        strategy=engine_result_to_strategy(result),
        annualized_return=result.annualized_return,
        sharpe_ratio=result.sharpe_ratio,
        trade_count=result.trade_count,
        rules=result.rules,
        trades=[
            BacktestTrade(
                date=trade.date,
                action=trade.action,
                price=trade.price,
                quantity=trade.quantity,
                reason=trade.reason,
            )
            for trade in result.trades
        ],
    )


def db_price_to_model(price: PricePointDB) -> PricePoint:
    return PricePoint(
        date=price.date,
        open=price.open,
        high=price.high,
        low=price.low,
        close=price.close,
        volume=price.volume,
    )


def db_alert_to_model(alert: AlertItemDB) -> AlertItem:
    return AlertItem(
        level=alert.level,
        title=alert.title,
        message=alert.message,
    )


def calculate_strategies(daily_data: list) -> list:
    return [
        {
            "id": result.id,
            "name": result.name,
            "period": result.period,
            "return_rate": result.return_rate,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "risk": result.risk,
            "summary": result.summary,
        }
        for result in build_strategy_summaries(daily_data)
    ]


def get_price_history(db: Session, code: str) -> list[PricePointDB]:
    return (
        db.query(PricePointDB)
        .filter(PricePointDB.stock_code == code)
        .order_by(PricePointDB.date)
        .all()
    )


def _item_value(item, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _format_tushare_date(value) -> str:
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def _stock_ts_code(stock: Stock) -> str:
    ts_code = getattr(stock, "ts_code", None)
    if ts_code:
        return ts_code
    suffix = ".SH" if stock.code.startswith(("5", "6", "9")) else ".SZ"
    return f"{stock.code}{suffix}"


def get_initialized_tushare_service():
    service = get_tushare_service()
    if tushare_config.token and not getattr(service, "pro", None):
        service = init_tushare(tushare_config.token)
    return service


def _is_trading_time() -> bool:
    now = datetime.now(MARKET_TIMEZONE).replace(tzinfo=None)
    weekday = now.weekday()

    if weekday >= 5:
        return False

    hour = now.hour
    minute = now.minute

    if (hour == 9 and minute >= 30) or (hour == 10) or (hour == 11 and minute < 30):
        return True
    if hour == 13 or hour == 14:
        return True

    return False

def _is_morning_break_time() -> bool:
    now = datetime.now(MARKET_TIMEZONE).replace(tzinfo=None)
    weekday = now.weekday()
    if weekday >= 5:
        return False

    hour = now.hour
    minute = now.minute

    if hour == 11 and minute >= 30:
        return True
    if hour == 12:
        return True

    return False

def _previous_weekday(value: datetime) -> datetime:
    previous = value - timedelta(days=1)
    while previous.weekday() >= 5:
        previous -= timedelta(days=1)
    return previous

def _last_market_session_end_time() -> datetime:
    now = datetime.now(MARKET_TIMEZONE).replace(tzinfo=None)
    today = now.date()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    is_today_trading_day = weekday < 5

    if is_today_trading_day:
        if (hour > 15) or (hour == 15):
            return datetime.combine(today, datetime.min.time()).replace(hour=15)
        if _is_morning_break_time():
            return datetime.combine(today, datetime.min.time()).replace(hour=11, minute=30)
        if hour < 9 or (hour == 9 and minute < 30):
            prev = _previous_weekday(now)
            return datetime.combine(prev.date(), datetime.min.time()).replace(hour=15)

    prev = _previous_weekday(now)
    return datetime.combine(prev.date(), datetime.min.time()).replace(hour=15)

def _history_needs_refresh(history: list[PricePointDB], stock: Stock) -> bool:
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

    if _is_trading_time():
        minutes_since_update = (now - last_update).total_seconds() / 60
        return minutes_since_update > 5

    last_session_end = _last_market_session_end_time()
    if latest_date < last_session_end.date():
        return True
    return last_update < last_session_end


def ensure_price_history(db: Session, stock: Stock) -> list[PricePointDB]:
    history = get_price_history(db, stock.code)
    if not _history_needs_refresh(history, stock):
        return history

    try:
        end_date = datetime.now().strftime("%Y%m%d")

        if history:
            latest_date = max(h.date for h in history)
            start_date = latest_date.replace("-", "")
            logger.info(f"Incremental update for stock {stock.code}, starting from {latest_date}")
        else:
            start_date = (datetime.now() - timedelta(days=720)).strftime("%Y%m%d")

        daily_data = get_initialized_tushare_service().get_daily_price(_stock_ts_code(stock), start_date, end_date)
        if not daily_data:
            stock.data_status = "partial" if not history else stock.data_status
            db.commit()
            return history

        updated_count = 0
        inserted_count = 0
        for item in daily_data:
            date = _format_tushare_date(_item_value(item, "date") or _item_value(item, "trade_date"))
            close = float(_item_value(item, "close", 0) or 0)
            if not date or close <= 0:
                continue

            existing = db.query(PricePointDB).filter(
                PricePointDB.stock_code == stock.code,
                PricePointDB.date == date
            ).first()

            if existing:
                existing.open = float(_item_value(item, "open", close) or close)
                existing.high = float(_item_value(item, "high", close) or close)
                existing.low = float(_item_value(item, "low", close) or close)
                existing.close = close
                existing.volume = int(_item_value(item, "volume", _item_value(item, "vol", 0)) or 0)
                updated_count += 1
            else:
                db.add(
                    PricePointDB(
                        stock_code=stock.code,
                        date=date,
                        open=float(_item_value(item, "open", close) or close),
                        high=float(_item_value(item, "high", close) or close),
                        low=float(_item_value(item, "low", close) or close),
                        close=close,
                        volume=int(_item_value(item, "volume", _item_value(item, "vol", 0)) or 0),
                    )
                )
                inserted_count += 1

        stock.data_status = "normal"
        stock.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Updated price history for stock {stock.code}: {inserted_count} inserted, {updated_count} updated")
    except Exception as e:
        logger.error(f"Failed to ensure price history for stock {stock.code}: {e}")
        db.rollback()
        return history

    refreshed_history = sorted(get_price_history(db, stock.code), key=lambda price: price.date)
    return refreshed_history


def parse_custom_strategy_id(strategy_id: str) -> tuple[str, int] | None:
    if not strategy_id.startswith("custom-"):
        return None

    try:
        template, lookback_days, _timestamp = strategy_id[len("custom-") :].rsplit("-", 2)
        return template, int(lookback_days)
    except (TypeError, ValueError):
        return None


def get_stock_detail(db: Session, code: str, update_realtime: bool = True) -> StockDetail:
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # 濡偓閺屻儲妲搁崥锕傛付鐟曚焦娲块弬鏉跨杽閺冩儼顢戦幆?
    # A閼测剝鏁归惄妯绘闂傜繝璐?5:00閿涘本鏁归惄妯烘倵閹靛秷鐑︽潻鍥ㄦ纯閺?
    now = datetime.now()
    today = now.date()
    current_hour = now.hour
    market_close_hour = 15  # A閼测剝鏁归惄妯绘闂?5:00

    need_update_realtime = update_realtime
    if stock.updated_at and update_realtime:
        last_update_date = stock.updated_at.date() if hasattr(stock.updated_at, 'date') else stock.updated_at
        if last_update_date == today and current_hour >= market_close_hour:
            need_update_realtime = False
            logger.info(f"Stock {code} already refreshed after market close today")
        elif last_update_date == today and current_hour < market_close_hour:
            logger.info(f"Stock {code} was refreshed today before market close; realtime update allowed")

    if need_update_realtime:
        update_stock_realtime_quote(db, stock)
    history = ensure_price_history(db, stock)

    # 从TuShare获取财务数据并计算因子评分
    factors = ensure_factor_scores(db, stock, history)
    # 基于真实数据生成风险预警
    alerts = ensure_alerts(db, stock, history, factors)
    custom_strategies = db.query(StrategyResultDB).filter(
        StrategyResultDB.stock_code == code,
        StrategyResultDB.id.like("custom-%"),
    ).all()
    strategy_models = [
        StrategyResult(**strategy)
        for strategy in calculate_strategies(history)
    ] + [db_strategy_to_model(strategy) for strategy in custom_strategies]
    factor_models = [db_factor_to_model(f) for f in factors]
    alert_models = [db_alert_to_model(a) for a in alerts]
    data_completeness = determine_data_completeness(stock, history, factor_models)
    holder_rows = db.query(InstHoldDB).filter(InstHoldDB.stock_code == code).all()
    dividend_rows = db.query(DividendDB).filter(DividendDB.stock_code == code).all()
    data_health_result = build_data_health(stock, history, factor_models, alert_models, holder_rows, dividend_rows)
    risk_results = build_risk_explanations(stock, factor_models, alert_models, holder_rows, dividend_rows, data_health_result)
    buy_checklist_result = build_pre_trade_checklist(stock, risk_results, data_health_result, mode="buy")
    sell_checklist_result = build_pre_trade_checklist(stock, risk_results, data_health_result, mode="sell")
    ordinary_summary, support_factors, risk_factors = build_ordinary_stock_summary(
        stock,
        factor_models,
        alert_models,
        data_completeness,
    )

    return StockDetail(
        stock=stock_to_summary(stock, history, factor_models, alert_models),
        factors=factor_models,
        strategies=strategy_models,
        alerts=alert_models,
        history=[db_price_to_model(h) for h in history],
        # 基于真实数据生成AI摘要
        ai_summary=ensure_ai_summary(db, stock, history, factors, alerts),
        data_status=stock.data_status,
        updated_at=stock.updated_at,
        ordinary_summary=ordinary_summary,
        support_factors=support_factors,
        risk_factors=risk_factors,
        data_completeness=data_completeness,
        data_updated_at=stock.updated_at,
        data_health=data_health_to_model(data_health_result),
        risk_explanations=[risk_explanation_to_model(result) for result in risk_results],
        buy_checklist=checklist_to_model(buy_checklist_result),
        sell_checklist=checklist_to_model(sell_checklist_result),
    )


def ensure_stock_related_data(db: Session, stock: Stock) -> None:
    try:
        history = ensure_price_history(db, stock)
        if not history:
            logger.warning(f"No price history for stock {stock.code}, skipping related data calculation")
            return

        factors = ensure_factor_scores(db, stock, history)
        alerts = ensure_alerts(db, stock, history, factors)
        ensure_ai_summary(db, stock, history, factors, alerts)

        strategies = calculate_strategies(history)
        for strategy in strategies:
            existing = db.query(StrategyResultDB).filter(
                StrategyResultDB.stock_code == stock.code,
                StrategyResultDB.id == strategy["id"],
            ).first()
            if existing:
                existing.name = strategy["name"]
                existing.period = strategy["period"]
                existing.return_rate = strategy["return_rate"]
                existing.max_drawdown = strategy["max_drawdown"]
                existing.win_rate = strategy["win_rate"]
                existing.risk = strategy["risk"]
                existing.summary = strategy["summary"]
            else:
                db.add(StrategyResultDB(
                    id=strategy["id"],
                    stock_code=stock.code,
                    name=strategy["name"],
                    period=strategy["period"],
                    return_rate=strategy["return_rate"],
                    max_drawdown=strategy["max_drawdown"],
                    win_rate=strategy["win_rate"],
                    risk=strategy["risk"],
                    summary=strategy["summary"],
                ))
        db.commit()
        logger.info(f"Updated strategy results for stock {stock.code}")
    except Exception as e:
        logger.error(f"Failed to ensure related data for stock {stock.code}: {e}")
        db.rollback()


def get_watchlist_user(db: Session, username: str = "admin") -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user

    user = User(username=username, password=hash_password("admin123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[StockSummary])
def get_stocks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取当前用户的自选股列表"""
    try:
        # 获取用户的自选股代码
        watchlist_items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()
        codes = [item.stock_code for item in watchlist_items]

        if not codes:
            logger.info(f"User [{user.username}] has no watchlist items")
            return []

        # 查询自选股详情
        stocks = db.query(Stock).filter(Stock.code.in_(codes)).all()

        # 尝试更新实时行情
        if codes:
            try:
                eastmoney = get_eastmoney_service()
                quotes = eastmoney.get_realtime_quote(codes)
                if quotes:
                    for quote in quotes:
                        stock = db.query(Stock).filter(Stock.code == quote.get('code')).first()
                        if stock:
                            stock.price = quote.get('price', 0)
                            stock.change_percent = quote.get('change_percent', 0)
                            stock.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    logger.info(f"Updated realtime quotes for user [{user.username}]: {len(quotes)} stocks")
            except Exception as e:
                logger.error(f"Failed to update realtime quotes: {e}")
                db.rollback()

        logger.info(f"Loaded watchlist for user [{user.username}]: {len(stocks)} stocks")
        return [stock_to_summary(s) for s in stocks]
    except Exception as e:
        logger.error(f"Failed to load watchlist for user [{user.username}]: {e}")
        raise HTTPException(status_code=500, detail="Failed to load stock list")


@router.get("/refresh-all", response_model=list[StockSummary])
def refresh_all_stocks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """批量刷新当前用户所有自选股的实时数据和历史行情并保存到数据库"""
    logger.info(f"Starting batch refresh for user [{user.username}]")

    try:
        watchlist_items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()
        codes = [item.stock_code for item in watchlist_items]

        if not codes:
            logger.info(f"User [{user.username}] has no watchlist items to refresh")
            return []

        logger.info(f"Refreshing {len(codes)} stocks for user [{user.username}]")

        eastmoney = get_eastmoney_service()
        quotes = eastmoney.get_realtime_quote(codes)

        if quotes:
            updated_count = 0
            for quote in quotes:
                code = quote.get('code')
                stock = db.query(Stock).filter(Stock.code == code).first()
                if stock:
                    old_price = stock.price
                    stock.price = quote.get('price', 0)
                    stock.change_percent = quote.get('change_percent', 0)
                    stock.name = quote.get('name', stock.name)
                    stock.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                    logger.debug(f"Updated {code}: {old_price} -> {stock.price}")

            db.commit()
            logger.info(f"Successfully refreshed {updated_count}/{len(quotes)} stocks for user [{user.username}]")
        else:
            logger.warning("No quotes received from EastMoney")

        for code in codes:
            stock = db.query(Stock).filter(Stock.code == code).first()
            if stock:
                ensure_stock_related_data(db, stock)

        updated_stocks = db.query(Stock).filter(Stock.code.in_(codes)).all()
        return [stock_to_summary(s) for s in updated_stocks]

    except Exception as e:
        logger.error(f"Batch refresh failed for user [{user.username}]: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Batch refresh failed: {str(e)}")


@router.get("/search", response_model=list[StockSummary])
def search_stocks(q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    keyword = q.strip()
    if not keyword:
        return get_stocks(db, user)

    logger.info(f"Searching stocks with keyword: {keyword}")

    try:
        stocks = db.query(Stock).filter(
            (Stock.code.ilike(f"%{keyword}%")) |
            (Stock.name.ilike(f"%{keyword}%")) |
            (Stock.english_name.ilike(f"%{keyword}%"))
        ).all()

        if stocks:
            logger.info(f"Database search returned {len(stocks)} results for {keyword}")
            return [stock_to_summary(s) for s in stocks]
    except Exception as e:
        logger.error(f"Database search failed for keyword '{keyword}': {e}")

    eastmoney = get_eastmoney_service()
    search_results = eastmoney.search_stocks(keyword)

    if search_results:
        summaries = []
        for r in search_results:
            code = r.get('code', '')
            name = r.get('name', '')
            ts_code = r.get('ts_code', '')
            market = r.get('market', '')

            try:
                existing = db.query(Stock).filter(Stock.code == code).first()
                if not existing:
                    stock = Stock(
                        code=code,
                        name=name,
                        ts_code=ts_code or code,
                        market=market or ('SH' if code.startswith(('6', '5', '9')) else 'SZ'),
                    )
                    db.add(stock)
                    db.commit()
                    logger.info(f"Created stock from search result: {code} - {name}")
            except Exception as e:
                logger.error(f"Failed to save search result stock {code}: {e}")
                db.rollback()

            try:
                quotes = eastmoney.get_realtime_quote([code])
                if quotes:
                    quote = quotes[0]
                    summaries.append(StockSummary(
                        code=code,
                        name=name,
                        price=quote.get('price', 0),
                        change_percent=quote.get('change_percent', 0),
                        score=50,
                        signal="neutral"
                    ))
                else:
                    summaries.append(StockSummary(
                        code=code,
                        name=name,
                        price=0,
                        change_percent=0,
                        score=50,
                        signal="neutral"
                    ))
            except Exception as e:
                logger.error(f"Failed to fetch realtime quote for search result {code}: {e}")
                summaries.append(StockSummary(
                    code=code,
                    name=name,
                    price=0,
                    change_percent=0,
                    score=50,
                    signal="neutral"
                ))

        logger.info(f"EastMoney search returned {len(summaries)} results for {keyword}")
        return summaries

    logger.warning(f"No stock search results for keyword: {keyword}")
    return []

@router.get("/{code}", response_model=StockDetail)
def get_stock_detail_api(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logger.info(f"Loading stock detail: {code}")

    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        logger.info(f"Stock {code} not found locally; fetching stock info")
        try:
            from app.eastmoney_service import get_stock_info_by_code
            stock_info = get_stock_info_by_code(code)
            if stock_info:
                stock = Stock(
                    code=stock_info.get('code', code),
                    name=stock_info.get('name', ''),
                    ts_code=stock_info.get('ts_code', code),
                    market=stock_info.get('market', ''),
                )
                db.add(stock)
                db.commit()
                db.refresh(stock)
                logger.info(f"Created stock while loading detail: {code} - {stock.name}")
            else:
                logger.error(f"Stock info not found for code: {code}")
                raise HTTPException(status_code=404, detail="Stock not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to load stock detail for {code}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get stock detail")

    return get_stock_detail(db, code)

@router.get("/{code}/strategies", response_model=list[StrategyResult])
def get_stock_strategies(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_stock_detail(db, code).strategies


@router.get("/{code}/strategies/{strategy_id}", response_model=StrategyDetail)
def get_stock_strategy_detail(code: str, strategy_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    detail = get_stock_detail(db, code)
    for strategy in detail.strategies:
        if strategy.id == strategy_id:
            return build_strategy_detail(detail, strategy)
    raise HTTPException(status_code=404, detail="Strategy not found")


@router.get("/{code}/history", response_model=list[PricePoint])
def get_stock_history(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    history = get_price_history(db, code)
    return [db_price_to_model(h) for h in history]


@router.get("/{code}/realtime")
def get_stock_realtime(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """閼惧嘲褰囬懖锛勩偍鐎圭偞妞傜悰灞惧剰"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()
    quote = tushare_svc.get_realtime_quote(code)

    if not quote:
        raise HTTPException(status_code=404, detail="Failed to get realtime quote")

    return quote


@router.get("/{code}/dividend")
def get_stock_dividend(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取股票分红记录"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")
    tushare_svc = get_tushare_service()
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Allow client to force a fresh fetch with ?force=true
    force: bool = Query(False)

    if not force:
        cached = db.query(DividendDB).filter(DividendDB.stock_code == code).order_by(DividendDB.ann_date.desc()).all()
        if cached and len(cached) > 0:
            results = []
            for c in cached:
                results.append({
                    'ts_code': code,
                    'div_proc': '',
                    'ann_date': c.ann_date,
                    'record_date': c.record_date,
                    'ex_date': c.ex_date,
                    'pay_date': c.pay_date,
                    'div_cash': c.div_cash,
                    'bonus_share': c.bonus_share,
                    'transfer_share': c.transfer_share,
                })
            return results

    dividend = tushare_svc.get_dividend(_stock_ts_code(stock))
    # If TuShare reported a last_error on the service, surface it as diagnostic 502
    if getattr(tushare_svc, 'last_error', None) and isinstance(getattr(tushare_svc, 'last_error'), dict):
        raise HTTPException(status_code=502, detail=tushare_svc.last_error)
    if dividend:
        try:
            db.query(DividendDB).filter(DividendDB.stock_code == code).delete()
            for item in dividend:
                db.add(DividendDB(
                    stock_code=code,
                    ann_date=item.get('ann_date', '') or '',
                    record_date=item.get('record_date', '') or '',
                    ex_date=item.get('ex_date', '') or '',
                    pay_date=item.get('pay_date', '') or '',
                    div_cash=float(item.get('div_cash', 0) or 0),
                    bonus_share=float(item.get('bonus_share', 0) or 0),
                    transfer_share=float(item.get('transfer_share', 0) or 0),
                ))
            db.commit()
        except Exception:
            db.rollback()

    return dividend


@router.get("/{code}/news")
def get_stock_news(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取股票重大事件/新闻"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")
    tushare_svc = get_tushare_service()
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    force: bool = Query(False)

    if not force:
        cached = db.query(StockNewsDB).filter(StockNewsDB.stock_code == code).order_by(StockNewsDB.pub_time.desc()).all()
        if cached and len(cached) > 0:
            results = []
            for c in cached:
                results.append({
                    'ts_code': code,
                    'title': c.title,
                    'content': c.content,
                    'pub_time': c.pub_time,
                    'src': c.source,
                })
            return results

    news = tushare_svc.get_stock_news(_stock_ts_code(stock))
    if getattr(tushare_svc, 'last_error', None) and isinstance(getattr(tushare_svc, 'last_error'), dict):
        raise HTTPException(status_code=502, detail=tushare_svc.last_error)
    if news:
        try:
            db.query(StockNewsDB).filter(StockNewsDB.stock_code == code).delete()
            for item in news:
                db.add(StockNewsDB(
                    stock_code=code,
                    title=item.get('title', '') or '',
                    content=item.get('content', '') or '',
                    pub_time=str(item.get('pub_time', '') or ''),
                    source=item.get('src', '') or '',
                ))
            db.commit()
        except Exception:
            db.rollback()

    return news


@router.get("/{code}/adj-factor")
def get_stock_adj_factor(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取股票除权除息信息"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    adj_factor = tushare_svc.get_adj_factor(_stock_ts_code(stock))
    if getattr(tushare_svc, 'last_error', None) and isinstance(getattr(tushare_svc, 'last_error'), dict):
        raise HTTPException(status_code=502, detail=tushare_svc.last_error)
    return adj_factor


@router.get("/{code}/inst-hold")
def get_stock_inst_hold(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取机构持仓数据（按时间倒序）"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")
    tushare_svc = get_tushare_service()
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    force: bool = Query(False)

    if not force:
        cached = db.query(InstHoldDB).filter(InstHoldDB.stock_code == code).order_by(InstHoldDB.trade_date.desc()).all()
        if cached and len(cached) > 0:
            results = []
            for c in cached:
                results.append({
                    'ts_code': code,
                    'trade_date': c.trade_date,
                    'inst_type': c.inst_type,
                    'hold_amount': c.hold_amount,
                    'hold_ratio': c.hold_ratio,
                    'change_amount': c.change_amount,
                    'change_ratio': c.change_ratio,
                })
            return results

    inst_hold = tushare_svc.get_inst_hold(_stock_ts_code(stock))
    if getattr(tushare_svc, 'last_error', None) and isinstance(getattr(tushare_svc, 'last_error'), dict):
        raise HTTPException(status_code=502, detail=tushare_svc.last_error)
    if inst_hold:
        try:
            db.query(InstHoldDB).filter(InstHoldDB.stock_code == code).delete()
            for item in inst_hold:
                db.add(InstHoldDB(
                    stock_code=code,
                    trade_date=item.get('trade_date', '') or '',
                    inst_type=item.get('inst_type', '') or '',
                    hold_amount=float(item.get('hold_amount', 0) or 0),
                    hold_ratio=float(item.get('hold_ratio', 0) or 0),
                    change_amount=float(item.get('change_amount', 0) or 0),
                    change_ratio=float(item.get('change_ratio', 0) or 0),
                ))
            db.commit()
        except Exception:
            db.rollback()

    return inst_hold


@router.get("/{code}/refresh")
def refresh_stock_data(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Refresh stock data from TuShare."""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()

    # 閼惧嘲褰囩€圭偞妞傜悰灞惧剰
    quote = tushare_svc.get_realtime_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail="Failed to get realtime quote")

    # 閺囧瓨鏌婇弫鐗堝祦鎼存挷鑵戦惃鍕亗缁併劋淇婇幁?
    stock = db.query(Stock).filter(Stock.code == code).first()
    if stock:
        stock.price = quote.get('price', stock.price)
        stock.change_percent = quote.get('change_pct', stock.change_percent)
        stock.updated_at = datetime.now(timezone.utc)
        db.commit()

    return {
        "success": True,
        "message": f"Stock {code} data refreshed",
        "price": quote.get('price'),
        "change_pct": quote.get('change_pct')
    }


@router.get("/{code}/factors", response_model=list[FactorScore])
def get_stock_factors(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 从TuShare获取财务数据并计算因子评分
    factors = ensure_factor_scores(db, stock, history)
    return [db_factor_to_model(f) for f in factors]


@router.get("/{code}/alerts", response_model=list[AlertItem])
def get_stock_alerts(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 基于真实数据生成风险预警
    alerts = ensure_alerts(db, stock, history, factors)
    return [db_alert_to_model(a) for a in alerts]


def build_strategy_detail(detail: StockDetail, strategy: StrategyResult) -> StrategyDetail:
    strategy_id = strategy.id
    lookback_days = None
    custom_strategy = parse_custom_strategy_id(strategy.id)
    if custom_strategy:
        strategy_id, lookback_days = custom_strategy

    result = run_backtest(
        strategy_id,
        detail.history,
        name=strategy.name,
        lookback_days=lookback_days,
        risk=strategy.risk,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Insufficient price history for backtest")
    if custom_strategy:
        result = BacktestResult(
            template=result.template,
            id=strategy.id,
            name=result.name,
            period=strategy.period,
            return_rate=result.return_rate,
            max_drawdown=result.max_drawdown,
            win_rate=result.win_rate,
            risk=result.risk,
            summary=result.summary,
            annualized_return=result.annualized_return,
            sharpe_ratio=result.sharpe_ratio,
            trade_count=result.trade_count,
            rules=result.rules,
            trades=result.trades,
        )
    return engine_result_to_detail(result)


def build_custom_backtest(detail: StockDetail, request: BacktestRequest) -> StrategyDetail:
    strategy_id = f"custom-{request.template}-{request.lookback_days}-{int(datetime.now().timestamp())}"
    result = run_backtest(
        request.template,
        detail.history,
        name=request.name.strip() or None,
        lookback_days=request.lookback_days,
        risk=request.risk,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Insufficient price history for backtest")
    result = BacktestResult(
        template=result.template,
        id=strategy_id,
        name=result.name,
        period=f"Last {request.lookback_days} days",
        return_rate=result.return_rate,
        max_drawdown=result.max_drawdown,
        win_rate=result.win_rate,
        risk=result.risk,
        summary=result.summary,
        annualized_return=result.annualized_return,
        sharpe_ratio=result.sharpe_ratio,
        trade_count=result.trade_count,
        rules=result.rules,
        trades=result.trades,
    )
    return engine_result_to_detail(result)





def get_item_value(item, key, default=None):
    """Get a value from a dict or object."""
    if hasattr(item, key):
        return getattr(item, key, default)
    elif isinstance(item, dict):
        return item.get(key, default)
    return default



import re


def ensure_factor_scores(db: Session, stock: Stock, history: list) -> list[FactorScore]:
    """从TuShare获取财务数据并计算因子评分"""
    ts_code = _stock_ts_code(stock)
    factors = []

    try:
        tushare = get_tushare_service()
        if tushare.pro:
            daily_basic = tushare.get_daily_basic(ts_code)
            fina_indicator = tushare.get_fina_indicator(ts_code)
            moneyflow = tushare.get_moneyflow(ts_code)
            factors = calculate_factors_from_financial(history, daily_basic, fina_indicator, moneyflow)
            if factors:
                db.query(FactorScoreDB).filter(FactorScoreDB.stock_code == stock.code).delete()
                for factor in factors:
                    db.add(FactorScoreDB(
                        stock_code=stock.code,
                        key=factor.key,
                        label=factor.label,
                        value=factor.value,
                        description=factor.description,
                    ))
                db.commit()
                logger.info(f"Updated factor scores for stock: {stock.code}")
                return factors
    except Exception as e:
        logger.error(f"Failed to fetch financial data for stock {stock.code}: {e}")
        db.rollback()
    if not factors and history:
        factors = calculate_factors(history)
        if factors:
            db.query(FactorScoreDB).filter(FactorScoreDB.stock_code == stock.code).delete()
            for factor in factors:
                db.add(FactorScoreDB(
                    stock_code=stock.code,
                    key=_item_value(factor, "key", ""),
                    label=_item_value(factor, "label", ""),
                    value=_item_value(factor, "value", 50),
                    description=_item_value(factor, "description", ""),
                ))
            db.commit()

    return [db_factor_to_model(f) for f in db.query(FactorScoreDB).filter(FactorScoreDB.stock_code == stock.code).all()]


def calculate_factors_from_financial(history: list, daily_basic: dict, fina_indicator: dict, moneyflow: list) -> list[FactorScore]:
    """基于真实财务数据计算因子评分"""
    factors = []

    # 1. 资金流向因子
    capital_flow_score = 50
    capital_flow_desc = "资金流向稳定。"
    if moneyflow:
        recent_flows = moneyflow[:5] if len(moneyflow) >= 5 else moneyflow
        net_mf_amounts = [float(m.get('net_mf_amount', 0) or 0) for m in recent_flows]
        total_net = sum(net_mf_amounts)
        if total_net > 0:
            capital_flow_score = min(85, 50 + int(total_net / 10000))
            capital_flow_desc = f"近5日主力资金净流入{total_net/10000:.1f}万元。"
        elif total_net < 0:
            capital_flow_score = max(20, 50 + int(total_net / 10000))
            capital_flow_desc = f"近5日主力资金净流出{abs(total_net)/10000:.1f}万元。"

    factors.append(FactorScore(key="capital_flow", label="Capital Flow", value=capital_flow_score, description=capital_flow_desc))

    # 2. 估值因子
    valuation_score = 50
    valuation_desc = "估值处于合理水平。"
    if daily_basic:
        pe = daily_basic.get('pe_ttm', 0) or daily_basic.get('pe', 0)
        pb = daily_basic.get('pb', 0)
        if pe > 0:
            if pe < 15:
                valuation_score = 80
                valuation_desc = f"PE(TTM)={pe:.1f}倍，估值明显偏低。"
            elif pe < 25:
                valuation_score = 65
                valuation_desc = f"PE(TTM)={pe:.1f}倍，估值合理偏低。"
            elif pe < 40:
                valuation_score = 50
                valuation_desc = f"PE(TTM)={pe:.1f}倍，估值中等。"
            elif pe < 60:
                valuation_score = 35
                valuation_desc = f"PE(TTM)={pe:.1f}倍，估值偏高。"
            else:
                valuation_score = 25
                valuation_desc = f"PE(TTM)={pe:.1f}倍，估值明显偏高。"
        if pb > 0 and pb < 1:
            valuation_score = min(90, valuation_score + 10)
            valuation_desc += f" PB={pb:.2f}倍。"

    factors.append(FactorScore(key="valuation", label="Valuation", value=valuation_score, description=valuation_desc))

    # 3. 动量因子
    momentum_score = 50
    momentum_desc = "动量中性。"
    if history and len(history) >= 20:
        closes = [h.close for h in history[-30:]] if len(history) >= 30 else [h.close for h in history]
        if len(closes) >= 5:
            ma5 = sum(closes[-5:]) / 5
            ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)
            current_price = closes[-1]
            if current_price > ma5 > ma20:
                momentum_score = 75
                momentum_desc = "价格位于MA5和MA20之上，上涨动能强劲。"
            elif current_price > ma5:
                momentum_score = 60
                momentum_desc = "价格位于MA5之上，短期动能向好。"
            elif current_price < ma5 < ma20:
                momentum_score = 30
                momentum_desc = "价格位于MA5和MA20之下，下跌动能明显。"
            elif current_price < ma5:
                momentum_score = 40
                momentum_desc = "价格位于MA5之下，短期动能偏弱。"

    factors.append(FactorScore(key="momentum", label="Momentum", value=momentum_score, description=momentum_desc))

    # 4. 波动性因子
    volatility_score = 50
    volatility_desc = "波动适中。"
    if history and len(history) >= 10:
        closes = [h.close for h in history[-20:]] if len(history) >= 20 else [h.close for h in history]
        if len(closes) >= 10:
            changes = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes)) if closes[i-1] > 0]
            if changes:
                avg_change = sum(abs(c) for c in changes) / len(changes)
                if avg_change > 3:
                    volatility_score = 70
                    volatility_desc = f"日均波动{avg_change:.1f}%，波动较大。"
                elif avg_change < 1.5:
                    volatility_score = 35
                    volatility_desc = f"日均波动{avg_change:.1f}%，波动较小。"
                else:
                    volatility_desc = f"日均波动{avg_change:.1f}%，波动适中。"

    if fina_indicator:
        debt_ratio = fina_indicator.get('debt_to_assets', 0)
        if debt_ratio > 70:
            volatility_score = min(85, volatility_score + 15)
            volatility_desc += f" 资产负债率{debt_ratio:.1f}%，财务风险较高。"
        elif debt_ratio < 40:
            volatility_score = max(30, volatility_score - 10)
            volatility_desc += f" 资产负债率{debt_ratio:.1f}%，财务稳健。"

    factors.append(FactorScore(key="volatility", label="Volatility", value=volatility_score, description=volatility_desc))

    # 5. 盈利能力因子
    profitability_score = 50
    profitability_desc = "盈利能力一般。"
    if fina_indicator:
        roe = fina_indicator.get('roe', 0) or fina_indicator.get('roe_dt', 0)
        net_margin = fina_indicator.get('netprofit_margin', 0)
        if roe > 0:
            if roe > 20:
                profitability_score = 85
                profitability_desc = f"ROE={roe:.1f}%，盈利能力优秀。"
            elif roe > 15:
                profitability_score = 70
                profitability_desc = f"ROE={roe:.1f}%，盈利能力良好。"
            elif roe > 10:
                profitability_score = 55
                profitability_desc = f"ROE={roe:.1f}%，盈利能力中等。"
            elif roe > 5:
                profitability_score = 40
                profitability_desc = f"ROE={roe:.1f}%，盈利能力偏弱。"
            else:
                profitability_score = 25
                profitability_desc = f"ROE={roe:.1f}%，盈利能力较差。"
        if net_margin > 0:
            profitability_desc += f" 净利率{net_margin:.1f}%。"

    factors.append(FactorScore(key="profitability", label="Profitability", value=profitability_score, description=profitability_desc))

    return factors


def ensure_alerts(db: Session, stock: Stock, history: list, factors: list) -> list[AlertItem]:
    """基于真实数据生成风险预警"""
    alerts = []

    valuation_factor = next((f for f in factors if f.key == 'valuation'), None)
    if valuation_factor and valuation_factor.value > 70:
        if 'PE' in valuation_factor.description:
            pe_match = re.search(r'PE.*?(\d+\.?\d*)', valuation_factor.description)
            if pe_match:
                pe_value = float(pe_match.group(1))
                if pe_value > 50:
                    alerts.append(AlertItem(level="high", title="估值过高风险", message=f"当前PE(TTM)为{pe_value:.1f}倍，远高于行业平均水平。"))

    volatility_factor = next((f for f in factors if f.key == 'volatility'), None)
    if volatility_factor and volatility_factor.value > 65:
        alerts.append(AlertItem(level="medium", title="波动性风险", message=volatility_factor.description))

    capital_factor = next((f for f in factors if f.key == 'capital_flow'), None)
    if capital_factor and capital_factor.value < 35:
        alerts.append(AlertItem(level="medium", title="资金流出风险", message=capital_factor.description))

    profitability_factor = next((f for f in factors if f.key == 'profitability'), None)
    if profitability_factor and profitability_factor.value < 35:
        alerts.append(AlertItem(level="high", title="盈利能力风险", message=profitability_factor.description))

    if history and len(history) >= 10:
        recent_closes = [h.close for h in history[-10:]]
        price_change = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] * 100 if recent_closes[0] > 0 else 0
        if price_change < -15:
            alerts.append(AlertItem(level="high", title="价格下跌风险", message=f"近10日累计下跌{abs(price_change):.1f}%。"))
        elif price_change > 20:
            alerts.append(AlertItem(level="medium", title="短期涨幅过大", message=f"近10日累计上涨{price_change:.1f}%。"))

    if alerts:
        db.query(AlertItemDB).filter(AlertItemDB.stock_code == stock.code).delete()
        for alert in alerts:
            db.add(AlertItemDB(stock_code=stock.code, level=alert.level, title=alert.title, message=alert.message))
        db.commit()
        logger.info(f"Updated risk alerts for stock: {stock.code}")

    return alerts


def ensure_ai_summary(db: Session, stock: Stock, history: list, factors: list, alerts: list) -> str:
    """基于真实数据生成AI摘要"""
    summary_parts = []

    avg_score = sum(f.value for f in factors) / len(factors) if factors else 50
    if avg_score >= 70:
        summary_parts.append("综合分析显示，该股票基本面强劲，各项指标表现优秀。")
    elif avg_score >= 55:
        summary_parts.append("综合分析显示，该股票基本面稳健，多数指标表现良好。")
    elif avg_score >= 40:
        summary_parts.append("综合分析显示，该股票基本面一般，部分指标需要关注。")
    else:
        summary_parts.append("综合分析显示，该股票基本面较弱，多项指标表现不佳。")

    for factor in factors:
        if factor.value >= 70:
            summary_parts.append(f"{factor.label}方面表现优秀：{factor.description}")
        elif factor.value <= 35:
            summary_parts.append(f"{factor.label}方面需要关注：{factor.description}")

    if alerts:
        high_alerts = [a for a in alerts if a.level == 'high']
        medium_alerts = [a for a in alerts if a.level == 'medium']
        if high_alerts:
            summary_parts.append(f"高风险提示：{'; '.join([a.title for a in high_alerts])}。")
        if medium_alerts:
            summary_parts.append(f"中等风险提示：{'; '.join([a.title for a in medium_alerts])}。")

    if avg_score >= 70 and not alerts:
        summary_parts.append("建议积极关注，可考虑逢低布局。")
    elif avg_score >= 55 and len(alerts) <= 1:
        summary_parts.append("建议持仓观望，适当控制仓位。")
    elif avg_score < 40 or len([a for a in alerts if a.level == 'high']) >= 2:
        summary_parts.append("建议谨慎观望，等待基本面改善。")
    else:
        summary_parts.append("建议适度关注，注意风险控制。")

    ai_summary = "。".join(summary_parts)
    stock.ai_summary = ai_summary
    db.commit()
    logger.info(f"Updated AI summary for stock: {stock.code}")

    return ai_summary

def calculate_factors(daily_data: list) -> list:
    """
    閺嶈宓侀崢鍡楀蕉閺佺増宓佺拋锛勭暬閸ョ姴鐡欑拠鍕瀻

    Args:
        daily_data: 閺冦儳鍤庨弫鐗堝祦閸掓銆冮敍鍫濆讲娴犮儲妲哥€涙鍚€閹存湢ricePointDB鐎电钖勯敍?

    Returns:
        閸ョ姴鐡欑拠鍕瀻閸掓銆?
    """
    if not daily_data or len(daily_data) < 5:
        return []

    # 閹稿妫╅張鐔稿笓鎼村骏绱欓弨顖涘瘮鐎涙鍚€閸滃苯顕挒鈽呯礆
    sorted_data = sorted(daily_data, key=lambda x: get_item_value(x, 'date') or get_item_value(x, 'trade_date', ''), reverse=True)

    # 鐠侊紕鐣绘禒閿嬬壐閸欐ê瀵?
    closes = [get_item_value(d, 'close', 0) for d in sorted_data[:30] if get_item_value(d, 'close')]
    if len(closes) < 5:
        closes = [get_item_value(d, 'close', 0) for d in sorted_data if get_item_value(d, 'close')]

    if not closes:
        return []

    # 鐠у嫰鍣惧ù浣告礈鐎涙劧绱欐担璺ㄦ暏閹存劒姘﹂柌蹇撳綁閸栨牗膩閹风噦绱?
    volumes = [get_item_value(d, 'volume', 0) for d in sorted_data[:20] if get_item_value(d, 'volume')]
    capital_flow_score = 50
    if len(volumes) >= 5:
        avg_vol = sum(volumes) / len(volumes)
        recent_vol = volumes[0] if volumes else 0
        if recent_vol > avg_vol * 1.2:
            capital_flow_score = 70
        elif recent_vol < avg_vol * 0.8:
            capital_flow_score = 35

    # 娴兼澘鈧厧娲滅€涙劧绱欐担璺ㄦ暏娴犻攱鐗哥搾瀣◢濡剝瀚欓敍?
    valuation_score = 50
    if len(closes) >= 10:
        price_change = (closes[0] - closes[-1]) / closes[-1] * 100 if closes[-1] > 0 else 0
        if price_change > 20:
            valuation_score = 75
        elif price_change > 10:
            valuation_score = 65
        elif price_change < -20:
            valuation_score = 30
        elif price_change < -10:
            valuation_score = 40

    # 閸斻劑鍣洪崶鐘茬摍
    momentum_score = 50
    if len(closes) >= 5:
        ma5 = sum(closes[:5]) / 5
        ma20 = sum(closes[:20]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)
        if closes[0] > ma5 > ma20:
            momentum_score = 70
        elif closes[0] < ma5 < ma20:
            momentum_score = 35

    # 濞夈垹濮╅幀褍娲滅€?
    volatility_score = 50
    if len(closes) >= 10:
        changes = [(closes[i] - closes[i+1]) / closes[i+1] * 100 for i in range(len(closes)-1) if closes[i+1] > 0]
        if changes:
            avg_change = sum(abs(c) for c in changes) / len(changes)
            if avg_change > 3:
                volatility_score = 70
            elif avg_change < 1.5:
                volatility_score = 35

    return [
        {"key": "capital_flow", "label": "Capital Flow", "value": capital_flow_score,
         "description": "Strong capital inflow detected." if capital_flow_score > 60 else "Mixed capital flow." if capital_flow_score > 40 else "Capital outflow detected."},
        {"key": "valuation", "label": "Valuation", "value": valuation_score,
         "description": "Strong upward momentum." if valuation_score > 65 else "Reasonable valuation." if valuation_score > 45 else "Below average valuation."},
        {"key": "momentum", "label": "Momentum", "value": momentum_score,
         "description": "Strong momentum." if momentum_score > 60 else "Weak momentum." if momentum_score > 40 else "Negative momentum."},
        {"key": "volatility", "label": "Volatility", "value": volatility_score,
         "description": "High volatility." if volatility_score > 60 else "Moderate volatility." if volatility_score > 40 else "Low volatility."},
    ]
