from datetime import datetime, timezone, timedelta
from typing import Literal

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import init_db, get_db, init_sample_data, AuthSession, User, WatchlistItem, Stock, FactorScoreDB, StrategyResultDB, PricePointDB, AlertItemDB
from backend.app.security import generate_auth_token, hash_password, hash_token, is_password_hash, verify_password
from backend.app.tushare_service import init_tushare, get_tushare_service
from backend.app.config import tushare_config
from backend.app.backtest_engine import BacktestResult, build_strategy_summaries, run_backtest

Signal = Literal["neutral", "buy", "sell"]
RiskLevel = Literal["low", "medium", "high"]
TradeAction = Literal["buy", "sell"]
StrategyTemplate = Literal["trend-breakout", "low-valuation-reversal", "dividend-defense"]


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
    ai_summary: str
    data_status: str
    updated_at: datetime


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


# 数据库初始化
@app.on_event("startup")
def on_startup():
    init_db()
    db = next(get_db())
    init_sample_data(db)

    # 初始化 TuShare 服务
    if tushare_config.token:
        init_tushare(tushare_config.token)
        print(f"TuShare Pro 已启用，Token: {tushare_config.token[:10]}...")
    elif tushare_config.enabled:
        init_tushare()
        print("TuShare 免费版已启用")


def stock_to_summary(stock: Stock) -> StockSummary:
    return StockSummary(
        code=stock.code,
        name=stock.name,
        price=stock.price,
        change_percent=stock.change_percent,
        score=stock.score,
        signal=stock.signal,
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


def get_stock_detail(db: Session, code: str) -> StockDetail:
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    factors = db.query(FactorScoreDB).filter(FactorScoreDB.stock_code == code).all()
    history = db.query(PricePointDB).filter(PricePointDB.stock_code == code).all()
    alerts = db.query(AlertItemDB).filter(AlertItemDB.stock_code == code).all()
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
        ai_summary=stock.ai_summary,
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
def get_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).all()
    return [stock_to_summary(s) for s in stocks]


@app.get("/api/stocks/search", response_model=list[StockSummary])
def search_stocks(q: str = "", db: Session = Depends(get_db)):
    keyword = q.strip().lower()
    if not keyword:
        return get_stocks(db)

    # 优先从 TuShare 搜索
    if tushare_config.enabled:
        tushare_svc = get_tushare_service()
        results = tushare_svc.search_stocks(keyword)
        if results:
            summaries = []
            for r in results:
                # 从数据库查找完整数据
                stock = db.query(Stock).filter(Stock.code == r.get('ts_code', r.get('code'))).first()
                if stock:
                    summaries.append(stock_to_summary(stock))
                else:
                    # 创建临时摘要
                    summaries.append(StockSummary(
                        code=r.get('ts_code', r.get('code', '')),
                        name=r.get('name', ''),
                        price=0.0,
                        change_percent=0.0,
                        score=50,
                        signal="neutral"
                    ))
            return summaries

    stocks = db.query(Stock).filter(
        (Stock.code.ilike(f"%{keyword}%")) | (Stock.name.ilike(f"%{keyword}%"))
    ).all()
    return [stock_to_summary(s) for s in stocks]


@app.get("/api/stocks/{code}", response_model=StockDetail)
def get_stock_detail_api(code: str, db: Session = Depends(get_db)):
    return get_stock_detail(db, code)


@app.get("/api/stocks/{code}/strategies", response_model=list[StrategyResult])
def get_stock_strategies(code: str, db: Session = Depends(get_db)):
    history = db.query(PricePointDB).filter(PricePointDB.stock_code == code).all()
    custom_strategies = db.query(StrategyResultDB).filter(
        StrategyResultDB.stock_code == code,
        StrategyResultDB.id.like("custom-%"),
    ).all()
    return [
        StrategyResult(**strategy)
        for strategy in calculate_strategies(history)
    ] + [db_strategy_to_model(strategy) for strategy in custom_strategies]


@app.get("/api/stocks/{code}/strategies/{strategy_id}", response_model=StrategyDetail)
def get_stock_strategy_detail(code: str, strategy_id: str, db: Session = Depends(get_db)):
    detail = get_stock_detail(db, code)
    for strategy in detail.strategies:
        if strategy.id == strategy_id:
            return build_strategy_detail(detail, strategy)
    raise HTTPException(status_code=404, detail="Strategy not found")


@app.get("/api/stocks/{code}/history", response_model=list[PricePoint])
def get_stock_history(code: str, db: Session = Depends(get_db)):
    history = db.query(PricePointDB).filter(PricePointDB.stock_code == code).all()
    return [db_price_to_model(h) for h in history]


@app.get("/api/stocks/{code}/realtime")
def get_stock_realtime(code: str, db: Session = Depends(get_db)):
    """获取股票实时行情"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()
    quote = tushare_svc.get_realtime_quote(code)

    if not quote:
        raise HTTPException(status_code=404, detail="Failed to get realtime quote")

    return quote


@app.get("/api/stocks/{code}/refresh")
def refresh_stock_data(code: str, db: Session = Depends(get_db)):
    """从 TuShare 刷新股票数据"""
    if not tushare_config.enabled:
        raise HTTPException(status_code=503, detail="TuShare is not enabled")

    tushare_svc = get_tushare_service()

    # 获取实时行情
    quote = tushare_svc.get_realtime_quote(code)
    if not quote:
        raise HTTPException(status_code=404, detail="Failed to get realtime quote")

    # 更新数据库中的股票信息
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
    """获取 TuShare 连接状态"""
    return {
        "enabled": tushare_config.enabled,
        "has_token": bool(tushare_config.token),
        "status": "connected" if tushare_config.enabled else "disabled"
    }


@app.get("/api/stocks/{code}/factors", response_model=list[FactorScore])
def get_stock_factors(code: str, db: Session = Depends(get_db)):
    factors = db.query(FactorScoreDB).filter(FactorScoreDB.stock_code == code).all()
    return [db_factor_to_model(f) for f in factors]


@app.get("/api/stocks/{code}/alerts", response_model=list[AlertItem])
def get_stock_alerts(code: str, db: Session = Depends(get_db)):
    alerts = db.query(AlertItemDB).filter(AlertItemDB.stock_code == code).all()
    return [db_alert_to_model(a) for a in alerts]


@app.post("/api/backtests", response_model=StrategyDetail)
def create_backtest(request: BacktestRequest, db: Session = Depends(get_db)) -> StrategyDetail:
    detail = get_stock_detail(db, request.code)
    strategy_detail = build_custom_backtest(detail, request)

    # 保存到数据库
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
    result = run_backtest(
        strategy.id,
        detail.history,
        name=strategy.name,
        risk=strategy.risk,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Insufficient price history for backtest")
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
def get_watchlist(username: str = "admin", db: Session = Depends(get_db)):
    user = get_watchlist_user(db, username)
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()
    return {"codes": [item.stock_code for item in items]}


@app.post("/api/watchlist/{code}")
def add_to_watchlist(code: str, username: str = "admin", db: Session = Depends(get_db)):
    if not db.query(Stock).filter(Stock.code == code).first():
        raise HTTPException(status_code=404, detail="Stock not found")
    user = get_watchlist_user(db, username)
    existing_item = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user.id,
        WatchlistItem.stock_code == code,
    ).first()
    if not existing_item:
        db.add(WatchlistItem(user_id=user.id, stock_code=code))
        db.commit()
    codes = [item.stock_code for item in db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()]
    stocks = db.query(Stock).filter(Stock.code.in_(codes)).all() if codes else []
    return [stock_to_summary(s) for s in stocks]


@app.delete("/api/watchlist/{code}")
def remove_from_watchlist(code: str, username: str = "admin", db: Session = Depends(get_db)):
    if not db.query(Stock).filter(Stock.code == code).first():
        raise HTTPException(status_code=404, detail="Stock not found")
    user = get_watchlist_user(db, username)
    item = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user.id,
        WatchlistItem.stock_code == code,
    ).first()
    if item:
        db.delete(item)
        db.commit()
    codes = [item.stock_code for item in db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()]
    stocks = db.query(Stock).filter(Stock.code.in_(codes)).all() if codes else []
    return [stock_to_summary(s) for s in stocks]


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}


@app.post("/api/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """用户登录接口"""
    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not is_password_hash(user.password):
        user.password = hash_password(request.password)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()

    token = generate_auth_token()
    db.add(AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    ))
    db.commit()

    return LoginResponse(token=token, username=user.username)


@app.post("/api/auth/change-password")
def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db)):
    """修改密码接口"""
    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(request.old_password, user.password):
        raise HTTPException(status_code=401, detail="Old password is incorrect")

    strength = validate_password_strength(request.new_password)
    if not strength["valid"]:
        raise HTTPException(status_code=400, detail=strength["messages"])

    user.password = hash_password(request.new_password)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "message": "Password changed successfully"}


@app.post("/api/auth/validate-password", response_model=PasswordStrengthResponse)
def check_password_strength(password: str):
    """验证密码强度"""
    return validate_password_strength(password)


@app.get("/api/auth/generate-password")
def generate_strong_password():
    """生成随机强密码"""
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


def validate_password_strength(password: str) -> dict:
    """验证密码强度（强密码要求）"""
    messages = []
    score = 0

    if len(password) >= 8:
        score += 1
    else:
        messages.append("Password must be at least 8 characters long")

    if any(c.isupper() for c in password):
        score += 1
    else:
        messages.append("Password must contain at least one uppercase letter")

    if any(c.islower() for c in password):
        score += 1
    else:
        messages.append("Password must contain at least one lowercase letter")

    if any(c.isdigit() for c in password):
        score += 1
    else:
        messages.append("Password must contain at least one number")

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if any(c in special_chars for c in password):
        score += 1
    else:
        messages.append("Password must contain at least one special character (!@#$%^&* etc.)")

    return {
        "valid": score >= 5,
        "score": score,
        "messages": messages if messages else ["Password is strong"]
    }
