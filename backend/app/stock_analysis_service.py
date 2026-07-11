from dataclasses import dataclass
import logging
import re
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.database import AlertItemDB, FactorScoreDB, Stock
from app.schemas import AlertItem, FactorScore


logger = logging.getLogger("stocks")


@dataclass(frozen=True)
class AnalysisOperations:
    get_tushare_service: Callable[[], Any]
    calculate_financial_factors: Callable[[list, dict, dict, list], list[FactorScore]]
    calculate_local_factors: Callable[[list], list]
    factor_to_model: Callable[[FactorScoreDB], FactorScore]
    item_value: Callable[[Any, str, Any], Any]
    stock_ts_code: Callable[[Stock], str]


def ensure_factor_scores(db: Session, stock: Stock, history: list, operations: AnalysisOperations) -> list[FactorScore]:
    factors = []
    try:
        tushare = operations.get_tushare_service()
        if tushare.pro:
            factors = operations.calculate_financial_factors(
                history,
                tushare.get_daily_basic(operations.stock_ts_code(stock)),
                tushare.get_fina_indicator(operations.stock_ts_code(stock)),
                tushare.get_moneyflow(operations.stock_ts_code(stock)),
            )
            if factors:
                _persist_factors(db, stock, factors, operations.item_value)
                return factors
    except Exception as exc:
        logger.error("Failed to fetch financial data for stock %s: %s", stock.code, exc)
        db.rollback()
    if not factors and history:
        factors = operations.calculate_local_factors(history)
        if factors:
            _persist_factors(db, stock, factors, operations.item_value)
    return [operations.factor_to_model(row) for row in db.query(FactorScoreDB).filter(FactorScoreDB.stock_code == stock.code).all()]


def _persist_factors(db, stock, factors, item_value) -> None:
    db.query(FactorScoreDB).filter(FactorScoreDB.stock_code == stock.code).delete()
    for factor in factors:
        db.add(FactorScoreDB(
            stock_code=stock.code,
            key=item_value(factor, "key", ""),
            label=item_value(factor, "label", ""),
            value=item_value(factor, "value", 50),
            description=item_value(factor, "description", ""),
        ))
    db.commit()


def ensure_alerts(db: Session, stock: Stock, history: list, factors: list) -> list[AlertItem]:
    alerts = []
    valuation = next((factor for factor in factors if factor.key == "valuation"), None)
    if valuation and valuation.value > 70 and "PE" in valuation.description:
        match = re.search(r"PE.*?(\d+\.?\d*)", valuation.description)
        if match and float(match.group(1)) > 50:
            alerts.append(AlertItem(level="high", title="估值过高风险", message=f"当前PE(TTM)为{float(match.group(1)):.1f}倍，远高于行业平均水平。"))
    volatility = next((factor for factor in factors if factor.key == "volatility"), None)
    if volatility and volatility.value > 65:
        alerts.append(AlertItem(level="medium", title="波动性风险", message=volatility.description))
    capital = next((factor for factor in factors if factor.key == "capital_flow"), None)
    if capital and capital.value < 35:
        alerts.append(AlertItem(level="medium", title="资金流出风险", message=capital.description))
    profitability = next((factor for factor in factors if factor.key == "profitability"), None)
    if profitability and profitability.value < 35:
        alerts.append(AlertItem(level="high", title="盈利能力风险", message=profitability.description))
    if history and len(history) >= 10:
        closes = [point.close for point in history[-10:]]
        change = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0
        if change < -15:
            alerts.append(AlertItem(level="high", title="价格下跌风险", message=f"近10日累计下跌{abs(change):.1f}%。"))
        elif change > 20:
            alerts.append(AlertItem(level="medium", title="短期涨幅过大", message=f"近10日累计上涨{change:.1f}%。"))
    if alerts:
        db.query(AlertItemDB).filter(AlertItemDB.stock_code == stock.code).delete()
        for alert in alerts:
            db.add(AlertItemDB(stock_code=stock.code, level=alert.level, title=alert.title, message=alert.message))
        db.commit()
    return alerts


def ensure_ai_summary(db: Session, stock: Stock, history: list, factors: list, alerts: list) -> str:
    average = sum(factor.value for factor in factors) / len(factors) if factors else 50
    if average >= 70:
        parts = ["综合分析显示，该股票基本面强劲，各项指标表现优秀。"]
    elif average >= 55:
        parts = ["综合分析显示，该股票基本面稳健，多数指标表现良好。"]
    elif average >= 40:
        parts = ["综合分析显示，该股票基本面一般，部分指标需要关注。"]
    else:
        parts = ["综合分析显示，该股票基本面较弱，多项指标表现不佳。"]
    for factor in factors:
        if factor.value >= 70:
            parts.append(f"{factor.label}方面表现优秀：{factor.description}")
        elif factor.value <= 35:
            parts.append(f"{factor.label}方面需要关注：{factor.description}")
    high = [alert for alert in alerts if alert.level == "high"]
    medium = [alert for alert in alerts if alert.level == "medium"]
    if high:
        parts.append(f"高风险提示：{'; '.join(alert.title for alert in high)}。")
    if medium:
        parts.append(f"中等风险提示：{'; '.join(alert.title for alert in medium)}。")
    if average >= 70 and not alerts:
        parts.append("建议积极关注，可考虑逢低布局。")
    elif average >= 55 and len(alerts) <= 1:
        parts.append("建议持仓观望，适当控制仓位。")
    elif average < 40 or len(high) >= 2:
        parts.append("建议谨慎观望，等待基本面改善。")
    else:
        parts.append("建议适度关注，注意风险控制。")
    summary = "。".join(parts)
    stock.ai_summary = summary
    db.commit()
    return summary
