from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import tushare_config
from app.database import Stock, get_db
from app.eastmoney_service import get_eastmoney_service
from app.routers.stocks import get_initialized_tushare_service
from app.tushare_service import get_tushare_service

router = APIRouter(prefix="/api")

@router.get("/tushare/status")
def get_tushare_status():
    """Return TuShare connection status."""
    service = get_initialized_tushare_service() if tushare_config.token else get_tushare_service()
    return {
        "enabled": tushare_config.enabled,
        "has_token": bool(tushare_config.token),
        "pro_initialized": bool(getattr(service, "pro", None)),
        "status": "connected" if tushare_config.enabled else "disabled"
    }


@router.get("/eastmoney/status")
def get_eastmoney_status():
    """Return EastMoney service status."""
    return {
        "enabled": True,
        "status": "connected"
    }


@router.get("/eastmoney/refresh/{code}")
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
