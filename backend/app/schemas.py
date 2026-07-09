from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Signal = Literal["neutral", "buy", "sell"]
ReferenceStatus = Literal["positive", "watch", "cautious", "insufficient_data"]
DataCompleteness = Literal["complete", "mostly_complete", "incomplete", "insufficient"]
RiskLevel = Literal["low", "medium", "high"]
RiskType = Literal["valuation", "volatility", "fundamentals", "holder_change", "dividend", "data_quality"]
ChecklistMode = Literal["buy", "sell"]
ChecklistStatus = Literal["pass", "attention", "user_confirm", "insufficient_data"]
WatchlistFocusLevel = Literal["priority", "watch", "cautious", "insufficient_data"]
WatchlistSortMode = Literal["overall", "risk", "data_health", "recent_change"]
ObservationType = Literal["priority", "risk", "data_quality", "refresh", "balanced"]
TradeAction = Literal["buy", "sell"]
StrategyTemplate = Literal["trend-breakout", "low-valuation-reversal", "dividend-defense"]

class StockSummary(BaseModel):
    code: str
    name: str
    price: float
    change_percent: float
    score: int = Field(ge=0, le=100)
    signal: Signal
    reference_status: ReferenceStatus = "watch"
    reference_label: str = "中性观察"
    primary_support: str = "暂无明确支持因素，适合继续观察。"
    primary_risk: str = "仍需结合估值、波动和数据完整度判断。"
    data_completeness: DataCompleteness = "incomplete"
    data_updated_at: datetime | None = None


class FactorScore(BaseModel):
    key: str
    label: str
    value: int = Field(ge=0, le=100)
    description: str


class StrategyResult(BaseModel):
    id: str
    name: str
    period: str
    return_rate: float
    max_drawdown: float
    win_rate: float
    risk: RiskLevel
    summary: str


class BacktestTrade(BaseModel):
    date: str
    action: TradeAction
    price: float
    quantity: int
    reason: str


class StrategyDetail(BaseModel):
    strategy: StrategyResult
    annualized_return: float
    sharpe_ratio: float
    trade_count: int
    rules: list[str]
    trades: list[BacktestTrade]


class BacktestRequest(BaseModel):
    code: str
    name: str = "Custom Strategy"
    template: StrategyTemplate = "trend-breakout"
    lookback_days: int = Field(default=180, ge=30, le=720)
    risk: RiskLevel = "medium"


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    role: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UpdateUserRequest(BaseModel):
    is_active: bool | None = None
    role: str | None = None


class LoginResponse(BaseModel):
    token: str
    username: str
    user_id: int
    role: str
    is_active: bool


class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


class PasswordStrengthResponse(BaseModel):
    valid: bool
    score: int
    messages: list[str]


class AlertItem(BaseModel):
    level: RiskLevel
    title: str
    message: str


class PricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class DataHealth(BaseModel):
    completeness: DataCompleteness = "incomplete"
    updated_at: datetime | None = None
    source_summary: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    downgrade_reasons: list[str] = Field(default_factory=list)
    user_message: str = "当前数据不完整，结论只能弱参考。"


class RiskExplanation(BaseModel):
    type: RiskType
    level: RiskLevel
    title: str
    what_it_means: str
    why_it_matters: str
    evidence: list[str] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    key: str
    label: str
    status: ChecklistStatus
    explanation: str
    user_confirm_required: bool = False


class PreTradeChecklist(BaseModel):
    mode: ChecklistMode
    title: str
    completion_hint: str
    items: list[ChecklistItem] = Field(default_factory=list)


class WatchlistDataHealthOverview(BaseModel):
    total: int = 0
    insufficient_count: int = 0
    incomplete_count: int = 0
    latest_updated_at: datetime | None = None
    message: str = "当前自选股数据健康状况可用于基础参考。"


class WatchlistStockInsight(BaseModel):
    code: str
    name: str
    focus_level: WatchlistFocusLevel
    focus_label: str
    focus_reason: str
    support_points: list[str] = Field(default_factory=list)
    risk_points: list[str] = Field(default_factory=list)
    data_completeness: DataCompleteness = "incomplete"
    score: int | None = None
    risk_score: int = 0
    priority_score: int = 0
    updated_at: datetime | None = None


class WatchlistRadar(BaseModel):
    title: str = "自选股机会雷达"
    summary: str = "当前自选股适合继续观察。"
    priority_count: int = 0
    cautious_count: int = 0
    insufficient_count: int = 0
    average_score: float | None = None


class WatchlistObservation(BaseModel):
    type: ObservationType
    title: str
    description: str
    stock_codes: list[str] = Field(default_factory=list)


class WatchlistIntelligence(BaseModel):
    radar: WatchlistRadar
    observations: list[WatchlistObservation] = Field(default_factory=list)
    insights: list[WatchlistStockInsight] = Field(default_factory=list)
    sort_modes: list[WatchlistSortMode] = Field(default_factory=lambda: ["overall", "risk", "data_health", "recent_change"])


class StockDetail(BaseModel):
    stock: StockSummary
    factors: list[FactorScore]
    strategies: list[StrategyResult]
    alerts: list[AlertItem]
    history: list[PricePoint]
    ai_summary: str | None = None
    data_status: str
    updated_at: datetime | None = None
    ordinary_summary: str = ""
    support_factors: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    data_completeness: DataCompleteness = "incomplete"
    data_updated_at: datetime | None = None
    disclaimer: str = "仅供学习和分析参考，不构成投资建议。"
    data_health: DataHealth | None = None
    risk_explanations: list[RiskExplanation] = Field(default_factory=list)
    buy_checklist: PreTradeChecklist | None = None
    sell_checklist: PreTradeChecklist | None = None


class WatchlistInsights(BaseModel):
    total: int
    groups: dict[ReferenceStatus, list[StockSummary]]
    risk_overview: str
    data_updated_at: datetime | None = None
    disclaimer: str = "仅供学习和分析参考，不构成投资建议。"
    data_health_overview: WatchlistDataHealthOverview | None = None
    intelligence: WatchlistIntelligence | None = None
