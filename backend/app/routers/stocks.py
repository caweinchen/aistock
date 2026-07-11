from datetime import datetime, timezone
import logging
import re

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
from app.routers.auth import get_current_user
from app.schemas import (
    AlertItem,
    BacktestRequest,
    BacktestTrade,
    FactorScore,
    PricePoint,
    StockDetail,
    StockSummary,
    StrategyDetail,
    StrategyResult,
)
from app.security import hash_password
from app.stock_summary import (
    stock_to_summary,
)
from app.tushare_service import get_tushare_service, init_tushare
from app.stock_detail_assembler import StockDetailOperations, assemble_stock_detail
from app.stock_data_service import (
    StockDataOperations,
    ensure_price_history as service_ensure_price_history,
    get_price_history as service_get_price_history,
    history_needs_refresh as service_history_needs_refresh,
    is_morning_break_time as service_is_morning_break_time,
    is_trading_time as service_is_trading_time,
    last_market_session_end_time as service_last_market_session_end_time,
    update_stock_realtime_quote as service_update_stock_realtime_quote,
)
from app.stock_analysis_service import (
    AnalysisOperations,
    ensure_ai_summary as service_ensure_ai_summary,
    ensure_alerts as service_ensure_alerts,
    ensure_factor_scores as service_ensure_factor_scores,
)

logger = logging.getLogger("stocks")
router = APIRouter(prefix="/api/stocks")

def update_stock_realtime_quote(db: Session, stock: Stock) -> None:
    return service_update_stock_realtime_quote(
        db,
        stock,
        StockDataOperations(get_realtime_quotes=get_eastmoney_service().get_realtime_quote),
    )


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
    return service_get_price_history(db, code)


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
    return service_is_trading_time()

def _is_morning_break_time() -> bool:
    return service_is_morning_break_time()

def _last_market_session_end_time() -> datetime:
    return service_last_market_session_end_time(morning_break_time=_is_morning_break_time)

def _history_needs_refresh(history: list[PricePointDB], stock: Stock) -> bool:
    return service_history_needs_refresh(
        history,
        stock,
        is_trading_time=_is_trading_time,
        last_market_session_end_time=_last_market_session_end_time,
    )


def ensure_price_history(db: Session, stock: Stock) -> list[PricePointDB]:
    return service_ensure_price_history(
        db,
        stock,
        StockDataOperations(get_tushare_service=get_initialized_tushare_service),
        needs_refresh=_history_needs_refresh,
    )


def parse_custom_strategy_id(strategy_id: str) -> tuple[str, int] | None:
    if not strategy_id.startswith("custom-"):
        return None

    try:
        template, lookback_days, _timestamp = strategy_id[len("custom-") :].rsplit("-", 2)
        return template, int(lookback_days)
    except (TypeError, ValueError):
        return None


def get_stock_detail(db: Session, code: str, update_realtime: bool = True) -> StockDetail:
    return assemble_stock_detail(
        db,
        code,
        update_realtime,
        StockDetailOperations(
            update_realtime_quote=update_stock_realtime_quote,
            ensure_price_history=ensure_price_history,
            ensure_factor_scores=ensure_factor_scores,
            ensure_alerts=ensure_alerts,
            calculate_strategies=calculate_strategies,
            strategy_to_model=db_strategy_to_model,
            factor_to_model=db_factor_to_model,
            alert_to_model=db_alert_to_model,
            price_to_model=db_price_to_model,
            ensure_ai_summary=ensure_ai_summary,
        ),
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
    return service_ensure_factor_scores(
        db,
        stock,
        history,
        AnalysisOperations(
            get_tushare_service=get_tushare_service,
            calculate_financial_factors=calculate_factors_from_financial,
            calculate_local_factors=calculate_factors,
            factor_to_model=db_factor_to_model,
            item_value=_item_value,
            stock_ts_code=_stock_ts_code,
        ),
    )


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
    return service_ensure_alerts(db, stock, history, factors)


def ensure_ai_summary(db: Session, stock: Stock, history: list, factors: list, alerts: list) -> str:
    return service_ensure_ai_summary(db, stock, history, factors, alerts)


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
