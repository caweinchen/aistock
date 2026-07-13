import logging
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import (
    AlertItemDB,
    DividendDB,
    FactorScoreDB,
    InstHoldDB,
    PricePointDB,
    Stock,
    User,
    WatchlistItem,
    WatchlistInsightBaselineDB,
    get_db,
)
from app.eastmoney_service import get_eastmoney_service
from app.ordinary_user import build_data_health
from app.routers.auth import get_current_user
from app.schemas import (
    ChecklistItem,
    PreTradeChecklist,
    ReferenceStatus,
    StockSummary,
    WatchlistDataHealthOverview,
    WatchlistInsights,
    WatchlistIntelligence,
    WatchlistObservation,
    WatchlistRadar,
    WatchlistStockInsight,
)
from app.stock_summary import stock_to_summary
from app.watchlist_intelligence import build_watchlist_intelligence

logger = logging.getLogger("stocks")
router = APIRouter(prefix="/api/watchlist")


def _group_by_stock_code(rows) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for row in rows:
        grouped.setdefault(row.stock_code, []).append(row)
    return grouped


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


def watchlist_intelligence_to_model(result) -> WatchlistIntelligence:
    return WatchlistIntelligence(
        radar=WatchlistRadar(**result.radar.__dict__),
        observations=[WatchlistObservation(**item.__dict__) for item in result.observations],
        insights=[
            WatchlistStockInsight(
                **{
                    **item.__dict__,
                    "recent_change": item.recent_change.__dict__,
                }
            )
            for item in result.insights
        ],
        sort_modes=result.sort_modes,
        risk_overview=result.risk_overview.__dict__,
        industry_concentration=result.industry_concentration.__dict__,
    )


@router.get("")
def get_watchlist(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()
        logger.info(f"Loaded watchlist [{user.username}]: {len(items)} items")
        return {"codes": [item.stock_code for item in items]}
    except Exception as e:
        logger.error(f"Failed to load watchlist for user [{user.username}]: {e}")
        raise HTTPException(status_code=500, detail="Failed to load watchlist")


@router.get("/insights", response_model=WatchlistInsights)
def get_watchlist_insights(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    watchlist_items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()
    codes = [item.stock_code for item in watchlist_items]
    stocks = db.query(Stock).filter(Stock.code.in_(codes)).all() if codes else []
    histories = _group_by_stock_code(db.query(PricePointDB).filter(PricePointDB.stock_code.in_(codes)).all()) if codes else {}
    factors = _group_by_stock_code(db.query(FactorScoreDB).filter(FactorScoreDB.stock_code.in_(codes)).all()) if codes else {}
    alerts = _group_by_stock_code(db.query(AlertItemDB).filter(AlertItemDB.stock_code.in_(codes)).all()) if codes else {}
    holders = _group_by_stock_code(db.query(InstHoldDB).filter(InstHoldDB.stock_code.in_(codes)).all()) if codes else {}
    dividends = _group_by_stock_code(db.query(DividendDB).filter(DividendDB.stock_code.in_(codes)).all()) if codes else {}
    groups: dict[ReferenceStatus, list[StockSummary]] = {
        "positive": [],
        "watch": [],
        "cautious": [],
        "insufficient_data": [],
    }
    latest_updated_at = None
    data_insufficient_count = 0
    data_incomplete_count = 0
    stock_contexts = []
    baselines = {
        row.stock_code: row
        for row in db.query(WatchlistInsightBaselineDB).filter(
            WatchlistInsightBaselineDB.user_id == user.id,
            WatchlistInsightBaselineDB.stock_code.in_(codes),
        ).all()
    } if codes else {}

    for stock in stocks:
        summary = stock_to_summary(stock)
        data_health_result = build_data_health(
            stock,
            histories.get(stock.code),
            factors.get(stock.code),
            alerts.get(stock.code),
            holders.get(stock.code),
            dividends.get(stock.code),
        )
        if data_health_result.completeness == "insufficient":
            data_insufficient_count += 1
        if data_health_result.completeness == "incomplete":
            data_incomplete_count += 1
        baseline = baselines.get(stock.code)
        stock_contexts.append(SimpleNamespace(
            stock=stock,
            summary=summary,
            data_health=data_health_result,
            support_factors=[summary.primary_support],
            risk_factors=[summary.primary_risk],
            baseline_score=baseline.score if baseline else None,
            baseline_risk_score=baseline.risk_score if baseline else None,
            baseline_published_at=baseline.published_at if baseline else None,
            baseline_data_completeness=baseline.data_completeness if baseline else None,
        ))
        groups[summary.reference_status].append(summary)
        if stock.updated_at and (latest_updated_at is None or stock.updated_at > latest_updated_at):
            latest_updated_at = stock.updated_at

    cautious_count = len(groups["cautious"])
    group_insufficient_count = len(groups["insufficient_data"])
    if cautious_count:
        risk_overview = f"当前自选股中有 {cautious_count} 只需要谨慎关注。"
    elif group_insufficient_count:
        risk_overview = f"当前自选股中有 {group_insufficient_count} 只数据不足，建议先补充数据。"
    else:
        risk_overview = "当前自选股未发现集中高风险提示，仍需结合仓位和估值检查。"

    if data_insufficient_count:
        health_message = f"当前自选股中有 {data_insufficient_count} 只数据不足，相关结论已降级。"
    elif data_incomplete_count:
        health_message = f"当前自选股中有 {data_incomplete_count} 只数据不完整，建议结合详情页继续查看。"
    else:
        health_message = "当前自选股数据健康状况可用于基础参考。"

    intelligence_result = build_watchlist_intelligence(stock_contexts)

    published_at = datetime.now(timezone.utc)
    for insight in intelligence_result.insights:
        baseline = baselines.get(insight.code)
        if baseline is None:
            baseline = WatchlistInsightBaselineDB(user_id=user.id, stock_code=insight.code)
            db.add(baseline)
        baseline.score = insight.score
        baseline.risk_score = insight.risk_score
        baseline.data_completeness = insight.data_completeness
        baseline.published_at = published_at
    if intelligence_result.insights:
        db.commit()

    return WatchlistInsights(
        total=len(stocks),
        groups=groups,
        risk_overview=risk_overview,
        data_updated_at=latest_updated_at,
        data_health_overview=WatchlistDataHealthOverview(
            total=len(stocks),
            insufficient_count=data_insufficient_count,
            incomplete_count=data_incomplete_count,
            latest_updated_at=latest_updated_at,
            message=health_message,
        ),
        intelligence=watchlist_intelligence_to_model(intelligence_result),
    )


@router.post("/{code}")
def add_to_watchlist(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logger.info(f"Adding stock to watchlist for user [{user.username}]: {code}")

    try:
        stock = db.query(Stock).filter(Stock.code == code).first()
        if not stock:
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
                logger.info(f"Created stock while adding to watchlist: {code} - {stock.name}")
            else:
                logger.error(f"Stock info not found while adding to watchlist: {code}")
                raise HTTPException(status_code=404, detail="Stock not found")

        if stock.price <= 0:
            update_stock_realtime_quote(db, stock)

        existing_item = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == user.id,
            WatchlistItem.stock_code == code,
        ).first()
        if not existing_item:
            db.add(WatchlistItem(user_id=user.id, stock_code=code))
            db.commit()
            logger.info(f"Added stock to watchlist for user [{user.username}]: {code}")

        codes = [item.stock_code for item in db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()]
        stocks = db.query(Stock).filter(Stock.code.in_(codes)).all() if codes else []
        return [stock_to_summary(s) for s in stocks]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add stock to watchlist for user [{user.username}] {code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add to watchlist")


@router.delete("/{code}")
def remove_from_watchlist(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logger.info(f"Removing stock from watchlist for user [{user.username}]: {code}")

    try:
        stock = db.query(Stock).filter(Stock.code == code).first()
        if not stock:
            logger.error(f"Stock not found while removing from watchlist: {code}")
            raise HTTPException(status_code=404, detail="Stock not found")

        item = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == user.id,
            WatchlistItem.stock_code == code,
        ).first()
        if item:
            db.delete(item)
            db.commit()
            logger.info(f"Removed stock from watchlist for user [{user.username}]: {code}")

        codes = [item.stock_code for item in db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()]
        stocks = db.query(Stock).filter(Stock.code.in_(codes)).all() if codes else []
        return [stock_to_summary(s) for s in stocks]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove stock from watchlist for user [{user.username}] {code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove from watchlist")
