import { useMemo } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { useProfile } from '@/hooks/useProfile';
import type { RangeKey } from '@/store/workspaceStore';
import type {
  RebalancingFrequency,
  ViewResponse,
  Weights,
  WorkspacePayload,
} from '@/types/workspace';

export const HISTORICAL = 'Historical Portfolio';

/** Benchmark series of the market ('Bitcoin' / BTCUSDT, 'Benchmark' / ^GSPC) */
export const useBenchmark = () => {
  const { benchmark_label, benchmark_ticker } = useProfile();
  return { label: benchmark_label, ticker: benchmark_ticker };
};

/** Allocation grid as {name: weights} */
export const useAllocationMap = (): Record<string, Weights> => {
  const allocations = useWorkspaceStore((s) => s.allocations);
  return useMemo(
    () => Object.fromEntries(allocations.map((row) => [row.name, row.weights])),
    [allocations]
  );
};

/**
 * Names of the series the backend builds, in its order: Historical Portfolio,
 * Fund / Core / Overlay, 'Rebalanced X' / 'Buy and Hold X' per allocation, the benchmark.
 */
export const useSeriesNames = (includeHistorical: boolean): string[] => {
  const allocations = useWorkspaceStore((s) => s.allocations);
  const backtest = useWorkspaceStore((s) => s.backtest);
  const universe = useWorkspaceStore((s) => s.universe);
  const benchmark = useBenchmark();
  return useMemo(() => {
    const names: string[] = includeHistorical ? [HISTORICAL] : [];
    if (backtest) names.push(...Object.keys(backtest.schedules));
    for (const row of allocations) names.push(`Rebalanced ${row.name}`, `Buy and Hold ${row.name}`);
    if (universe?.symbols.includes(benchmark.ticker)) names.push(benchmark.label);
    return names;
  }, [includeHistorical, allocations, backtest, universe, benchmark.ticker, benchmark.label]);
};

/** Payload of the workspace views for a date range, or null until prices are loaded */
export const useWorkspacePayload = (
  rangeKey: RangeKey,
  frequency: RebalancingFrequency,
  includeHistorical: boolean
): WorkspacePayload | null => {
  const universe = useWorkspaceStore((s) => s.universe);
  const range = useWorkspaceStore((s) => s.ranges[rangeKey]);
  const backtest = useWorkspaceStore((s) => s.backtest);
  const allocations = useAllocationMap();

  return useMemo(() => {
    if (!universe) return null;
    return {
      symbols: universe.symbols,
      history_start: universe.start,
      start_date: range.start < universe.start ? universe.start : range.start,
      end_date: range.end,
      allocations,
      frequency,
      strategies: backtest?.schedules ?? {},
      include_bitcoin: true,
      include_historical: includeHistorical,
    };
  }, [universe, range, backtest, allocations, frequency, includeHistorical]);
};

/** Readable message from an API error (message + detail of the backend's error body) */
export const apiErrorMessage = (error: unknown): string => {
  if (error instanceof AxiosError) {
    const body = error.response?.data;
    if (body?.message) {
      const detail = typeof body.detail === 'string' ? body.detail : '';
      return detail && detail !== body.message ? `${body.message} — ${detail}` : body.message;
    }
    if (Array.isArray(body?.detail)) return JSON.stringify(body.detail);
    return error.message;
  }
  return error instanceof Error ? error.message : 'An unexpected error occurred';
};

/**
 * Button-driven view, like the notebook's 'Refresh' / 'Get ...' buttons: nothing runs
 * until `run()`, results are cached per parameters and kept on screen when the
 * parameters change (`stale` tells they no longer match).
 */
export const useView = <P, T>(
  key: string,
  params: P | null,
  fetcher: (params: P) => Promise<ViewResponse<T>>,
  /** Fetch on its own whenever the parameters change (for quick views) */
  auto = false
) => {
  const query = useQuery({
    queryKey: ['view', key, params],
    queryFn: () => fetcher(params as P),
    enabled: auto && params !== null,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
    gcTime: 60 * 60 * 1000,
    retry: false,
  });

  return {
    data: query.data?.data,
    warnings: query.data?.warnings ?? [],
    isFetching: query.isFetching,
    error: query.error ? apiErrorMessage(query.error) : null,
    stale: query.isPlaceholderData && !!query.data,
    run: () => {
      if (params) void query.refetch();
    },
  };
};
