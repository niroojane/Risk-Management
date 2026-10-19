import { apiClient } from './api';
import type {
  AccountPnLView,
  AnalyticsPayload,
  BacktestResult,
  BetaView,
  CalendarView,
  ConstraintSign,
  CorrelationView,
  HoldingsView,
  MarketDriversView,
  Objective,
  OptimizeResult,
  OverlayRow,
  PCAView,
  PerformanceView,
  PnLAnalysisView,
  PositioningView,
  RebalancingFrequency,
  ReturnAnalysisView,
  RiskContributionView,
  RiskTrajectoryView,
  StressPreview,
  TrackingErrorView,
  UploadResult,
  VaRHistoryView,
  VaRMethod,
  VaRResult,
  ViewResponse,
  WeightConstraint,
  Weights,
  WorkspacePayload,
} from '@/types/workspace';

/** Rolling / simulation views can take minutes, like the notebook */
const LONG_REQUEST = { timeout: 15 * 60 * 1000 };

const post = async <T>(url: string, body: unknown, params?: object): Promise<ViewResponse<T>> => {
  const response = await apiClient.post(`/api/v1${url}`, body, { ...LONG_REQUEST, params });
  return response.data;
};

const get = async <T>(url: string, params?: object): Promise<ViewResponse<T>> => {
  const response = await apiClient.get(`/api/v1${url}`, { ...LONG_REQUEST, params });
  return response.data;
};

export interface OptimizeParams extends AnalyticsPayload {
  objectives: Objective[];
  constraints: WeightConstraint[];
  risk_constraints?: Record<string, { sign: ConstraintSign; limit: number }> | null;
  benchmark?: Weights | null;
  benchmark_frequency?: RebalancingFrequency | null;
}

export interface BacktestParams extends AnalyticsPayload {
  objective: Objective;
  overlays: OverlayRow[];
  frequency: RebalancingFrequency;
  constraints: WeightConstraint[];
  risk_constraints?: Record<string, { sign: ConstraintSign; limit: number }> | null;
  benchmark?: Weights | null;
}

export interface VaRParams extends AnalyticsPayload {
  allocations: Record<string, Weights>;
  var_centile: number;
  iterations: number;
  num_scenarios: number;
  stress_factor: number | number[][];
  mean_shock: number | Weights;
  horizon_days: number;
  theta: number;
}

export const workspaceService = {
  // Strategy
  optimize: async (params: OptimizeParams): Promise<OptimizeResult> => {
    const response = await apiClient.post('/api/v1/strategy/optimize', params, LONG_REQUEST);
    return response.data.data;
  },
  backtest: (params: BacktestParams) => post<BacktestResult>('/strategy/backtest', params),

  // Portfolio series
  performance: (
    params: WorkspacePayload & {
      benchmark?: string | null;
      vol_window: number;
      constraints: WeightConstraint[];
    }
  ) => post<PerformanceView>('/portfolio/performance', params),
  calendar: (
    params: WorkspacePayload & { fund: string; benchmark: string; period: 'Year' | 'Month' }
  ) => post<CalendarView>('/portfolio/calendar', params),
  returnAnalysis: (params: WorkspacePayload & { fund: string; benchmark: string }) =>
    post<ReturnAnalysisView>('/portfolio/return-analysis', params),
  beta: (params: WorkspacePayload & { fund: string; benchmark: string; window: number }) =>
    post<BetaView>('/portfolio/beta', params),
  pnlAnalysis: (params: WorkspacePayload) =>
    post<PnLAnalysisView>('/portfolio/pnl-analysis', params),

  // Risk
  riskContribution: (
    params: AnalyticsPayload & {
      allocations: Record<string, Weights>;
      fund: string;
      benchmark: string;
      frequency: RebalancingFrequency;
    }
  ) => post<RiskContributionView>('/risk/contribution', params),
  riskTrajectory: (params: WorkspacePayload & { selected: string; window: number }) =>
    post<RiskTrajectoryView>('/risk/trajectory', params),
  trackingError: (
    params: WorkspacePayload & { selected: string; benchmark: string; window: number }
  ) => post<TrackingErrorView>('/risk/tracking-error', params),
  varHistory: (
    params: WorkspacePayload & {
      selected: string;
      method: VaRMethod;
      window: number;
      var_centile: number;
      iterations: number;
      stress_factor: number;
      mean_factor: number;
    }
  ) => post<VaRHistoryView>('/risk/var-history', params),
  stressPreview: (
    params: AnalyticsPayload & { stress_factor: number | number[][]; mean_shock: number | Weights }
  ) => post<StressPreview>('/risk/stress-preview', params),
  valueAtRisk: async (params: VaRParams): Promise<VaRResult> => {
    const response = await apiClient.post('/api/v1/metrics/var', params, LONG_REQUEST);
    return response.data.data;
  },

  // Market risk
  pca: (
    params: AnalyticsPayload & { num_components: number; component: string; num_closest: number }
  ) => post<PCAView>('/market-risk/pca-analysis', params),
  correlation: (params: AnalyticsPayload & { asset1: string; asset2: string; window: number }) =>
    post<CorrelationView>('/market-risk/correlation-analysis', params),
  marketDrivers: (
    params: WorkspacePayload & {
      eigen_frequency: RebalancingFrequency;
      component: string;
      window: number;
    }
  ) => post<MarketDriversView>('/market-risk/drivers', params),

  // Account (`fresh` skips the backend cache: live balances / prices, like the notebook)
  holdings: (fresh = false) =>
    get<HoldingsView>('/account/holdings', fresh ? { use_cache: false } : undefined),
  positioning: (modelWeights: Weights, fresh = false) =>
    post<PositioningView>(
      '/account/positioning',
      { model_weights: modelWeights },
      fresh ? { use_cache: false } : undefined
    ),
  accountPnl: (fresh = false) =>
    get<AccountPnLView>('/account/pnl', fresh ? { use_cache: false } : undefined),
  upload: () => post<UploadResult>('/account/upload', {}),
};
