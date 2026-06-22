from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, ForeignKey, Text, UniqueConstraint, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
from backend.app.config import db_config
from backend.app.security import hash_password, is_password_hash, verify_password, validate_password_strength

engine = create_engine(db_config.url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

REQUIRED_SCHEMA_COLUMNS = {
    "stocks": {
        "english_name": "english_name VARCHAR(100) DEFAULT ''",
        "ts_code": "ts_code VARCHAR(20) DEFAULT ''",
        "market": "market VARCHAR(10) DEFAULT ''",
    },
    "price_history": {
        "open": "open FLOAT DEFAULT 0",
        "high": "high FLOAT DEFAULT 0",
        "low": "low FLOAT DEFAULT 0",
    },
}


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    watchlist = relationship("WatchlistItem", back_populates="user")


class WatchlistItem(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "stock_code", name="uq_watchlist_user_stock"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    stock_code = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="watchlist")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)


class Stock(Base):
    __tablename__ = "stocks"

    code = Column(String(20), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    english_name = Column(String(100), default="")
    ts_code = Column(String(20), default="")  # 通联数据格式: 000001.SZ
    market = Column(String(10), default="")   # SH/SZ
    price = Column(Float, nullable=False, default=0)
    change_percent = Column(Float, nullable=False, default=0)
    score = Column(Integer, nullable=False, default=50)
    signal = Column(String(20), nullable=False, default="neutral")
    ai_summary = Column(Text)
    data_status = Column(String(20), default="normal")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FactorScoreDB(Base):
    __tablename__ = "factor_scores"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), ForeignKey("stocks.code"))
    key = Column(String(50), nullable=False)
    label = Column(String(100), nullable=False)
    value = Column(Integer, nullable=False)
    description = Column(Text)


class StrategyResultDB(Base):
    __tablename__ = "strategies"

    id = Column(String(100), primary_key=True, index=True)
    stock_code = Column(String(20), ForeignKey("stocks.code"))
    name = Column(String(100), nullable=False)
    period = Column(String(50))
    return_rate = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    risk = Column(String(20))
    summary = Column(Text)


class PricePointDB(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), ForeignKey("stocks.code"))
    date = Column(String(20), nullable=False)
    open = Column(Float, default=0)
    high = Column(Float, default=0)
    low = Column(Float, default=0)
    close = Column(Float, nullable=False)
    volume = Column(Integer)


class AlertItemDB(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), ForeignKey("stocks.code"))
    level = Column(String(20), nullable=False)
    title = Column(String(100), nullable=False)
    message = Column(Text)


def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()


def _missing_columns(existing_columns: set[str], required_columns: dict[str, str]) -> dict[str, str]:
    return {
        column_name: ddl
        for column_name, ddl in required_columns.items()
        if column_name not in existing_columns
    }


def ensure_schema_columns():
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, required_columns in REQUIRED_SCHEMA_COLUMNS.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for ddl in _missing_columns(existing_columns, required_columns).values():
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_sample_data(db):
    from datetime import datetime, timezone

    stocks_data = {
        "600519": {
            "name": "贵州茅台",
            "english_name": "Kweichow Moutai",
            "price": 1563.0,
            "change_percent": 1.28,
            "score": 82,
            "signal": "buy",
            "ai_summary": "综合分析显示，该股票基本面强劲，资金流向健康，估值适中。建议持仓观望，适当控制仓位。",
            "data_status": "normal",
            "factors": [
                {"key": "capital_flow", "label": "资金流向", "value": 72, "description": "近5日主力资金净流入。"},
                {"key": "valuation", "label": "估值水平", "value": 64, "description": "估值处于行业中上水平。"},
                {"key": "momentum", "label": "动量指标", "value": 81, "description": "价格走势优于300只同类股票。"},
                {"key": "volatility", "label": "波动性", "value": 39, "description": "短期波动性可控。"},
            ],
            "strategies": [
                {"id": "trend-breakout", "name": "趋势突破", "period": "近180天", "return_rate": 12.6, "max_drawdown": -6.4, "win_rate": 57.0, "risk": "medium", "summary": "趋势形态已形成，等待确认信号，不追高。"},
                {"id": "low-valuation-reversal", "name": "低估值反转", "period": "近1年", "return_rate": 8.9, "max_drawdown": -4.1, "win_rate": 54.0, "risk": "low", "summary": "低估特征明显，信心稳固。"},
            ],
            "alerts": [
                {"level": "medium", "title": "估值提醒", "message": "当前市盈率38.5倍，高于历史平均水平。"},
            ],
            "history": [
                {"date": "2024-01-02", "close": 1450.0, "volume": 2340000},
                {"date": "2024-01-03", "close": 1465.5, "volume": 3120000},
                {"date": "2024-01-04", "close": 1478.3, "volume": 2890000},
                {"date": "2024-01-05", "close": 1492.1, "volume": 4560000},
                {"date": "2024-01-08", "close": 1505.8, "volume": 3210000},
                {"date": "2024-01-09", "close": 1518.2, "volume": 2670000},
                {"date": "2024-01-10", "close": 1530.5, "volume": 3450000},
                {"date": "2024-01-11", "close": 1542.3, "volume": 2980000},
                {"date": "2024-01-12", "close": 1551.7, "volume": 3120000},
                {"date": "2024-01-15", "close": 1563.0, "volume": 2780000},
            ],
        },
        "000858": {
            "name": "五粮液",
            "english_name": "Wuliangye",
            "price": 168.5,
            "change_percent": -0.85,
            "score": 76,
            "signal": "neutral",
            "ai_summary": "该股票基本面稳定，具有适度增长潜力。适合中长期投资，关注市场波动。",
            "data_status": "normal",
            "factors": [
                {"key": "capital_flow", "label": "资金流向", "value": 58, "description": "资金流向稳定。"},
                {"key": "valuation", "label": "估值水平", "value": 52, "description": "估值处于合理水平。"},
                {"key": "momentum", "label": "动量指标", "value": 68, "description": "温和上涨动能。"},
                {"key": "volatility", "label": "波动性", "value": 45, "description": "波动在可接受范围内。"},
            ],
            "strategies": [
                {"id": "trend-breakout", "name": "趋势突破", "period": "近180天", "return_rate": 8.2, "max_drawdown": -5.8, "win_rate": 52.0, "risk": "medium", "summary": "横盘整理阶段，等待方向性突破。"},
                {"id": "low-valuation-reversal", "name": "低估值反转", "period": "近1年", "return_rate": 6.5, "max_drawdown": -3.9, "win_rate": 51.0, "risk": "low", "summary": "估值优势存在，适合逢低吸纳。"},
            ],
            "alerts": [],
            "history": [
                {"date": "2024-01-02", "close": 165.0, "volume": 5670000},
                {"date": "2024-01-03", "close": 167.2, "volume": 6890000},
                {"date": "2024-01-04", "close": 169.5, "volume": 5430000},
                {"date": "2024-01-05", "close": 171.2, "volume": 7120000},
                {"date": "2024-01-08", "close": 170.5, "volume": 4980000},
                {"date": "2024-01-09", "close": 169.8, "volume": 5230000},
                {"date": "2024-01-10", "close": 170.2, "volume": 4560000},
                {"date": "2024-01-11", "close": 169.1, "volume": 5890000},
                {"date": "2024-01-12", "close": 168.9, "volume": 4230000},
                {"date": "2024-01-15", "close": 168.5, "volume": 5120000},
            ],
        },
        "601318": {
            "name": "中国平安",
            "english_name": "Ping An",
            "price": 48.2,
            "change_percent": 2.15,
            "score": 68,
            "signal": "buy",
            "ai_summary": "金融板块龙头企业，基本面稳健。当前价格具有良好的入场机会。",
            "data_status": "normal",
            "factors": [
                {"key": "capital_flow", "label": "资金流向", "value": 75, "description": "近期资金大幅净流入。"},
                {"key": "valuation", "label": "估值水平", "value": 48, "description": "估值明显偏低。"},
                {"key": "momentum", "label": "动量指标", "value": 72, "description": "上涨动能强劲。"},
                {"key": "volatility", "label": "波动性", "value": 55, "description": "波动适中。"},
            ],
            "strategies": [
                {"id": "trend-breakout", "name": "趋势突破", "period": "近180天", "return_rate": 15.3, "max_drawdown": -8.2, "win_rate": 59.0, "risk": "medium", "summary": "突破盘整格局。"},
                {"id": "dividend-defense", "name": "分红防御", "period": "近1年", "return_rate": 9.8, "max_drawdown": -4.5, "win_rate": 56.0, "risk": "low", "summary": "分红稳定，收益率有吸引力。"},
            ],
            "alerts": [],
            "history": [
                {"date": "2024-01-02", "close": 42.5, "volume": 12500000},
                {"date": "2024-01-03", "close": 43.8, "volume": 15600000},
                {"date": "2024-01-04", "close": 44.5, "volume": 13200000},
                {"date": "2024-01-05", "close": 45.2, "volume": 18900000},
                {"date": "2024-01-08", "close": 46.1, "volume": 14500000},
                {"date": "2024-01-09", "close": 46.8, "volume": 16700000},
                {"date": "2024-01-10", "close": 47.3, "volume": 12800000},
                {"date": "2024-01-11", "close": 47.8, "volume": 15200000},
                {"date": "2024-01-12", "close": 48.0, "volume": 11900000},
                {"date": "2024-01-15", "close": 48.2, "volume": 14300000},
            ],
        },
        "000001": {
            "name": "平安银行",
            "english_name": "Ping An Bank",
            "price": 12.5,
            "change_percent": -1.23,
            "score": 58,
            "signal": "neutral",
            "ai_summary": "银行业基本面稳定，资产质量可控。信用卡业务增长强劲。",
            "data_status": "normal",
            "factors": [
                {"key": "capital_flow", "label": "Capital Flow", "value": 42, "description": "Mixed capital flow."},
                {"key": "valuation", "label": "Valuation", "value": 55, "description": "Reasonable valuation."},
                {"key": "momentum", "label": "Momentum", "value": 45, "description": "Weak momentum."},
                {"key": "volatility", "label": "Volatility", "value": 48, "description": "Moderate volatility."},
            ],
            "strategies": [
                {"id": "dividend-defense", "name": "Dividend Defense", "period": "Last 1 year", "return_rate": 5.2, "max_drawdown": -3.2, "win_rate": 53.0, "risk": "low", "summary": "Stable dividend strategy suitable for conservative investors."},
            ],
            "alerts": [
                {"level": "high", "title": "Credit Risk", "message": "Non-performing loan ratio slightly above sector average."},
            ],
            "history": [
                {"date": "2024-01-02", "close": 12.8, "volume": 8900000},
                {"date": "2024-01-03", "close": 12.9, "volume": 9200000},
                {"date": "2024-01-04", "close": 12.7, "volume": 7800000},
                {"date": "2024-01-05", "close": 12.6, "volume": 10100000},
                {"date": "2024-01-08", "close": 12.7, "volume": 8500000},
                {"date": "2024-01-09", "close": 12.6, "volume": 9300000},
                {"date": "2024-01-10", "close": 12.5, "volume": 7200000},
                {"date": "2024-01-11", "close": 12.4, "volume": 8100000},
                {"date": "2024-01-12", "close": 12.6, "volume": 6900000},
                {"date": "2024-01-15", "close": 12.5, "volume": 7600000},
            ],
        },
        "600036": {
            "name": "招商银行",
            "english_name": "China Merchants Bank",
            "price": 35.8,
            "change_percent": 0.75,
            "score": 74,
            "signal": "buy",
            "ai_summary": "零售银行业龙头，基本面稳健。数字化转型进展顺利。",
            "data_status": "normal",
            "factors": [
                {"key": "capital_flow", "label": "Capital Flow", "value": 68, "description": "Strong institutional interest."},
                {"key": "valuation", "label": "Valuation", "value": 58, "description": "Slightly undervalued."},
                {"key": "momentum", "label": "Momentum", "value": 65, "description": "Healthy upward trend."},
                {"key": "volatility", "label": "Volatility", "value": 42, "description": "Low volatility."},
            ],
            "strategies": [
                {"id": "trend-breakout", "name": "Trend Breakout", "period": "Last 180 days", "return_rate": 11.2, "max_drawdown": -5.1, "win_rate": 55.0, "risk": "medium", "summary": "Steady upward trend established."},
                {"id": "dividend-defense", "name": "Dividend Defense", "period": "Last 1 year", "return_rate": 8.5, "max_drawdown": -3.8, "win_rate": 54.0, "risk": "low", "summary": "Consistent dividend growth."},
            ],
            "alerts": [],
            "history": [
                {"date": "2024-01-02", "close": 33.2, "volume": 6700000},
                {"date": "2024-01-03", "close": 33.8, "volume": 8200000},
                {"date": "2024-01-04", "close": 34.1, "volume": 7100000},
                {"date": "2024-01-05", "close": 34.5, "volume": 9500000},
                {"date": "2024-01-08", "close": 35.0, "volume": 6800000},
                {"date": "2024-01-09", "close": 35.3, "volume": 7400000},
                {"date": "2024-01-10", "close": 35.5, "volume": 6200000},
                {"date": "2024-01-11", "close": 35.6, "volume": 5800000},
                {"date": "2024-01-12", "close": 35.4, "volume": 7100000},
                {"date": "2024-01-15", "close": 35.8, "volume": 6500000},
            ],
        },
    }

    # 先插入所有股票（父表）
    for code, detail in stocks_data.items():
        existing_stock = db.query(Stock).filter(Stock.code == code).first()
        if not existing_stock:
            stock = Stock(
                code=code,
                name=detail["name"],
                english_name=detail.get("english_name", ""),
                price=detail["price"],
                change_percent=detail["change_percent"],
                score=detail["score"],
                signal=detail["signal"],
                ai_summary=detail["ai_summary"],
                data_status=detail["data_status"],
                updated_at=datetime.now(timezone.utc),
            )
            db.add(stock)

    # 先提交股票数据
    db.commit()

    # 然后插入关联数据（子表）
    for code, detail in stocks_data.items():
        for factor in detail["factors"]:
            existing_factor = db.query(FactorScoreDB).filter(
                FactorScoreDB.stock_code == code,
                FactorScoreDB.key == factor["key"]
            ).first()
            if not existing_factor:
                fs = FactorScoreDB(
                    stock_code=code,
                    key=factor["key"],
                    label=factor["label"],
                    value=factor["value"],
                    description=factor["description"],
                )
                db.add(fs)

        for strategy in detail["strategies"]:
            strategy_id = f"{code}-{strategy['id']}"
            existing_strategy = db.query(StrategyResultDB).filter(
                StrategyResultDB.id == strategy_id
            ).first()
            if not existing_strategy:
                sr = StrategyResultDB(
                    id=strategy_id,
                    stock_code=code,
                    name=strategy["name"],
                    period=strategy["period"],
                    return_rate=strategy["return_rate"],
                    max_drawdown=strategy["max_drawdown"],
                    win_rate=strategy["win_rate"],
                    risk=strategy["risk"],
                    summary=strategy["summary"],
                )
                db.add(sr)

        for point in detail["history"]:
            existing_point = db.query(PricePointDB).filter(
                PricePointDB.stock_code == code,
                PricePointDB.date == point["date"]
            ).first()
            if not existing_point:
                ph = PricePointDB(
                    stock_code=code,
                    date=point["date"],
                    close=point["close"],
                    volume=point["volume"],
                )
                db.add(ph)

        for alert in detail["alerts"]:
            existing_alert = db.query(AlertItemDB).filter(
                AlertItemDB.stock_code == code,
                AlertItemDB.title == alert["title"]
            ).first()
            if not existing_alert:
                al = AlertItemDB(
                    stock_code=code,
                    level=alert["level"],
                    title=alert["title"],
                    message=alert["message"],
                )
                db.add(al)

    # 插入用户数据 - 所有密码必须符合强密码要求（长度≥8、包含大小写字母、数字和特殊字符）
    users = [
        ("admin", "Test@bcd!234"),
        ("demo", "Demo@123!"),
        ("user", "User@456!"),
    ]
    for username, password in users:
        password_validation = validate_password_strength(password)
        if not password_validation["valid"]:
            raise ValueError(f"Password for user '{username}' does not meet strength requirements: {', '.join(password_validation['messages'])}")
        
        existing_user = db.query(User).filter(User.username == username).first()
        if not existing_user:
            user = User(username=username, password=hash_password(password))
            db.add(user)
        elif not is_password_hash(existing_user.password):
            existing_user.password = hash_password(password)
            existing_user.updated_at = datetime.now(timezone.utc)
        elif not verify_password(password, existing_user.password):
            existing_user.password = hash_password(password)
            existing_user.updated_at = datetime.now(timezone.utc)

    db.commit()
