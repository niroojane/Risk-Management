import { workspaceService } from '@/services/workspaceService';
import type { OptimizeParams } from '@/services/workspaceService';
import type { AllocationRow, DateRange, LoadedUniverse } from '@/store/workspaceStore';
import type {
  ConstraintSign,
  Objective,
  RebalancingFrequency,
  RiskConstraintRow,
  RiskType,
  WeightConstraint,
  Weights,
} from '@/types/workspace';

export const STRATEGY_OPTIONS: { value: Objective; label: string }[] = [
  { value: 'minimum_variance', label: 'Minimum Variance' },
  { value: 'risk_parity', label: 'Risk Parity' },
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { value: 'maximum_diversification', label: 'Maximum Diversification' },
  { value: 'eigenportfolio', label: 'Eigen Strategy' },
  { value: 'tracking_error', label: 'Minimum Tracking Error' },
  { value: 'information_ratio', label: 'Maximum Information Ratio' },
];
export const strategyLabel = (objective: Objective) =>
  STRATEGY_OPTIONS.find((o) => o.value === objective)?.label ?? objective;

export const RELATIVE: Objective[] = ['tracking_error', 'information_ratio'];

export const RISK_OPTIONS: { value: RiskType; label: string }[] = [
  { value: 'beta', label: 'Beta' },
  { value: 'volatility', label: 'Volatility' },
  { value: 'tracking_error', label: 'Tracking Error' },
  { value: 'information_ratio', label: 'Information Ratio' },
];
export const riskLabel = (risk: RiskType) =>
  RISK_OPTIONS.find((o) => o.value === risk)?.label ?? risk;

export const SIGN_OPTIONS: { value: ConstraintSign; label: string }[] = [
  { value: '=', label: '=' },
  { value: '>=', label: '≥' },
  { value: '<=', label: '≤' },
];
export const signLabel = (sign: ConstraintSign) =>
  SIGN_OPTIONS.find((o) => o.value === sign)!.label;

export const FREQUENCIES: RebalancingFrequency[] = ['Monthly', 'Quarterly', 'Yearly'];

/** Absolute objectives and the grid names of their unconstrained / constrained versions */
const GRID_NAMES: [Objective, string, string][] = [
  ['sharpe_ratio', 'Optimal Portfolio', 'Constrained Optimal Portfolio'],
  ['minimum_variance', 'Min Variance', 'Constrained Min Var'],
  ['maximum_diversification', 'Max Diversification', 'Max Diversification Constrained'],
  ['risk_parity', 'Risk Parity', 'Constrained RP'],
  ['eigenportfolio', 'Eigen Portfolio', 'Eigen Portfolio Constrained'],
];
const RELATIVE_NAMES: [Objective, string][] = [
  ['tracking_error', 'Min Tracking Error'],
  ['information_ratio', 'Max Information Ratio'],
];

const round4 = (weights: Weights): Weights =>
  Object.fromEntries(Object.entries(weights).map(([s, w]) => [s, Math.round(w * 1e4) / 1e4]));

/** Risk constraints in the API format (one per risk type) */
export const riskPayload = (rows: RiskConstraintRow[]) =>
  rows.length
    ? Object.fromEntries(rows.map((r) => [r.risk, { sign: r.sign, limit: r.limit }]))
    : null;

export interface OptimizeInput {
  universe: LoadedUniverse;
  range: DateRange;
  constraints: WeightConstraint[];
  riskConstraints: RiskConstraintRow[];
  allocations: AllocationRow[];
  benchmark: string | null;
  frequency: RebalancingFrequency;
}

/** 'Optimize Portfolio': the notebook's allocation grid */
export const optimizeGrid = async (input: OptimizeInput) => {
  const { universe, range, constraints, riskConstraints, allocations, benchmark, frequency } =
    input;
  const base = { symbols: universe.symbols, start_date: range.start, end_date: range.end };
  const benchWeights = allocations.find((a) => a.name === benchmark)?.weights ?? null;
  const messages: string[] = [];

  // Risk constraints are measured against the benchmark allocation
  const risk = benchWeights ? riskPayload(riskConstraints) : null;
  if (riskConstraints.length && !benchWeights) {
    messages.push('⚠️ Skipping risk constraints: no benchmark allocation selected yet.');
  }
  const constrained = constraints.length > 0 || !!risk;
  const absolute = GRID_NAMES.map(([objective]) => objective);
  const withConstraints: Partial<OptimizeParams> = {
    constraints,
    risk_constraints: risk,
    benchmark: benchWeights,
    benchmark_frequency: frequency,
  };

  const calls = [
    workspaceService.optimize({ ...base, objectives: absolute, constraints: [] }),
    constrained
      ? workspaceService.optimize({
          ...base,
          objectives: absolute,
          ...withConstraints,
        } as OptimizeParams)
      : null,
    benchWeights
      ? workspaceService.optimize({
          ...base,
          objectives: RELATIVE,
          constraints: [],
          benchmark: benchWeights,
        })
      : null,
    benchWeights && constrained
      ? workspaceService.optimize({
          ...base,
          objectives: RELATIVE,
          ...withConstraints,
        } as OptimizeParams)
      : null,
  ];
  const [free, bounded, relative, relativeBounded] = await Promise.all(calls);

  const rows: AllocationRow[] = [];
  for (const [objective, name, constrainedName] of GRID_NAMES) {
    rows.push({ name, weights: round4(free!.allocations[objective]) });
    rows.push({
      name: constrainedName,
      weights: round4((bounded ?? free)!.allocations[objective]),
    });
  }
  rows.push({ name: 'Equal Weighted', weights: round4(free!.allocations.equal_weight) });

  if (relative) {
    for (const [objective, name] of RELATIVE_NAMES) {
      rows.push({ name, weights: round4(relative.allocations[objective]) });
      rows.push({
        name: `${name} Constrained`,
        weights: round4((relativeBounded ?? relative).allocations[objective]),
      });
    }
  } else {
    messages.push(
      "ℹ️ Min Tracking Error / Max Information Ratio need a benchmark allocation: select it in 'Benchmark' and click Optimize again."
    );
  }

  // The real portfolio's weights, when every held asset is in the universe
  try {
    const { weights } = (await workspaceService.holdings()).data;
    if (Object.keys(weights).every((t) => universe.symbols.includes(t))) {
      rows.push({ name: 'Current Weights', weights: round4(weights) });
    }
  } catch {
    // account not reachable
  }

  for (const result of [free, bounded, relative, relativeBounded]) {
    if (result) messages.push(...result.warnings);
  }
  return { rows, messages };
};
