from datetime import datetime, timezone
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import tushare_config
from app.database import get_db, init_db, init_sample_data
from app.eastmoney_service import init_eastmoney
from app.routers.admin import router as admin_router
from app.routers.auth import decrypt_password, router as auth_router
from app.routers.backtests import router as backtests_router
from app.routers.data_sources import router as data_sources_router
from app.routers.stocks import (
    _history_needs_refresh,
    _is_trading_time,
    _last_market_session_end_time,
    build_strategy_detail,
    engine_result_to_detail,
    engine_result_to_strategy,
    ensure_price_history,
    get_stock_adj_factor,
    get_stock_dividend,
    get_stock_inst_hold,
    get_stock_news,
    get_tushare_service,
    router as stocks_router,
)
from app.routers.watchlist import router as watchlist_router
from app.schemas import PricePoint, StockDetail, StockSummary, StrategyResult
from app.tushare_service import init_tushare

# Application logger.
logger = logging.getLogger("stocks")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 认证依赖
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

app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(stocks_router)
app.include_router(data_sources_router)
app.include_router(backtests_router)
app.include_router(admin_router)


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


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}
