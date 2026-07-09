export type Signal = 'neutral' | 'buy' | 'sell';
export type ReferenceStatus = 'positive' | 'watch' | 'cautious' | 'insufficient_data';
export type DataCompleteness = 'complete' | 'mostly_complete' | 'incomplete' | 'insufficient';
export type RiskLevel = 'low' | 'medium' | 'high';
export type RiskType = 'valuation' | 'volatility' | 'fundamentals' | 'holder_change' | 'dividend' | 'data_quality';
export type ChecklistMode = 'buy' | 'sell';
export type ChecklistStatus = 'pass' | 'attention' | 'user_confirm' | 'insufficient_data';
export type WatchlistFocusLevel = 'priority' | 'watch' | 'cautious' | 'insufficient_data';
export type WatchlistSortMode = 'overall' | 'risk' | 'data_health' | 'recent_change';
export type ObservationType = 'priority' | 'risk' | 'data_quality' | 'refresh' | 'balanced';
export type StrategyTemplate = 'trend-breakout' | 'low-valuation-reversal' | 'dividend-defense';

export interface StockSummary {
  code: string;
  name: string;
  price: number;
  change_percent: number;
  score: number;
  signal: Signal;
  reference_status?: ReferenceStatus;
  reference_label?: string;
  primary_support?: string;
  primary_risk?: string;
  data_completeness?: DataCompleteness;
  data_updated_at?: string | null;
}

export interface FactorScore {
  key: string;
  label: string;
  value: number;
  description: string;
}

export interface StrategyResult {
  id: string;
  name: string;
  period: string;
  return_rate: number;
  max_drawdown: number;
  win_rate: number;
  risk: RiskLevel;
  summary: string;
}

export interface BacktestTrade {
  date: string;
  action: 'buy' | 'sell';
  price: number;
  quantity: number;
  reason: string;
}

export interface StrategyDetail {
  strategy: StrategyResult;
  annualized_return: number;
  sharpe_ratio: number;
  trade_count: number;
  rules: string[];
  trades: BacktestTrade[];
}

export interface AlertItem {
  level: RiskLevel;
  title: string;
  message: string;
}

export interface PricePoint {
  date: string;
  close: number;
  volume: number;
}

export interface DataHealth {
  completeness: DataCompleteness;
  updated_at?: string | null;
  source_summary: string[];
  missing_items: string[];
  downgrade_reasons: string[];
  user_message: string;
}

export interface RiskExplanation {
  type: RiskType;
  level: RiskLevel;
  title: string;
  what_it_means: string;
  why_it_matters: string;
  evidence: string[];
}

export interface ChecklistItem {
  key: string;
  label: string;
  status: ChecklistStatus;
  explanation: string;
  user_confirm_required: boolean;
}

export interface PreTradeChecklist {
  mode: ChecklistMode;
  title: string;
  completion_hint: string;
  items: ChecklistItem[];
}

export interface StockDetail {
  stock: StockSummary;
  factors: FactorScore[];
  strategies: StrategyResult[];
  alerts: AlertItem[];
  history: PricePoint[];
  ai_summary: string;
  data_status: string;
  updated_at: string;
  ordinary_summary?: string;
  support_factors?: string[];
  risk_factors?: string[];
  data_completeness?: DataCompleteness;
  data_updated_at?: string | null;
  disclaimer?: string;
  data_health?: DataHealth | null;
  risk_explanations?: RiskExplanation[];
  buy_checklist?: PreTradeChecklist | null;
  sell_checklist?: PreTradeChecklist | null;
}

export interface WatchlistDataHealthOverview {
  total: number;
  insufficient_count: number;
  incomplete_count: number;
  latest_updated_at?: string | null;
  message: string;
}

export interface WatchlistStockInsight {
  code: string;
  name: string;
  focus_level: WatchlistFocusLevel;
  focus_label: string;
  focus_reason: string;
  support_points: string[];
  risk_points: string[];
  data_completeness: DataCompleteness;
  score?: number | null;
  risk_score: number;
  priority_score: number;
  updated_at?: string | null;
}

export interface WatchlistRadar {
  title: string;
  summary: string;
  priority_count: number;
  cautious_count: number;
  insufficient_count: number;
  average_score?: number | null;
}

export interface WatchlistObservation {
  type: ObservationType;
  title: string;
  description: string;
  stock_codes: string[];
}

export interface WatchlistIntelligence {
  radar: WatchlistRadar;
  observations: WatchlistObservation[];
  insights: WatchlistStockInsight[];
  sort_modes: WatchlistSortMode[];
}

export interface WatchlistInsights {
  total: number;
  groups: Record<ReferenceStatus, StockSummary[]>;
  risk_overview: string;
  data_updated_at?: string | null;
  disclaimer: string;
  data_health_overview?: WatchlistDataHealthOverview | null;
  intelligence?: WatchlistIntelligence | null;
}

export interface ResearchSnapshot {
  stockName?: string;
  stockCode?: string;
  score: number;
  alertCount: number;
  averageWinRate: number;
  aiSummary?: string | null;
  dataStatus?: string;
}

export interface DividendRecord {
  ts_code: string;
  div_proc: string;
  ann_date: string;
  record_date: string;
  ex_date: string;
  pay_date: string;
  div_cash: number;
  bonus_share: number;
  transfer_share: number;
}

export interface StockNews {
  ts_code: string;
  title: string;
  content: string;
  pub_time: string;
  source: string;
}

export interface InstHoldRecord {
  ts_code: string;
  trade_date: string;
  inst_type: string;
  hold_amount: number;
  hold_ratio: number;
  change_amount: number;
  change_ratio: number;
}

export interface BacktestRequest {
  code: string;
  name: string;
  template: StrategyTemplate;
  lookback_days: number;
  risk: RiskLevel;
}

export interface LoginResponse {
  token: string;
  username: string;
  user_id: number;
  role: 'admin' | 'user';
  is_active: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
}

export interface AppUser {
  id: number;
  username: string;
  is_active: boolean;
  role: 'admin' | 'user';
  created_at?: string | null;
  updated_at?: string | null;
}
