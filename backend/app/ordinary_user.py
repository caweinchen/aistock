from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

DataCompleteness = Literal["complete", "mostly_complete", "incomplete", "insufficient"]
RiskLevel = Literal["low", "medium", "high"]
RiskType = Literal["valuation", "volatility", "fundamentals", "holder_change", "dividend", "data_quality"]
ChecklistMode = Literal["buy", "sell"]
ChecklistStatus = Literal["pass", "attention", "user_confirm", "insufficient_data"]


@dataclass
class DataHealthResult:
    completeness: DataCompleteness
    updated_at: datetime | None
    source_summary: list[str] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    downgrade_reasons: list[str] = field(default_factory=list)
    user_message: str = ""


@dataclass
class RiskExplanationResult:
    type: RiskType
    level: RiskLevel
    title: str
    what_it_means: str
    why_it_matters: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class ChecklistItemResult:
    key: str
    label: str
    status: ChecklistStatus
    explanation: str
    user_confirm_required: bool = False


@dataclass
class PreTradeChecklistResult:
    mode: ChecklistMode
    title: str
    completion_hint: str
    items: list[ChecklistItemResult] = field(default_factory=list)


def _item_count(items) -> int:
    return len(items or [])


def build_data_health(stock, history=None, factors=None, alerts=None, holders=None, dividends=None) -> DataHealthResult:
    history_count = _item_count(history)
    factor_count = _item_count(factors)
    alert_count = _item_count(alerts)
    holder_count = _item_count(holders)
    dividend_count = _item_count(dividends)
    updated_at = getattr(stock, "updated_at", None)
    data_status = getattr(stock, "data_status", "normal")

    source_summary: list[str] = []
    missing_items: list[str] = []
    downgrade_reasons: list[str] = []

    if history_count >= 20:
        source_summary.append("本地历史行情")
    else:
        missing_items.append("历史行情不足")
        downgrade_reasons.append("历史行情样本少于 20 条")

    if factor_count >= 4:
        source_summary.append("本地因子评分")
    else:
        missing_items.append("财务和因子数据不足")
        downgrade_reasons.append("估值、趋势、波动或盈利因子不完整")

    if alert_count:
        source_summary.append("本地风险提示")
    if holder_count:
        source_summary.append("重要股东变动")
    elif history_count < 20 or factor_count < 4:
        missing_items.append("重要股东变动数据不足")
    if dividend_count:
        source_summary.append("分红记录")

    if data_status == "partial":
        downgrade_reasons.append("股票基础数据处于部分可用状态")
    if updated_at is None:
        missing_items.append("最近更新时间缺失")
        downgrade_reasons.append("无法确认数据新鲜度")

    if history_count < 20 or factor_count < 2 or updated_at is None:
        completeness: DataCompleteness = "insufficient"
        user_message = "当前数据不足，暂不适合形成明确判断。"
    elif data_status == "partial" or factor_count < 4:
        completeness = "incomplete"
        user_message = "当前关键数据不完整，结论只能弱参考。"
    else:
        completeness = "complete"
        user_message = "当前关键数据较完整，结论可信度相对较高。"

    return DataHealthResult(
        completeness=completeness,
        updated_at=updated_at,
        source_summary=source_summary,
        missing_items=list(dict.fromkeys(missing_items)),
        downgrade_reasons=list(dict.fromkeys(downgrade_reasons)),
        user_message=user_message,
    )


def _factor_value(factors, key: str) -> int | None:
    for factor in factors or []:
        if getattr(factor, "key", "") == key:
            return getattr(factor, "value", None)
    return None


def _factor_description(factors, key: str) -> str | None:
    for factor in factors or []:
        if getattr(factor, "key", "") == key:
            return getattr(factor, "description", None)
    return None


def build_risk_explanations(stock, factors=None, alerts=None, holders=None, dividends=None, data_health=None) -> list[RiskExplanationResult]:
    risks: list[RiskExplanationResult] = []
    factors = factors or []
    alerts = alerts or []
    holders = holders or []
    dividends = dividends or []

    valuation = _factor_value(factors, "valuation")
    if valuation is not None and valuation < 45:
        risks.append(RiskExplanationResult(
            type="valuation",
            level="high" if valuation < 35 else "medium",
            title="估值风险",
            what_it_means="当前估值指标偏弱，价格可能已经反映较多乐观预期。",
            why_it_matters="如果后续业绩增长跟不上，股价可能承压。",
            evidence=[_factor_description(factors, "valuation") or f"估值因子为 {valuation} 分"],
        ))

    volatility = _factor_value(factors, "volatility")
    if volatility is not None and volatility < 45:
        risks.append(RiskExplanationResult(
            type="volatility",
            level="high" if volatility < 35 else "medium",
            title="波动风险",
            what_it_means="近期价格波动偏高，短期回撤可能超出普通用户预期。",
            why_it_matters="波动较大时，用户更容易因短期涨跌做出情绪化决策。",
            evidence=[_factor_description(factors, "volatility") or f"波动因子为 {volatility} 分"],
        ))

    profitability = _factor_value(factors, "profitability")
    if profitability is not None and profitability < 45:
        risks.append(RiskExplanationResult(
            type="fundamentals",
            level="medium",
            title="业绩质量风险",
            what_it_means="盈利质量或基本面因子偏弱。",
            why_it_matters="基本面偏弱时，价格上涨更依赖情绪或短期资金推动。",
            evidence=[_factor_description(factors, "profitability") or f"盈利因子为 {profitability} 分"],
        ))

    negative_holder_changes = [
        holder for holder in holders
        if getattr(holder, "change_amount", 0) is not None and getattr(holder, "change_amount", 0) < 0
    ]
    if negative_holder_changes:
        risks.append(RiskExplanationResult(
            type="holder_change",
            level="medium",
            title="重要股东变动风险",
            what_it_means="重要持有人出现减持迹象。",
            why_it_matters="连续或明显减持可能带来筹码压力，需要结合公告和价格表现继续观察。",
            evidence=[f"发现 {len(negative_holder_changes)} 条重要股东减持记录"],
        ))

    if not dividends:
        risks.append(RiskExplanationResult(
            type="dividend",
            level="low",
            title="分红稳定性信息不足",
            what_it_means="当前缺少可用于判断分红稳定性的记录。",
            why_it_matters="分红记录不足时，不能把长期持有回报作为强支撑因素。",
            evidence=["未读取到分红记录"],
        ))

    high_alerts = [alert for alert in alerts if getattr(alert, "level", "") == "high"]
    for alert in high_alerts[:2]:
        risks.append(RiskExplanationResult(
            type="fundamentals",
            level="high",
            title=getattr(alert, "title", "高风险提示"),
            what_it_means=getattr(alert, "message", "系统发现高风险提示。"),
            why_it_matters="高风险提示可能影响普通用户的风险承受判断。",
            evidence=[getattr(alert, "message", "高风险提示")],
        ))

    if data_health and data_health.completeness in ("insufficient", "incomplete"):
        risks.insert(0, RiskExplanationResult(
            type="data_quality",
            level="high" if data_health.completeness == "insufficient" else "medium",
            title="数据不足风险",
            what_it_means=data_health.user_message,
            why_it_matters="数据不足时，系统不应形成过强结论，用户需要先补充或刷新数据。",
            evidence=data_health.missing_items or data_health.downgrade_reasons,
        ))

    return risks[:6]
