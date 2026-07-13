from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


WatchlistFocusLevel = Literal["priority", "watch", "cautious", "insufficient_data"]
WatchlistSortMode = Literal["overall", "risk", "data_health", "recent_change"]
ObservationType = Literal["priority", "risk", "data_quality", "refresh", "balanced"]
AvailabilityStatus = Literal["available", "insufficient_data"]
PortfolioRiskLevel = Literal["low", "medium", "high", "insufficient_data"]


@dataclass
class WatchlistRecentChangeResult:
    status: AvailabilityStatus = "insufficient_data"
    score_change: int | None = None
    risk_score_change: int | None = None
    baseline_at: datetime | None = None
    current_updated_at: datetime | None = None


@dataclass
class WatchlistRiskOverviewResult:
    status: AvailabilityStatus = "insufficient_data"
    level: PortfolioRiskLevel = "insufficient_data"
    total_count: int = 0
    high_risk_count: int = 0
    insufficient_count: int = 0


@dataclass
class WatchlistIndustryConcentrationResult:
    status: AvailabilityStatus = "insufficient_data"
    top_industry: str | None = None
    top_industry_count: int = 0
    top_industry_ratio: float | None = None
    is_concentrated: bool = False


@dataclass
class WatchlistStockInsightResult:
    code: str
    name: str
    focus_level: WatchlistFocusLevel
    focus_label: str
    focus_reason: str
    support_points: list[str] = field(default_factory=list)
    risk_points: list[str] = field(default_factory=list)
    data_completeness: str = "incomplete"
    score: int | None = None
    risk_score: int = 0
    priority_score: int = 0
    updated_at: datetime | None = None
    industry: str | None = None
    recent_change: WatchlistRecentChangeResult = field(default_factory=WatchlistRecentChangeResult)


@dataclass
class WatchlistRadarResult:
    title: str
    summary: str
    priority_count: int = 0
    cautious_count: int = 0
    insufficient_count: int = 0
    average_score: float | None = None


@dataclass
class WatchlistObservationResult:
    type: ObservationType
    title: str
    description: str
    stock_codes: list[str] = field(default_factory=list)


@dataclass
class WatchlistIntelligenceResult:
    radar: WatchlistRadarResult
    observations: list[WatchlistObservationResult] = field(default_factory=list)
    insights: list[WatchlistStockInsightResult] = field(default_factory=list)
    sort_modes: list[WatchlistSortMode] = field(default_factory=lambda: ["overall", "risk", "data_health", "recent_change"])
    risk_overview: WatchlistRiskOverviewResult = field(default_factory=WatchlistRiskOverviewResult)
    industry_concentration: WatchlistIndustryConcentrationResult = field(default_factory=WatchlistIndustryConcentrationResult)


def _as_list(value) -> list[str]:
    return [str(item) for item in (value or []) if str(item).strip()]


def _data_completeness(context) -> str:
    data_health = getattr(context, "data_health", None)
    return getattr(data_health, "completeness", "incomplete")


def _updated_at(context):
    data_health = getattr(context, "data_health", None)
    stock = getattr(context, "stock", None)
    return getattr(data_health, "updated_at", None) or getattr(stock, "updated_at", None)


def _risk_score(risk_points: list[str], completeness: str, score: int | None) -> int:
    value = len(risk_points) * 20
    if completeness == "insufficient":
        value += 40
    elif completeness == "incomplete":
        value += 20
    if score is not None and score < 45:
        value += 25
    return min(value, 100)


def _priority_score(support_points: list[str], risk_score: int, score: int | None, completeness: str) -> int:
    value = len(support_points) * 15
    if score is not None:
        value += max(score - 50, 0)
    value -= risk_score // 2
    if completeness == "insufficient":
        value -= 50
    return max(min(value, 100), 0)


def _recent_change(context, score: int | None, risk_score: int, completeness: str) -> WatchlistRecentChangeResult:
    baseline_score = getattr(context, "baseline_score", None)
    baseline_risk_score = getattr(context, "baseline_risk_score", None)
    baseline_at = getattr(context, "baseline_published_at", None)
    baseline_completeness = getattr(context, "baseline_data_completeness", None)
    current_updated_at = _updated_at(context)
    if (
        completeness == "insufficient"
        or baseline_completeness in (None, "insufficient")
        or not isinstance(score, int)
        or not isinstance(baseline_score, int)
    ):
        return WatchlistRecentChangeResult(baseline_at=baseline_at, current_updated_at=current_updated_at)
    return WatchlistRecentChangeResult(
        status="available",
        score_change=score - baseline_score,
        risk_score_change=risk_score - baseline_risk_score if isinstance(baseline_risk_score, int) else None,
        baseline_at=baseline_at,
        current_updated_at=current_updated_at,
    )


def _portfolio_overview(insights: list[WatchlistStockInsightResult]):
    total = len(insights)
    insufficient = sum(item.data_completeness == "insufficient" for item in insights)
    high_risk = sum(item.risk_score >= 45 and item.data_completeness != "insufficient" for item in insights)
    if not total or insufficient == total:
        risk = WatchlistRiskOverviewResult(total_count=total, insufficient_count=insufficient)
    else:
        ratio = high_risk / total
        level: PortfolioRiskLevel = "high" if ratio >= 0.5 else "medium" if high_risk else "low"
        risk = WatchlistRiskOverviewResult(
            status="available", level=level, total_count=total,
            high_risk_count=high_risk, insufficient_count=insufficient,
        )

    counts: dict[str, int] = {}
    for item in insights:
        if item.industry:
            counts[item.industry] = counts.get(item.industry, 0) + 1
    if not counts or not total:
        concentration = WatchlistIndustryConcentrationResult()
    else:
        industry, count = max(counts.items(), key=lambda entry: (entry[1], entry[0]))
        ratio = round(count / total, 4)
        concentration = WatchlistIndustryConcentrationResult(
            status="available", top_industry=industry, top_industry_count=count,
            top_industry_ratio=ratio, is_concentrated=ratio >= 0.5,
        )
    return risk, concentration


def _focus_for(summary, completeness: str, risk_score: int, priority_score: int) -> tuple[WatchlistFocusLevel, str, str]:
    reference_status = getattr(summary, "reference_status", "watch")
    if completeness == "insufficient":
        return "insufficient_data", "数据不足", "关键数据不足，相关结论只能弱参考。"
    if reference_status == "cautious" or risk_score >= 45:
        return "cautious", "谨慎关注", "风险因素较多，适合先查看风险解释和数据来源。"
    if reference_status == "positive" and priority_score >= 35:
        return "priority", "重点观察", "支撑因素相对更集中，可优先查看详情页确认依据。"
    return "watch", "继续观察", "当前适合保持观察，结合后续数据变化再复查。"


def _build_observations(insights: list[WatchlistStockInsightResult]) -> list[WatchlistObservationResult]:
    observations: list[WatchlistObservationResult] = []
    priority = [item.code for item in insights if item.focus_level == "priority"][:3]
    cautious = [item.code for item in insights if item.focus_level == "cautious"][:3]
    insufficient = [item.code for item in insights if item.focus_level == "insufficient_data"][:3]

    if priority:
        observations.append(WatchlistObservationResult(
            type="priority",
            title="优先复查重点观察股",
            description="这些自选股的支撑因素相对更集中，建议先查看详情页确认依据。",
            stock_codes=priority,
        ))
    if cautious:
        observations.append(WatchlistObservationResult(
            type="risk",
            title="先看风险较多的自选股",
            description="这些自选股存在较多风险因素，适合优先查看风险解释。",
            stock_codes=cautious,
        ))
    if insufficient:
        observations.append(WatchlistObservationResult(
            type="data_quality",
            title="补充数据不足的自选股",
            description="这些自选股关键数据不足，相关判断已降级为弱参考。",
            stock_codes=insufficient,
        ))
    if not observations:
        observations.append(WatchlistObservationResult(
            type="balanced",
            title="保持定期复查",
            description="当前自选股未出现集中风险或明显数据缺口，可按详情页逐只复查。",
            stock_codes=[],
        ))
    return observations


def build_watchlist_intelligence(stock_contexts) -> WatchlistIntelligenceResult:
    insights: list[WatchlistStockInsightResult] = []
    scores: list[int] = []

    for context in stock_contexts or []:
        stock = getattr(context, "stock", None)
        summary = getattr(context, "summary", None)
        if stock is None or summary is None:
            continue

        support_points = _as_list(getattr(context, "support_factors", None))
        if not support_points:
            primary_support = getattr(summary, "primary_support", None)
            support_points = _as_list([primary_support] if primary_support else [])

        risk_points = _as_list(getattr(context, "risk_factors", None))
        if not risk_points:
            primary_risk = getattr(summary, "primary_risk", None)
            risk_points = _as_list([primary_risk] if primary_risk else [])

        score = getattr(summary, "score", None)
        if isinstance(score, int):
            scores.append(score)

        completeness = _data_completeness(context)
        risk_score = _risk_score(risk_points, completeness, score)
        priority_score = _priority_score(support_points, risk_score, score, completeness)
        focus_level, focus_label, focus_reason = _focus_for(summary, completeness, risk_score, priority_score)

        insights.append(WatchlistStockInsightResult(
            code=getattr(stock, "code", getattr(summary, "code", "")),
            name=getattr(stock, "name", getattr(summary, "name", "")),
            focus_level=focus_level,
            focus_label=focus_label,
            focus_reason=focus_reason,
            support_points=support_points[:3],
            risk_points=risk_points[:3],
            data_completeness=completeness,
            score=score,
            risk_score=risk_score,
            priority_score=priority_score,
            updated_at=_updated_at(context),
            industry=getattr(stock, "industry", None) or None,
            recent_change=_recent_change(context, score, risk_score, completeness),
        ))

    insights = sort_watchlist_insights(insights, "overall")
    priority_count = sum(1 for item in insights if item.focus_level == "priority")
    cautious_count = sum(1 for item in insights if item.focus_level == "cautious")
    insufficient_count = sum(1 for item in insights if item.focus_level == "insufficient_data")
    average_score = round(sum(scores) / len(scores), 1) if scores else None

    if insufficient_count:
        summary = f"今日自选股中有 {insufficient_count} 只数据不足，建议先补充数据后再观察。"
    elif cautious_count:
        summary = f"今日自选股中有 {cautious_count} 只风险较多，适合优先查看风险解释。"
    elif priority_count:
        summary = f"今日自选股中有 {priority_count} 只可重点观察，仍需结合详情页依据。"
    else:
        summary = "今日自选股整体适合继续观察，暂未出现集中风险或明显机会。"

    risk_overview, industry_concentration = _portfolio_overview(insights)
    return WatchlistIntelligenceResult(
        radar=WatchlistRadarResult(
            title="自选股机会雷达",
            summary=summary,
            priority_count=priority_count,
            cautious_count=cautious_count,
            insufficient_count=insufficient_count,
            average_score=average_score,
        ),
        observations=_build_observations(insights),
        insights=insights,
        risk_overview=risk_overview,
        industry_concentration=industry_concentration,
    )


def sort_watchlist_insights(insights, mode: WatchlistSortMode) -> list[WatchlistStockInsightResult]:
    items = list(insights or [])
    if mode == "risk":
        return sorted(
            items,
            key=lambda item: (item.focus_level != "insufficient_data", item.risk_score, item.priority_score),
            reverse=True,
        )
    if mode == "data_health":
        order = {"insufficient": 0, "incomplete": 1, "mostly_complete": 2, "complete": 3}
        return sorted(items, key=lambda item: (order.get(item.data_completeness, 1), -item.priority_score))
    if mode == "recent_change":
        return sorted(
            items,
            key=lambda item: (
                item.recent_change.status == "available",
                abs(item.recent_change.score_change or 0),
                item.updated_at or datetime.min,
            ),
            reverse=True,
        )
    return sorted(items, key=lambda item: (item.priority_score, -item.risk_score), reverse=True)
