export type Signal = 'neutral' | 'buy' | 'sell';
export type RiskLevel = 'low' | 'medium' | 'high';
export type StrategyTemplate = 'trend-breakout' | 'low-valuation-reversal' | 'dividend-defense';

export interface StockSummary {
  code: string;
  name: string;
  price: number;
  change_percent: number;
  score: number;
  signal: Signal;
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

export interface StockDetail {
  stock: StockSummary;
  factors: FactorScore[];
  strategies: StrategyResult[];
  alerts: AlertItem[];
  history: PricePoint[];
  ai_summary: string;
  data_status: string;
  updated_at: string;
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
  user_id: string;
  expires_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
}
