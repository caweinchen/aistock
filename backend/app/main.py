from datetime import datetime, timezone, timedelta
from typing import Literal
import logging

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Application logger.
logger = logging.getLogger("stocks")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import init_db, get_db, init_sample_data, AuthSession, User, WatchlistItem, Stock, FactorScoreDB, StrategyResultDB, PricePointDB, AlertItemDB
from app.security import generate_auth_token, hash_password, hash_token, is_password_hash, verify_password, validate_password_strength
from app.tushare_service import init_tushare, get_tushare_service
from app.eastmoney_service import init_eastmoney, get_eastmoney_service
from app.config import tushare_config
from app.backtest_engine import BacktestResult, build_strategy_summaries, run_backtest
from app.rsa_utils import get_rsa_utils

Signal = Literal["neutral", "buy", "sell"]
RiskLevel = Literal["low", "medium", "high"]
TradeAction = Literal["buy", "sell"]
StrategyTemplate = Literal["trend-breakout", "low-valuation-reversal", "dividend-defense"]


# 认证依赖
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """验证token并返回当前用户"""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_hash = hash_token(token)
    session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash).first()
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # 处理时区问题
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Token expired")
    
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


class StockSummary(BaseModel):
    code: str
    name: str
    price: float
    change_percent: float
    score: int = Field(ge=0, le=100)
    signal: Signal


class FactorScore(BaseModel):
    key: str
    label: str
    value: int = Field(ge=0, le=100)
    description: str


class StrategyResult(BaseModel):
    id: str
    name: str
    period: str
    return_rate: float
    max_drawdown: float
    win_rate: float
    risk: RiskLevel
    summary: str


class BacktestTrade(BaseModel):
    date: str
    action: TradeAction
    price: float
    quantity: int
    reason: str


class StrategyDetail(BaseModel):
    strategy: StrategyResult
    annualized_return: float
    sharpe_ratio: float
    trade_count: int
    rules: list[str]
    trades: list[BacktestTrade]


class BacktestRequest(BaseModel):
    code: str
    name: str = "Custom Strategy"
    template: StrategyTemplate = "trend-breakout"
    lookback_days: int = Field(default=180, ge=30, le=720)
    risk: RiskLevel = "medium"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


class PasswordStrengthResponse(BaseModel):
    valid: bool
    score: int
    messages: list[str]


class AlertItem(BaseModel):
    level: RiskLevel
    title: str
    message: str


class PricePoint(BaseModel):
    date: str
    close: float
    volume: int


class StockDetail(BaseModel):
    stock: StockSummary
    factors: list[FactorScore]
    strategies: list[StrategyResult]
    alerts: list[AlertItem]
    history: list[PricePoint]
    ai_summary: str | None = None
    data_status: str
    updated_at: datetime | None = None


app = FastAPI(
    title="AIStock API",
    version="0.1.0",
    description="Backend API for AIStock mobile stock selection and detail panels.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database and data-source initialization.
@app.on_event("startup")
def on_startup():
    init_db()
    db = next(get_db())
    init_sample_data(db)

    # Initialize EastMoney realtime data service.
    init_eastmoney()
    print("EastMoney data service enabled")

    # Keep TuShare cache files inside the backend directory.
    import os
    os.environ['TUSHARE_DATA_DIR'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Initialize TuShare when configured.
    if tushare_config.token:
        init_tushare(tushare_config.token)
        print(f"TuShare Pro enabled, Token: {tushare_config.token[:10]}...")
    elif tushare_config.enabled:
        init_tushare()
        print("TuShare free mode enabled")


def stock_to_summary(stock: Stock) -> StockSummary:
    return StockSummary(
        code=stock.code,
        name=stock.name,
        price=stock.price or 0,
        change_percent=stock.change_percent or 0,
        score=stock.score or 50,
        signal=stock.signal or "neutral",
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


def _history_needs_refresh(history: list[PricePointDB]) -> bool:
    if not history:
        return True
    latest = max(history, key=lambda price: price.date)
    try:
        latest_date = datetime.strptime(latest.date, "%Y-%m-%d").date()
    except ValueError:
        return True
    return (datetime.now().date() - latest_date).days > 1


def ensure_price_history(db: Session, stock: Stock) -> list[PricePointDB]:
    history = get_price_history(db, stock.code)
    if not _history_needs_refresh(history) or not tushare_config.enabled:
        return history

    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=720)).strftime("%Y%m%d")
        daily_data = get_tushare_service().get_daily_price(_stock_ts_code(stock), start_date, end_date)
        if not daily_data:
            return history

        db.query(PricePointDB).filter(PricePointDB.stock_code == stock.code).delete()
        for item in daily_data:
            date = _format_tushare_date(_item_value(item, "date") or _item_value(item, "trade_date"))
            close = float(_item_value(item, "close", 0) or 0)
            if not date or close <= 0:
                continue
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
        db.commit()
    except Exception:
        db.rollback()
        return history

    return sorted(get_price_history(db, stock.code), key=lambda price: price.date)


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
        # 閸欘亝婀侀崷銊︽暪閻╂ê鎮楅敍?5:00娑斿鎮楅敍澶夌瑬娴犲﹤銇夊鍙夋纯閺傛媽绻冮敍灞惧鐠哄疇绻?
        if last_update_date == today and current_hour >= market_close_hour:
            need_update_realtime = False
            logger.info(f"瀹稿弶鏁归惄妯圭瑬鐎圭偞妞傜悰灞惧剰瀹稿弶妲告禒濠冩）閺佺増宓侀敍宀冪儲鏉╁洦娲块弬? {code}")
        elif last_update_date == today and current_hour < market_close_hour:
            logger.info(f"娴溿倖妲楅弮鍫曟？閸愬拑绱濋棁鈧憰浣规纯閺傛澘鐤勯弮鎯邦攽閹? {code}")

    if need_update_realtime:
        try:
            eastmoney = get_eastmoney_service()
            quotes = eastmoney.get_realtime_quote([code])
            if quotes:
                quote = quotes[0]
                stock.price = quote.get('price', stock.price or 0)
                stock.change_percent = quote.get('change_percent', stock.change_percent or 0)
                stock.updated_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"閺囧瓨鏌婄€圭偞妞傜悰灞惧剰: {code} - {stock.name}")
        except Exception as e:
            logger.error(f"閺囧瓨鏌婄€圭偞妞傜悰灞惧剰婢惰精瑙?{code}: {e}")
            db.rollback()

    # 获取历史价格数据
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

    return StockDetail(
        stock=stock_to_summary(stock),
        factors=[db_factor_to_model(f) for f in factors],
        strategies=strategy_models,
        alerts=[db_alert_to_model(a) for a in alerts],
        history=[db_price_to_model(h) for h in history],
        # 基于真实数据生成AI摘要
        ai_summary=ensure_ai_summary(db, stock, history, factors, alerts),
        data_status=stock.data_status,
        updated_at=stock.updated_at,
    )


def get_watchlist_user(db: Session, username: str = "admin") -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user

    user = User(username=username, password=hash_password("admin123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/api/stocks", response_model=list[StockSummary])
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


@app.get("/api/stocks/refresh-all", response_model=list[StockSummary])
def refresh_all_stocks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """批量刷新当前用户所有自选股的实时数据并保存到数据库"""
    logger.info(f"Starting batch refresh for user [{user.username}]")
    
    try:
        # 获取用户的自选股代码
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

        # 返回用户自选股列表
        updated_stocks = db.query(Stock).filter(Stock.code.in_(codes)).all()
        return [stock_to_summary(s) for s in updated_stocks]
        
    except Exception as e:
        logger.error(f"Batch refresh failed for user [{user.username}]: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Batch refresh failed: {str(e)}")


@app.get("/api/stocks/search", response_model=list[StockSummary])
def search_stocks(q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """搜索股票（公共数据，所有用户共用）"""
    keyword = q.strip()
    if not keyword:
        # 无搜索关键词时返回用户自选股
        return get_stocks(db, user)

    logger.info(f"閹兼粎鍌ㄩ懖锛勩偍: {keyword}")

    # 1. 娴兼ê鍘涙禒搴㈡殶閹诡喖绨遍幖婊呭偍閿涘牊鏁幐浣疯厬閼昏鲸鏋冮崥宥囆為敍?
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
        logger.error(f"閺佺増宓佹惔鎾存偝缁便垹銇戠拹?'{keyword}': {e}")

    # 2. 閺佺増宓佹惔鎾寸梾閺堝绱濇禒搴濈閺傜鍌ㄧ€靛本鎮崇槐銏犵杽閺冭埖鏆熼幑?
    eastmoney = get_eastmoney_service()
    search_results = eastmoney.search_stocks(keyword)

    if search_results:
        summaries = []
        for r in search_results:
            code = r.get('code', '')
            name = r.get('name', '')
            ts_code = r.get('ts_code', '')
            market = r.get('market', '')

            # 閼奉亜濮╂穱婵嗙摠閸掔増鏆熼幑顔肩氨
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
                    logger.info(f"閼奉亜濮╂穱婵嗙摠閼诧紕銈ㄩ崚鐗堟殶閹诡喖绨? {code} - {name}")
            except Exception as e:
                logger.error(f"娣囨繂鐡ㄩ懖锛勩偍婢惰精瑙?{code}: {e}")
                db.rollback()

            # 閼惧嘲褰囩€圭偞妞傜悰灞惧剰
            try:
                quotes = eastmoney.get_realtime_quote([code])
                if quotes:
                    quote = quotes[0]
                    summaries.append(StockSummary(
                        code=code,
                        name=name,
                        price=quote.get('price', 0),
                        change_percent=quote.get('change_percent', 0),
                        score=50,  # 姒涙顓荤拠鍕瀻
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
                logger.error(f"閼惧嘲褰囩€圭偞妞傜悰灞惧剰婢惰精瑙?{code}: {e}")
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

    logger.warning(f"閹兼粎鍌ㄩ弮鐘电波閺? {keyword}")
    return []


@app.get("/api/stocks/{code}", response_model=StockDetail)
def get_stock_detail_api(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logger.info(f"閼惧嘲褰囬懖锛勩偍鐠囷附鍎? {code}")

    # 濡偓閺屻儲鏆熼幑顔肩氨娑擃厽妲搁崥锕€鐡ㄩ崷?
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        logger.info(f"閼诧紕銈ㄦ稉宥呮躬閺佺増宓佹惔鎾茶厬閿涘苯鐨剧拠鏇氱矤娑撴粍鏌熺拹銏犵槣閼惧嘲褰? {code}")
        # 娴犲簼绗㈤弬纭呭偍鐎靛矁骞忛崣鏍ц嫙娣囨繂鐡ㄩ崚鐗堟殶閹诡喖绨?
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
                logger.info(f"娴犲簼绗㈤弬纭呭偍鐎靛矁骞忛崣鏍ц嫙娣囨繂鐡ㄩ懖锛勩偍: {code} - {stock.name}")
            else:
                logger.error(f"閺冪姵纭堕懢宄板絿閼诧紕銈ㄦ穱鈩冧紖: {code}")
                raise HTTPException(status_code=404, detail="Stock not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"閼惧嘲褰囬懖锛勩偍鐠囷附鍎忔径杈Е {code}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get stock detail")

    return get_stock_detail(db, code)


@app.get("/api/stocks/{code}/strategies", response_model=list[StrategyResult])
def get_stock_strategies(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_stock_detail(db, code).strategies


@app.get("/api/stocks/{code}/strategies/{strategy_id}", response_model=StrategyDetail)
def get_stock_strategy_detail(code: str, strategy_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    detail = get_stock_detail(db, code)
    for strategy in detail.strategies:
        if strategy.id == strategy_id:
            return build_strategy_detail(detail, strategy)
    raise HTTPException(status_code=404, detail="Strategy not found")


@app.get("/api/stocks/{code}/history", response_model=list[PricePoint])
def get_stock_history(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    history = get_price_history(db, code)
    return [db_price_to_model(h) for h in history]


@app.get("/api/stocks/{code}/realtime")
def get_stock_realtime(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """閼惧嘲褰囬懖锛勩偍鐎圭偞妞傜悰灞惧剰"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()
    quote = tushare_svc.get_realtime_quote(code)

    if not quote:
        raise HTTPException(status_code=404, detail="Failed to get realtime quote")

    return quote


@app.get("/api/stocks/{code}/dividend")
def get_stock_dividend(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取股票分红记录"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    dividend = tushare_svc.get_dividend(stock.ts_code)
    return dividend


@app.get("/api/stocks/{code}/news")
def get_stock_news(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取股票重大事件/新闻"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    news = tushare_svc.get_stock_news(stock.ts_code)
    return news


@app.get("/api/stocks/{code}/adj-factor")
def get_stock_adj_factor(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取股票除权除息信息"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    adj_factor = tushare_svc.get_adj_factor(stock.ts_code)
    return adj_factor


@app.get("/api/stocks/{code}/inst-hold")
def get_stock_inst_hold(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取机构持仓数据（按时间倒序）"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    inst_hold = tushare_svc.get_inst_hold(stock.ts_code)
    return inst_hold


@app.get("/api/stocks/{code}/refresh")
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


@app.get("/api/tushare/status")
def get_tushare_status():
    """Return TuShare connection status."""
    return {
        "enabled": tushare_config.enabled,
        "has_token": bool(tushare_config.token),
        "status": "connected" if tushare_config.enabled else "disabled"
    }


@app.get("/api/eastmoney/status")
def get_eastmoney_status():
    """Return EastMoney service status."""
    return {
        "enabled": True,
        "status": "connected"
    }


@app.get("/api/eastmoney/refresh/{code}")
def refresh_stock_from_eastmoney(code: str, db: Session = Depends(get_db)):
    """Refresh realtime stock data from EastMoney."""
    eastmoney = get_eastmoney_service()
    quotes = eastmoney.get_realtime_quote([code])

    if not quotes:
        raise HTTPException(status_code=404, detail="Failed to get quote from EastMoney")

    quote = quotes[0]

    # 閺囧瓨鏌婇弫鐗堝祦鎼存挷鑵戦惃鍕亗缁併劋淇婇幁?
    stock = db.query(Stock).filter(Stock.code == code).first()
    if stock:
        stock.price = quote.get('price', stock.price)
        stock.change_percent = quote.get('change_percent', stock.change_percent)
        stock.updated_at = datetime.now(timezone.utc)
        db.commit()

    return {
        "success": True,
        "code": code,
        "name": quote.get('name'),
        "price": quote.get('price'),
        "change_percent": quote.get('change_percent')
    }


@app.get("/api/stocks/{code}/factors", response_model=list[FactorScore])
def get_stock_factors(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 从TuShare获取财务数据并计算因子评分
    factors = ensure_factor_scores(db, stock, history)
    return [db_factor_to_model(f) for f in factors]


@app.get("/api/stocks/{code}/alerts", response_model=list[AlertItem])
def get_stock_alerts(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 基于真实数据生成风险预警
    alerts = ensure_alerts(db, stock, history, factors)
    return [db_alert_to_model(a) for a in alerts]


@app.post("/api/backtests", response_model=StrategyDetail)
def create_backtest(request: BacktestRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> StrategyDetail:
    detail = get_stock_detail(db, request.code)
    strategy_detail = build_custom_backtest(detail, request)

    # 娣囨繂鐡ㄩ崚鐗堟殶閹诡喖绨?
    strategy_db = StrategyResultDB(
        id=strategy_detail.strategy.id,
        stock_code=request.code,
        name=strategy_detail.strategy.name,
        period=strategy_detail.strategy.period,
        return_rate=strategy_detail.strategy.return_rate,
        max_drawdown=strategy_detail.strategy.max_drawdown,
        win_rate=strategy_detail.strategy.win_rate,
        risk=strategy_detail.strategy.risk,
        summary=strategy_detail.strategy.summary,
    )
    db.add(strategy_db)
    db.commit()

    return strategy_detail


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


@app.get("/api/watchlist")
def get_watchlist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()
        logger.info(f"Loaded watchlist [{user.username}]: {len(items)} items")
        return {"codes": [item.stock_code for item in items]}
    except Exception as e:
        logger.error(f"閼惧嘲褰囬懛顏堚偓澶庡亗閸掓銆冩径杈Е [{user.username}]: {e}")
        raise HTTPException(status_code=500, detail="閼惧嘲褰囬懛顏堚偓澶庡亗閸掓銆冩径杈Е")


@app.post("/api/watchlist/{code}")
def add_to_watchlist(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logger.info(f"濞ｈ濮為懛顏堚偓澶庡亗 [{user.username}]: {code}")

    # 濡偓閺屻儴鍋傜粊銊︽Ц閸氾箑婀弫鐗堝祦鎼存挷鑵戦敍灞肩瑝閸︺劌鍨懛顏勫З娣囨繂鐡?
    try:
        stock = db.query(Stock).filter(Stock.code == code).first()
        if not stock:
            # 娴犲孩鏆熼幑顔界爱閼惧嘲褰囬懖锛勩偍娣団剝浼呴獮鏈电箽鐎涙ê鍩岄弫鐗堝祦鎼?
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
                logger.info(f"閼奉亜濮╂穱婵嗙摠閼诧紕銈ㄦ穱鈩冧紖: {code} - {stock.name}")
            else:
                logger.error(f"閼惧嘲褰囬懖锛勩偍娣団剝浼呮径杈Е: {code}")
                raise HTTPException(status_code=404, detail="Stock not found")

        existing_item = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == user.id,
            WatchlistItem.stock_code == code,
        ).first()
        if not existing_item:
            db.add(WatchlistItem(user_id=user.id, stock_code=code))
            db.commit()
            logger.info(f"濞ｈ濮為懛顏堚偓澶庡亗閹存劕濮?[{user.username}]: {code}")

        codes = [item.stock_code for item in db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()]
        stocks = db.query(Stock).filter(Stock.code.in_(codes)).all() if codes else []
        return [stock_to_summary(s) for s in stocks]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"濞ｈ濮為懛顏堚偓澶庡亗婢惰精瑙?[{user.username}] {code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add to watchlist")


@app.delete("/api/watchlist/{code}")
def remove_from_watchlist(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logger.info(f"閸掔娀娅庨懛顏堚偓澶庡亗 [{user.username}]: {code}")

    try:
        stock = db.query(Stock).filter(Stock.code == code).first()
        if not stock:
            logger.error(f"閼诧紕銈ㄦ稉宥呯摠閸? {code}")
            raise HTTPException(status_code=404, detail="Stock not found")

        item = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == user.id,
            WatchlistItem.stock_code == code,
        ).first()
        if item:
            db.delete(item)
            db.commit()
            logger.info(f"閸掔娀娅庨懛顏堚偓澶庡亗閹存劕濮?[{user.username}]: {code}")

        codes = [item.stock_code for item in db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()]
        stocks = db.query(Stock).filter(Stock.code.in_(codes)).all() if codes else []
        return [stock_to_summary(s) for s in stocks]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"閸掔娀娅庨懛顏堚偓澶庡亗婢惰精瑙?[{user.username}] {code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove from watchlist")


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}


@app.get("/api/auth/public-key")
def get_public_key():
    """Get RSA public key for password encryption."""
    rsa_utils = get_rsa_utils()
    return {"public_key": rsa_utils.get_public_key()}


def decrypt_password(encrypted_password: str | None) -> str:
    """Decrypt password if it's encrypted, otherwise return as-is for backward compatibility."""
    if not encrypted_password:
        return ""
    
    if encrypted_password.startswith('encrypted:'):
        try:
            rsa_utils = get_rsa_utils()
            return rsa_utils.decrypt_base64(encrypted_password[10:])
        except Exception as e:
            logger.error(f"Failed to decrypt password: {e}")
            raise HTTPException(status_code=400, detail="Invalid encrypted password")
    
    return encrypted_password


@app.post("/api/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """User login endpoint. Supports both encrypted and plain password for backward compatibility."""
    logger.info(f"Login attempt for username: {request.username}")
    
    try:
        password = decrypt_password(request.password)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password decryption error: {e}")
        raise HTTPException(status_code=400, detail="Invalid password format")

    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        logger.info(f"User {request.username} not found, attempting auto-create")
        # Auto-create user if not exists (for demo purposes)
        if request.username == "admin" and password == "Test@bcd!234":
            user = User(username=request.username, password=hash_password(password))
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"User {request.username} created successfully")
        else:
            logger.warning(f"Failed to auto-create user {request.username}: invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid username or password")

    logger.info(f"User found: {user.username}, verifying password...")
    if not verify_password(password, user.password):
        logger.warning(f"Password verification failed for user {request.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not is_password_hash(user.password):
        user.password = hash_password(password)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()

    token = generate_auth_token()
    db.add(AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    ))
    db.commit()
    logger.info(f"Login successful for user {request.username}")

    return LoginResponse(token=token, username=user.username)


@app.post("/api/auth/change-password")
def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db)):
    """Change password endpoint. Supports encrypted passwords."""
    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        old_password = decrypt_password(request.old_password)
        new_password = decrypt_password(request.new_password)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password decryption error: {e}")
        raise HTTPException(status_code=400, detail="Invalid password format")

    if not verify_password(old_password, user.password):
        raise HTTPException(status_code=401, detail="Old password is incorrect")

    strength = validate_password_strength(new_password)
    if not strength["valid"]:
        raise HTTPException(status_code=400, detail=strength["messages"])

    user.password = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "message": "Password changed successfully"}


@app.post("/api/auth/validate-password", response_model=PasswordStrengthResponse)
def check_password_strength(password: str):
    """妤犲矁鐦夌€靛棛鐖滃鍝勫€"""
    return validate_password_strength(password)


@app.get("/api/auth/verify")
def verify_token(user: User = Depends(get_current_user)):
    """Verify token is valid and get user info."""
    return {"valid": True, "username": user.username, "user_id": user.id}


@app.get("/api/auth/generate-password")
def generate_strong_password():
    """Generate a strong random password."""
    import random
    import string

    lowercase = random.choice(string.ascii_lowercase)
    uppercase = random.choice(string.ascii_uppercase)
    digit = random.choice(string.digits)
    special = random.choice("!@#$%^&*")

    remaining_chars = random.choices(
        string.ascii_letters + string.digits + "!@#$%^&*",
        k=4
    )

    password_list = list(lowercase + uppercase + digit + special + ''.join(remaining_chars))
    random.shuffle(password_list)
    password = ''.join(password_list)

    return {"password": password, "length": len(password)}


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
                logger.info(f"因子评分更新成功: {stock.code}")
                return factors
    except Exception as e:
        logger.error(f"获取财务数据失败: {stock.code}: {e}")
        db.rollback()

    if not factors and history:
        factors = calculate_factors(history)
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
        logger.info(f"风险预警更新成功: {stock.code}")

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
    logger.info(f"AI摘要更新成功: {stock.code}")

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
