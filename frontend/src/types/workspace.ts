/** A pandas DataFrame in the backend's split layout */
export type Cell = number | string | null;

export interface Frame {
  index: string[];
  columns: string[];
  data: Cell[][];
}

export interface ViewResponse<T> {
  success: boolean;
  data: T;
  warnings?: string[];
  message?: string;
}

export type Weights = Record<string, number>;
/** {date: {symbol: weight}} */
export type Schedule = Record<string, Weights>;

export type ConstraintSign = '=' | '>=' | '<=';
export type RebalancingFrequency = 'Weekly' | 'Monthly' | 'Quarterly' | 'Yearly';
export type Objective =
  | 'minimum_variance'
  | 'sharpe_ratio'
  | 'risk_parity'
  | 'maximum_diversification'
  | 'eigenportfolio'
  | 'tracking_error'
  | 'information_ratio';
export type RiskType = 'beta' | 'volatility' | 'tracking_error' | 'information_ratio';
export type VaRMethod =
  | 'multivariate'
  | 'gaussian_copula'
  | 't_copula'
  | 'gumbel_copula'
  | 'monte_carlo';

export interface WeightConstraint {
  asset: string;
  sign: ConstraintSign;
  limit: number;
}

export interface RiskConstraintRow {
  risk: RiskType;
  sign: ConstraintSign;
  limit: number;
}

export interface OverlayRow {
  objective: Objective;
  limit: number;
}

export interface AnalyticsPayload {
  symbols: string[];
  start_date: string;
  end_date: string;
}

export interface WorkspacePayload extends AnalyticsPayload {
  history_start: string;
  allocations: Record<string, Weights>;
  frequency: RebalancingFrequency;
  strategies: Record<string, Schedule>;
  include_bitcoin: boolean;
  include_historical: boolean;
}

// ---------------------------------------------------------------- view results

export interface BacktestResult {
  schedules: Record<string, Schedule>;
  tables: Record<string, Frame>;
  model: Weights;
  metrics: Frame;
  symbols: string[];
}

export interface PerformanceView {
  levels: Frame;
  drawdown: Frame;
  rolling_volatility: Frame;
  returns_table: Frame;
  risk_table: Frame;
  frontier: { indicators: Frame; frontier: Frame; constrained: Frame | null } | null;
}

export interface CalendarView {
  returns: Frame;
  volatility: Frame;
  tracking_error: Frame;
  sharpe_ratio: Frame;
}

export interface ReturnAnalysisView {
  contribution: Frame;
  benchmark_contribution: Frame;
  active_contribution: Frame;
  drawdown: Frame;
}

export interface BetaView {
  asset_beta: Frame;
  weights: Frame;
  portfolio_beta: Frame;
  beta_contribution: Frame;
}

export interface PnLAnalysisView {
  positions: Frame;
  cumulative_contribution: Frame;
  daily_pnl: Frame;
  cumulative_return: Frame;
  history_start: string;
}

export interface RiskContributionView {
  contribution: Frame;
  excess: Frame;
  ex_ante: Frame;
}

export interface DecompositionView {
  vol_contribution: Frame;
  correlation_contribution: Frame;
  idiosyncratic_contribution: Frame;
}

/** Every series is decomposed, so switching the fund needs no request */
export interface RiskTrajectoryView {
  volatility: Frame;
  decomposition: Record<string, DecompositionView>;
}

export interface TrackingErrorView {
  tracking_error: Frame;
  decomposition: Record<string, DecompositionView>;
}

export interface VaRHistoryView {
  var: Frame;
  cvar: Frame;
  /** Per-asset VaR / CVaR of every series ('Portfolio' = total) */
  contributions: Record<string, { var: Frame; cvar: Frame }>;
}

export interface StressPreview {
  moments: Frame;
  correlation: Frame;
  stressed_correlation: Frame;
}

export interface VaRMethodResult {
  var: number | null;
  cvar: number | null;
  var_contribution?: Record<string, number | null> | null;
  cvar_contribution?: Record<string, number | null> | null;
  histogram?: { counts: number[]; bin_edges: number[] } | null;
}

export type VaRResult = Record<string, { methods: Record<string, VaRMethodResult> }>;

export interface PCAView {
  components: string[];
  component: string;
  variance_explained: Frame;
  eigen_weights: Frame;
  eigen_index: Frame;
  similarity: Frame;
}

export interface CorrelationView {
  rolling_correlation: Frame;
  rolling_mean_returns: Frame;
  first_component: Frame;
  matrix: Frame;
}

export interface MarketDriversView {
  performance: Frame;
  drivers: Frame;
  correlation_contribution: Frame;
  vol_contribution: Frame;
  idiosyncratic_contribution: Frame;
  weights: Frame;
}

export interface HoldingsView {
  holdings: Frame;
  /** Held assets, cash / stablecoins excluded */
  tickers: string[];
  /** Current weights of `tickers` */
  weights: Weights;
  base_currency?: string;
}

export interface UploadResult {
  files: Record<string, string>;
  /** What 'Update Files' added (multi-asset) */
  messages: string[];
}

export interface PositioningView {
  positioning: Frame;
  holdings: Frame;
}

export interface AccountPnLView {
  pnl: Frame;
  trades: Frame;
}

export interface OptimizeResult {
  allocations: Record<string, Weights>;
  metrics: Record<string, Record<string, number | null>>;
  warnings: string[];
}
