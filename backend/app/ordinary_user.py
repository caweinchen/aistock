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
