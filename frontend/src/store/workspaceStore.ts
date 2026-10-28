import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  BacktestResult,
  OverlayRow,
  StrategyKey,
  RebalancingFrequency,
  RiskConstraintRow,
  WeightConstraint,
  Weights,
} from '@/types/workspace';
import type { UniverseTicker } from '@/types/profile';

/** 'yyyy-MM-dd' bounds */
export interface DateRange {
  start: string;
  end: string;
  /** End date the user set in the past: kept on the next visit, which otherwise moves it to today */
  fixedEnd?: boolean;
}

export interface AllocationRow {
  name: string;
  weights: Weights;
}

/** Prices loaded by 'Get Prices' (the notebook's `dataframe`) */
export interface LoadedUniverse {
  symbols: string[];
  /** Tickers picked in the market-cap scope (the universe also holds the account's assets) */
  selected: string[];
  start: string;
  end: string;
  holdings: string[];
  excluded: string[];
}

export type RangeKey = 'perf' | 'risk' | 'market' | 'expost';

const today = () => new Date().toISOString().slice(0, 10);
const DEFAULT_START = '2020-01-01';
/** The notebook's analysis windows start two months after the backtest start */
const DEFAULT_WINDOW = { start: '2020-03-01', end: today() };

/**
 * End dates moved to today on each visit, as the notebook's date pickers start at today: the
 * loaded universe's ('Get Prices' runs to today, and the backend fetches prices per request)
 * and the analysis windows', except an end date the user set in the past.
 */
const withEndToday = (state: WorkspaceState): WorkspaceState => {
  const end = today();
  const ranges = Object.fromEntries(
    Object.entries(state.ranges).map(([key, range]) => [
      key,
      range.fixedEnd ? range : { ...range, end },
    ])
  ) as Record<RangeKey, DateRange>;
  const universe =
    state.universe && state.universe.end < end ? { ...state.universe, end } : state.universe;
  return { ...state, ranges, universe };
};

interface WorkspaceState {
  // Investment Universe
  nCrypto: number;
  startDate: string;
  unchecked: string[];
  /** Multi-asset universe (null: the profile's default universe) */
  yahooTickers: UniverseTicker[] | null;
  universe: LoadedUniverse | null;
  ranges: Record<RangeKey, DateRange>;

  // Strategy
  objective: StrategyKey;
  frequency: RebalancingFrequency;
  benchmark: string | null;
  volWindow: number;
  constraints: WeightConstraint[];
  overlays: OverlayRow[];
  riskConstraints: RiskConstraintRow[];
  allocations: AllocationRow[];
  optimizedAllocations: AllocationRow[];
  backtest: BacktestResult | null;

  // Current Portfolio / Risk Analysis
  pnlFrequency: RebalancingFrequency;
  historicalEnabled: boolean;

  /** Fund / benchmark picked in each view's dropdowns, kept like the notebook's widgets */
  selections: Record<string, SeriesSelection>;

  setNCrypto: (n: number) => void;
  setStartDate: (date: string) => void;
  toggleTicker: (ticker: string) => void;
  setYahooTickers: (tickers: UniverseTicker[] | null) => void;
  setUniverse: (universe: LoadedUniverse) => void;
  setRange: (key: RangeKey, range: DateRange) => void;
  setStrategy: (
    patch: Partial<Pick<WorkspaceState, 'objective' | 'frequency' | 'benchmark' | 'volWindow'>>
  ) => void;
  addConstraint: (constraint: WeightConstraint) => void;
  clearConstraints: () => void;
  addOverlay: (overlay: OverlayRow) => void;
  clearOverlays: () => void;
  addRiskConstraint: (constraint: RiskConstraintRow) => void;
  clearRiskConstraints: () => void;
  setAllocations: (rows: AllocationRow[], optimized?: boolean) => void;
  resetAllocations: () => void;
  setBacktest: (result: BacktestResult | null) => void;
  setPnlFrequency: (frequency: RebalancingFrequency) => void;
  setHistoricalEnabled: (enabled: boolean) => void;
  setSelection: (key: string, patch: SeriesSelection) => void;
}

export interface SeriesSelection {
  fund?: string;
  benchmark?: string;
  period?: 'Year' | 'Month';
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      nCrypto: 20,
      startDate: DEFAULT_START,
      unchecked: [],
      yahooTickers: null,
      universe: null,
      ranges: {
        perf: DEFAULT_WINDOW,
        risk: DEFAULT_WINDOW,
        market: DEFAULT_WINDOW,
        expost: { start: '2024-01-01', end: today() },
      },

      objective: 'minimum_variance',
      frequency: 'Monthly',
      benchmark: null,
      volWindow: 252,
      constraints: [],
      overlays: [],
      riskConstraints: [],
      allocations: [],
      optimizedAllocations: [],
      backtest: null,

      pnlFrequency: 'Monthly',
      historicalEnabled: false,
      selections: {},

      setNCrypto: (nCrypto) => set({ nCrypto }),
      setStartDate: (startDate) => set({ startDate }),
      toggleTicker: (ticker) =>
        set((state) => ({
          unchecked: state.unchecked.includes(ticker)
            ? state.unchecked.filter((t) => t !== ticker)
            : [...state.unchecked, ticker],
        })),
      setYahooTickers: (yahooTickers) => set({ yahooTickers }),
      // New prices invalidate constraints / overlays / risk limits that may reference dropped tickers
      setUniverse: (universe) =>
        set({ universe, constraints: [], overlays: [], riskConstraints: [] }),
      setRange: (key, range) =>
        set((state) => ({
          ranges: { ...state.ranges, [key]: { ...range, fixedEnd: range.end < today() } },
        })),
      setStrategy: (patch) => set(patch),
      addConstraint: (constraint) =>
        set((state) => ({ constraints: [...state.constraints, constraint] })),
      clearConstraints: () => set({ constraints: [] }),
      addOverlay: (overlay) => set((state) => ({ overlays: [...state.overlays, overlay] })),
      clearOverlays: () => set({ overlays: [] }),
      // One row per risk type: the last one added wins
      addRiskConstraint: (constraint) =>
        set((state) => ({
          riskConstraints: [
            ...state.riskConstraints.filter((c) => c.risk !== constraint.risk),
            constraint,
          ],
        })),
      clearRiskConstraints: () => set({ riskConstraints: [] }),
      setAllocations: (rows, optimized = false) =>
        set(optimized ? { allocations: rows, optimizedAllocations: rows } : { allocations: rows }),
      resetAllocations: () => set((state) => ({ allocations: state.optimizedAllocations })),
      setBacktest: (backtest) => set({ backtest }),
      setPnlFrequency: (pnlFrequency) => set({ pnlFrequency }),
      setHistoricalEnabled: (historicalEnabled) => set({ historicalEnabled }),
      setSelection: (key, patch) =>
        set((state) => ({
          selections: { ...state.selections, [key]: { ...state.selections[key], ...patch } },
        })),
    }),
    {
      name: 'risk-management-workspace',
      version: 3,
      // v1 universes have no `selected` list: load prices again. Before v3 the Yahoo universe
      // was the US ETFs: start again from the profile's default (the UCITS ETFs of the regimes)
      migrate: (persisted, version) => {
        const state = { ...(persisted as WorkspaceState), universe: null };
        return version < 3 ? { ...state, yahooTickers: null, unchecked: [] } : state;
      },
      merge: (persisted, current) =>
        withEndToday({ ...current, ...(persisted as Partial<WorkspaceState>) }),
    }
  )
);
