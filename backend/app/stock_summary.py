from app.database import PricePointDB, Stock
from app.schemas import AlertItem, DataCompleteness, FactorScore, ReferenceStatus, StockSummary


def determine_data_completeness(
    stock: Stock,
    history: list[PricePointDB] | None = None,
    factors: list[FactorScore] | None = None,
) -> DataCompleteness:
    if stock.data_status == "partial":
        return "incomplete"
    if history is not None and len(history) < 20:
        return "insufficient"
    if factors is not None and len(factors) >= 4 and stock.updated_at:
        return "complete"
    if stock.updated_at:
        return "mostly_complete"
    return "incomplete"


def determine_reference_status(
    score: int,
    signal: str,
    data_completeness: DataCompleteness,
    alerts: list[AlertItem] | None = None,
) -> ReferenceStatus:
    if data_completeness in ("insufficient", "incomplete"):
        return "insufficient_data"

    high_alert_count = len([alert for alert in (alerts or []) if alert.level == "high"])
    if high_alert_count >= 2 or signal == "sell" or score < 45:
        return "cautious"
    if score >= 70 and signal == "buy" and high_alert_count == 0:
        return "positive"
    return "watch"


def reference_label(status: ReferenceStatus) -> str:
    return {
        "positive": "偏积极",
        "watch": "中性观察",
        "cautious": "偏谨慎",
        "insufficient_data": "数据不足",
    }[status]


def build_primary_support(score: int, status: ReferenceStatus) -> str:
    if status == "positive":
        return "当前综合表现靠前，适合加入重点观察，但仍需自行评估风险与仓位。"
    if status == "watch":
        return "当前缺少明确优势，适合继续观察后续业绩、资金和价格趋势变化。"
    if status == "cautious":
        return "当前风险项较多，建议先确认风险是否可接受。"
    return "当前数据不足，暂不适合形成明确判断。"


def build_primary_risk(status: ReferenceStatus, data_completeness: DataCompleteness) -> str:
    if data_completeness in ("insufficient", "incomplete"):
        return "关键数据不完整，结论只能弱参考。"
    if status == "positive":
        return "仍需关注估值、仓位和短期波动，不能只凭排序操作。"
    if status == "cautious":
        return "需要重点检查估值、波动、资金流出或盈利变化。"
    return "需要等待更明确的支撑因素或风险变化。"



def stock_to_summary(
    stock: Stock,
    history: list[PricePointDB] | None = None,
    factors: list[FactorScore] | None = None,
    alerts: list[AlertItem] | None = None,
) -> StockSummary:
    score = stock.score or 50
    data_completeness = determine_data_completeness(stock, history, factors)
    status = determine_reference_status(score, stock.signal or "neutral", data_completeness, alerts)
    return StockSummary(
        code=stock.code,
        name=stock.name,
        price=stock.price or 0,
        change_percent=stock.change_percent or 0,
        score=score,
        signal=stock.signal or "neutral",
        reference_status=status,
        reference_label=reference_label(status),
        primary_support=build_primary_support(score, status),
        primary_risk=build_primary_risk(status, data_completeness),
        data_completeness=data_completeness,
        data_updated_at=stock.updated_at,
    )

