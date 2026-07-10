from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database import DividendDB, InstHoldDB, Stock, StrategyResultDB
from app.ordinary_user import build_data_health, build_pre_trade_checklist, build_risk_explanations
from app.schemas import (
    AlertItem,
    ChecklistItem,
    DataCompleteness,
    DataHealth,
    FactorScore,
    PreTradeChecklist,
    RiskExplanation,
    StockDetail,
    StrategyResult,
)
from app.stock_summary import (
    build_primary_risk,
    build_primary_support,
    determine_data_completeness,
    determine_reference_status,
    stock_to_summary,
)


@dataclass(frozen=True)
class StockDetailOperations:
    update_realtime_quote: Callable[..., Any]
    ensure_price_history: Callable[..., list]
    ensure_factor_scores: Callable[..., list]
    ensure_alerts: Callable[..., list]
    calculate_strategies: Callable[..., list]
    strategy_to_model: Callable[..., StrategyResult]
    factor_to_model: Callable[..., FactorScore]
    alert_to_model: Callable[..., AlertItem]
    price_to_model: Callable[..., Any]
    ensure_ai_summary: Callable[..., str | None]


def _build_ordinary_stock_summary(
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


def _checklist_to_model(result) -> PreTradeChecklist:
    return PreTradeChecklist(
        mode=result.mode,
        title=result.title,
        completion_hint=result.completion_hint,
        items=[ChecklistItem(**item.__dict__) for item in result.items],
    )


def assemble_stock_detail(
    db: Session,
    code: str,
    update_realtime: bool,
    operations: StockDetailOperations,
) -> StockDetail:
    stock = db.query(Stock).filter(Stock.code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    now = datetime.now()
    need_update_realtime = update_realtime
    if stock.updated_at and update_realtime:
        last_update_date = stock.updated_at.date() if hasattr(stock.updated_at, "date") else stock.updated_at
        if last_update_date == now.date() and now.hour >= 15:
            need_update_realtime = False

    if need_update_realtime:
        operations.update_realtime_quote(db, stock)
    history = operations.ensure_price_history(db, stock)
    factors = operations.ensure_factor_scores(db, stock, history)
    alerts = operations.ensure_alerts(db, stock, history, factors)
    custom_strategies = db.query(StrategyResultDB).filter(
        StrategyResultDB.stock_code == code,
        StrategyResultDB.id.like("custom-%"),
    ).all()
    strategy_models = [
        StrategyResult(**strategy)
        for strategy in operations.calculate_strategies(history)
    ] + [operations.strategy_to_model(strategy) for strategy in custom_strategies]
    factor_models = [operations.factor_to_model(factor) for factor in factors]
    alert_models = [operations.alert_to_model(alert) for alert in alerts]
    data_completeness = determine_data_completeness(stock, history, factor_models)
    holder_rows = db.query(InstHoldDB).filter(InstHoldDB.stock_code == code).all()
    dividend_rows = db.query(DividendDB).filter(DividendDB.stock_code == code).all()
    data_health_result = build_data_health(stock, history, factor_models, alert_models, holder_rows, dividend_rows)
    risk_results = build_risk_explanations(
        stock,
        factor_models,
        alert_models,
        holder_rows,
        dividend_rows,
        data_health_result,
    )
    buy_checklist_result = build_pre_trade_checklist(stock, risk_results, data_health_result, mode="buy")
    sell_checklist_result = build_pre_trade_checklist(stock, risk_results, data_health_result, mode="sell")
    ordinary_summary, support_factors, risk_factors = _build_ordinary_stock_summary(
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
        history=[operations.price_to_model(price) for price in history],
        ai_summary=operations.ensure_ai_summary(db, stock, history, factors, alerts),
        data_status=stock.data_status,
        updated_at=stock.updated_at,
        ordinary_summary=ordinary_summary,
        support_factors=support_factors,
        risk_factors=risk_factors,
        data_completeness=data_completeness,
        data_updated_at=stock.updated_at,
        data_health=DataHealth(**data_health_result.__dict__),
        risk_explanations=[RiskExplanation(**result.__dict__) for result in risk_results],
        buy_checklist=_checklist_to_model(buy_checklist_result),
        sell_checklist=_checklist_to_model(sell_checklist_result),
    )
