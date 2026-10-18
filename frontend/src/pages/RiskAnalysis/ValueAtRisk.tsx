import { useMemo, useState } from 'react';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import type { EChartsCoreOption } from 'echarts/core';
import { EChart, PALETTE, chartTheme, formatValue, DataTable } from '@/components/data';
import { Button } from '@/components/ui/button';
import {
  Grid2,
  Notice,
  NumberField,
  Panel,
  RangeFields,
  RunButton,
  SelectField,
  Toolbar,
  ViewStatus,
} from '@/components/ui';
import { apiErrorMessage, useAllocationMap } from '@/hooks/useWorkspace';
import { useSeriesPair } from '@/hooks/useSeriesPair';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { Frame, VaRResult } from '@/types/workspace';
import { RequireAllocations } from '../shared/Guards';
import { StressGrid } from './components/StressGrid';

const METHODS: [string, string][] = [
  ['historical', 'Historical'],
  ['parametric', 'Parametric'],
  ['multivariate', 'Multivariate'],
  ['gaussian_copula', 'Gaussian Copula'],
  ['t_copula', 'T-Student Copula'],
  ['gumbel_copula', 'Gumbel Copula'],
  ['monte_carlo', 'Monte Carlo'],
];
const SIMULATED = METHODS.slice(2);

const diagonal = (n: number, value: number) =>
  Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? value : 0)));

/** {allocation: {method: VaR}} tables */
const summaryTable = (result: VaRResult, key: 'var' | 'cvar'): Frame => {
  const names = Object.keys(result);
  return {
    index: names,
    columns: METHODS.map(([, label]) => label),
    data: names.map((name) =>
      METHODS.map(([method]) => result[name].methods[method]?.[key] ?? null)
    ),
  };
};

/** Per-asset scenario of each simulation method for one allocation */
const contributionTable = (result: VaRResult, fund: string, key: 'var' | 'cvar'): Frame | null => {
  const methods = result[fund]?.methods;
  if (!methods) return null;
  const field = key === 'var' ? 'var_contribution' : 'cvar_contribution';
  const assets = Object.keys(methods[SIMULATED[0][0]]?.[field] ?? {});
  return {
    index: [...assets, 'Portfolio'],
    columns: SIMULATED.map(([, label]) => label),
    data: [
      ...assets.map((asset) => SIMULATED.map(([m]) => methods[m]?.[field]?.[asset] ?? null)),
      SIMULATED.map(([m]) => methods[m]?.[key] ?? null),
    ],
  };
};

/** Risk Analysis > Value at Risk > Value at Risk */
const ValueAtRiskPage = () => {
  const universe = useWorkspaceStore((s) => s.universe)!;
  const range = useWorkspaceStore((s) => s.ranges.risk);
  const allocations = useAllocationMap();
  const names = Object.keys(allocations);
  const { fund, setFund } = useSeriesPair('var', names, 'Optimal Portfolio', '');
  const symbols = universe.symbols;

  const [stressFactor, setStressFactor] = useState(1);
  const [meanFactor, setMeanFactor] = useState(1);
  const [iterations, setIterations] = useState(10000);
  const [scenarios, setScenarios] = useState(10);
  const [centile, setCentile] = useState(0.05);
  const [stressGrid, setStressGrid] = useState(() => diagonal(symbols.length, 1));
  const [meanShock, setMeanShock] = useState<Record<string, number>>(() =>
    Object.fromEntries(symbols.map((s) => [s, 1]))
  );
  const gridMatches = stressGrid.length === symbols.length;

  const resetStress = () => {
    setStressGrid(diagonal(symbols.length, stressFactor));
    setMeanShock(Object.fromEntries(symbols.map((s) => [s, meanFactor])));
  };

  const base = { symbols, start_date: range.start, end_date: range.end };
  const preview = useQuery({
    queryKey: ['stress-preview', base, stressGrid, meanShock],
    queryFn: () =>
      workspaceService.stressPreview({ ...base, stress_factor: stressGrid, mean_shock: meanShock }),
    enabled: gridMatches,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
    retry: false,
  });

  const simulation = useMutation({
    mutationFn: () =>
      workspaceService.valueAtRisk({
        ...base,
        allocations,
        var_centile: centile,
        iterations,
        num_scenarios: scenarios,
        stress_factor: stressGrid,
        mean_shock: meanShock,
        horizon_days: 1,
        theta: 2,
      }),
  });
  const result = simulation.data;

  // Overlaid distributions of the simulated portfolio returns, one per method
  const histogram = useMemo<EChartsCoreOption | null>(() => {
    const methods = result?.[fund]?.methods;
    if (!methods) return null;
    const theme = chartTheme();
    const series = SIMULATED.flatMap(([method, label]) => {
      const bins = methods[method]?.histogram;
      if (!bins) return [];
      const data = bins.counts.map((count, i) => [
        (bins.bin_edges[i] + bins.bin_edges[i + 1]) / 2,
        count,
      ]);
      return [{ name: label, type: 'bar', data, barGap: '-100%', itemStyle: { opacity: 0.55 } }];
    });
    if (series.length === 0) return null;
    return {
      color: PALETTE,
      tooltip: {
        trigger: 'item',
        formatter: (p: { seriesName: string; value: number[] }) =>
          `${p.seriesName}<br/>${formatValue(p.value[0], 'percent')}: ${p.value[1]} scenarios`,
      },
      legend: { bottom: 0, textStyle: { color: theme.text } },
      grid: { left: 56, right: 16, top: 16, bottom: 48 },
      xAxis: {
        type: 'value',
        scale: true,
        axisLabel: { color: theme.muted, formatter: (v: number) => formatValue(v, 'percent') },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: theme.muted },
        splitLine: { lineStyle: { color: theme.grid } },
      },
      series,
    };
  }, [result, fund]);

  return (
    <div className="space-y-6">
      <Panel title="Simulation">
        <Toolbar>
          <RangeFields rangeKey="risk" />
          <SelectField
            label="Fund"
            value={fund}
            options={names}
            onChange={setFund}
            selectClassName="w-60"
          />
          <NumberField
            label="Stress Factor"
            value={stressFactor}
            step={0.1}
            min={1}
            max={3}
            onChange={setStressFactor}
          />
          <NumberField
            label="Mean Factor"
            value={meanFactor}
            step={0.1}
            min={0}
            max={3}
            onChange={setMeanFactor}
          />
          <NumberField
            label="Iterations"
            value={iterations}
            step={1000}
            min={1000}
            max={100000}
            onChange={setIterations}
          />
          <NumberField
            label="Scenarios"
            value={scenarios}
            min={1}
            max={100}
            onChange={setScenarios}
          />
          <NumberField
            label="VaR Centile"
            value={centile}
            step={0.01}
            min={0.01}
            max={0.49}
            onChange={setCentile}
          />
        </Toolbar>
        <Toolbar>
          <RunButton
            onClick={() => simulation.mutate()}
            loading={simulation.isPending}
            disabled={!gridMatches}
          >
            Run Simulation
          </RunButton>
          <Button variant="outline" onClick={resetStress}>
            Refresh
          </Button>
          <span className="text-xs text-muted-foreground">
            “Refresh” resets the grids to the stress and mean factors.
          </span>
        </Toolbar>
        {simulation.error && <Notice tone="error">{apiErrorMessage(simulation.error)}</Notice>}
      </Panel>

      {result && (
        <Panel title="Results">
          <DataTable
            frame={summaryTable(result, 'var')}
            title="Value at Risk (daily)"
            format="percent"
          />
          <DataTable frame={summaryTable(result, 'cvar')} title="CVaR (daily)" format="percent" />
          <Grid2>
            <DataTable
              frame={contributionTable(result, fund, 'var')}
              title={`VaR Results for ${fund}`}
              format="percent"
            />
            <DataTable
              frame={contributionTable(result, fund, 'cvar')}
              title={`CVaR Results for ${fund}`}
              format="percent"
            />
          </Grid2>
          {histogram && <EChart option={histogram} title={`Simulated daily returns — ${fund}`} />}
        </Panel>
      )}

      <Panel title="Stress Scenario">
        {!gridMatches && (
          <Notice>
            The universe changed since the grids were set —{' '}
            <button className="underline" onClick={resetStress}>
              reset them
            </button>
            .
          </Notice>
        )}
        <Grid2>
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Correlation Shock</h3>
            <p className="text-xs text-muted-foreground">
              Diagonal: volatility multipliers. Off-diagonal: shocks added to the correlations.
            </p>
            {gridMatches && (
              <StressGrid symbols={symbols} matrix={stressGrid} onChange={setStressGrid} />
            )}
          </div>
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Returns Shock</h3>
            <div className="flex flex-wrap gap-2">
              {symbols.map((s) => (
                <NumberField
                  key={s}
                  label={s}
                  value={meanShock[s] ?? 1}
                  step={0.1}
                  onChange={(v) =>
                    setMeanShock((prev) => ({ ...prev, [s]: Number.isFinite(v) ? v : 1 }))
                  }
                />
              ))}
            </div>
          </div>
        </Grid2>
        <ViewStatus
          isFetching={preview.isFetching}
          error={preview.error ? apiErrorMessage(preview.error) : null}
        />
        {preview.data && (
          <>
            <DataTable
              frame={preview.data.data.moments}
              title="Mean and Vol Changes"
              format="percent"
            />
            <Grid2>
              <DataTable
                frame={preview.data.data.correlation}
                title="Original Correlation"
                decimals={2}
              />
              <DataTable
                frame={preview.data.data.stressed_correlation}
                title="New Correlation"
                decimals={2}
              />
            </Grid2>
          </>
        )}
      </Panel>
    </div>
  );
};

const ValueAtRisk = () => (
  <RequireAllocations>
    <ValueAtRiskPage />
  </RequireAllocations>
);

export default ValueAtRisk;
