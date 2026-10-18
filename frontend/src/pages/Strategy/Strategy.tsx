import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { FrameChart, DataTable } from '@/components/data';
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
import { apiErrorMessage, useBenchmark, useView, useWorkspacePayload } from '@/hooks/useWorkspace';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { ConstraintSign, Objective, RiskType } from '@/types/workspace';
import { frameFromRecords } from '@/utils/frame';
import { AssetMetricsTables } from '../shared/AssetMetricsTables';
import { RequireUniverse } from '../shared/Guards';
import { AllocationGrid } from './components/AllocationGrid';
import { FrontierChart } from './components/FrontierChart';
import {
  FREQUENCIES,
  RELATIVE,
  RISK_OPTIONS,
  SIGN_OPTIONS,
  STRATEGY_OPTIONS,
  optimizeGrid,
  riskLabel,
  riskPayload,
  signLabel,
  strategyLabel,
} from './strategyGrid';

const StrategyPage = () => {
  const store = useWorkspaceStore();
  const HEADLINE = ['Fund', useBenchmark().label];
  const universe = store.universe!;
  const symbols = universe.symbols;
  const allocationNames = store.allocations.map((a) => a.name);

  // Constraint / overlay / risk forms
  const [asset, setAsset] = useState<string>('All');
  const [sign, setSign] = useState<ConstraintSign>('<=');
  const [limit, setLimit] = useState(0.2);
  const [overlay, setOverlay] = useState<Objective>('minimum_variance');
  const [overlayLimit, setOverlayLimit] = useState(0.1);
  const [risk, setRisk] = useState<RiskType>('volatility');
  const [riskSign, setRiskSign] = useState<ConstraintSign>('<=');
  const [riskLimit, setRiskLimit] = useState(0.5);
  const refreshAfterBacktest = useRef(false);

  const optimize = useMutation({
    mutationFn: () =>
      optimizeGrid({
        universe,
        range: store.ranges.perf,
        constraints: store.constraints,
        riskConstraints: store.riskConstraints,
        allocations: store.allocations,
        benchmark: store.benchmark,
        frequency: store.frequency,
      }),
    onSuccess: ({ rows }) => {
      store.setAllocations(rows, true);
      if (store.benchmark && !rows.some((r) => r.name === store.benchmark)) {
        store.setStrategy({ benchmark: null });
      }
    },
  });

  const backtest = useMutation({
    mutationFn: async () => {
      const benchWeights = store.allocations.find((a) => a.name === store.benchmark)?.weights;
      const wanted = [store.objective, ...store.overlays.map((o) => o.objective)];
      if (!benchWeights && wanted.some((o) => RELATIVE.includes(o))) {
        throw new Error(
          "⚠️ Min Tracking Error / Max Information Ratio need a benchmark allocation: select it in 'Benchmark' first."
        );
      }
      return workspaceService.backtest({
        symbols,
        start_date: universe.start,
        end_date: universe.end,
        objective: store.objective,
        overlays: store.overlays,
        frequency: store.frequency,
        constraints: store.constraints,
        risk_constraints: benchWeights ? riskPayload(store.riskConstraints) : null,
        benchmark: benchWeights ?? null,
      });
    },
    onSuccess: (response) => {
      refreshAfterBacktest.current = true;
      store.setBacktest(response.data);
      const rows = store.allocations.filter((a) => a.name !== 'Model');
      store.setAllocations([...rows, { name: 'Model', weights: response.data.model }]);
    },
  });

  const workspace = useWorkspacePayload('perf', store.frequency, false);
  const performanceParams = useMemo(
    () =>
      workspace && {
        ...workspace,
        benchmark: store.benchmark,
        vol_window: store.volWindow,
        constraints: store.constraints,
      },
    [workspace, store.benchmark, store.volWindow, store.constraints]
  );
  const performance = useView(
    'strategy-performance',
    performanceParams,
    workspaceService.performance
  );

  // The notebook refreshes the performance right after 'Get Results', once the new Fund is in the payload
  const { run: runPerformance } = performance;
  useEffect(() => {
    if (refreshAfterBacktest.current && performanceParams) {
      refreshAfterBacktest.current = false;
      runPerformance();
    }
  }, [performanceParams, runPerformance]);

  const view = performance.data;

  return (
    <div className="space-y-6">
      <Panel title="Settings">
        <Toolbar>
          <RangeFields rangeKey="perf" />
          <SelectField
            label="Strategy"
            value={store.objective}
            options={STRATEGY_OPTIONS}
            onChange={(objective) => store.setStrategy({ objective })}
          />
          <SelectField
            label="Frequency"
            value={store.frequency}
            options={FREQUENCIES}
            onChange={(frequency) => store.setStrategy({ frequency })}
          />
          <SelectField
            label="Benchmark"
            value={store.benchmark}
            options={allocationNames}
            placeholder="Optimize first"
            selectClassName="w-60"
            onChange={(benchmark) => store.setStrategy({ benchmark })}
          />
          <NumberField
            label="Vol Window"
            value={store.volWindow}
            min={2}
            onChange={(volWindow) => store.setStrategy({ volWindow })}
          />
        </Toolbar>
      </Panel>

      <Panel title="Assets">
        <AssetMetricsTables withRange={false} />
      </Panel>

      <Panel title="Constraints">
        <Toolbar>
          <SelectField
            label="Asset"
            value={asset}
            options={[...symbols, 'All']}
            onChange={setAsset}
          />
          <SelectField label="Sign" value={sign} options={SIGN_OPTIONS} onChange={setSign} />
          <NumberField label="Limit" value={limit} step={0.01} onChange={setLimit} />
          <Button
            variant="secondary"
            onClick={() => Number.isFinite(limit) && store.addConstraint({ asset, sign, limit })}
          >
            Add Constraint
          </Button>
          <Button variant="outline" onClick={store.clearConstraints}>
            Clear All
          </Button>
          <RunButton onClick={() => optimize.mutate()} loading={optimize.isPending}>
            Optimize Portfolio
          </RunButton>
        </Toolbar>
        <DataTable
          frame={frameFromRecords(
            Object.fromEntries(
              store.constraints.map((c, i) => [
                String(i + 1),
                { Asset: c.asset, Sign: signLabel(c.sign), Limit: c.limit },
              ])
            )
          )}
        />
        {optimize.error && <Notice tone="error">{apiErrorMessage(optimize.error)}</Notice>}
        {optimize.data?.messages.map((m) => (
          <Notice key={m}>{m}</Notice>
        ))}
      </Panel>

      <Panel title="Allocations">
        {store.allocations.length === 0 ? (
          <Notice tone="info">Click “Optimize Portfolio” to build the allocation grid.</Notice>
        ) : (
          <AllocationGrid
            rows={store.allocations}
            symbols={symbols}
            onChange={(rows) => store.setAllocations(rows)}
          />
        )}
        <Toolbar>
          <Button
            variant="secondary"
            disabled={store.allocations.length === 0}
            onClick={() =>
              store.setAllocations([
                ...store.allocations,
                {
                  name: `Allocation ${store.allocations.length}`,
                  weights: Object.fromEntries(symbols.map((s) => [s, 0])),
                },
              ])
            }
          >
            Add Allocation
          </Button>
          <Button variant="outline" onClick={store.resetAllocations}>
            Clear Allocation
          </Button>
        </Toolbar>
      </Panel>

      <Grid2>
        <Panel title="Strategy Overlay">
          <Toolbar>
            <SelectField
              label="Strategy Overlay"
              value={overlay}
              options={STRATEGY_OPTIONS}
              onChange={setOverlay}
            />
            <NumberField
              label="Overlay Limit"
              value={overlayLimit}
              step={0.05}
              onChange={setOverlayLimit}
            />
            <Button
              variant="secondary"
              onClick={() =>
                Number.isFinite(overlayLimit) &&
                store.addOverlay({ objective: overlay, limit: overlayLimit })
              }
            >
              Add Strategy
            </Button>
            <Button variant="outline" onClick={store.clearOverlays}>
              Clear Strategy
            </Button>
          </Toolbar>
          <DataTable
            frame={frameFromRecords(
              Object.fromEntries(
                store.overlays.map((o, i) => [
                  String(i + 1),
                  { Strategy: strategyLabel(o.objective), Limit: o.limit },
                ])
              )
            )}
          />
        </Panel>

        <Panel title="Risk Constraints">
          <Toolbar>
            <SelectField label="Risk Type" value={risk} options={RISK_OPTIONS} onChange={setRisk} />
            <SelectField
              label="Sign"
              value={riskSign}
              options={SIGN_OPTIONS}
              onChange={setRiskSign}
            />
            <NumberField label="Risk Limit" value={riskLimit} step={0.01} onChange={setRiskLimit} />
            <Button
              variant="secondary"
              onClick={() =>
                Number.isFinite(riskLimit) &&
                store.addRiskConstraint({ risk, sign: riskSign, limit: riskLimit })
              }
            >
              Add Risk Strat
            </Button>
            <Button variant="outline" onClick={store.clearRiskConstraints}>
              Clear Risk Strat
            </Button>
          </Toolbar>
          <DataTable
            frame={frameFromRecords(
              Object.fromEntries(
                store.riskConstraints.map((c) => [
                  riskLabel(c.risk),
                  { Sign: signLabel(c.sign), Limit: c.limit },
                ])
              )
            )}
            indexLabel="Risk"
          />
          <p className="text-xs text-muted-foreground">
            Beta, tracking error and information ratio are measured against the Benchmark
            allocation.
          </p>
        </Panel>
      </Grid2>

      <Panel title="Rolling Strategy">
        <Toolbar>
          <RunButton onClick={() => backtest.mutate()} loading={backtest.isPending}>
            Get Results
          </RunButton>
          <span className="text-xs text-muted-foreground">
            {strategyLabel(store.objective)} rebalanced {store.frequency.toLowerCase()} over the
            full history ({universe.start} → {universe.end})
            {store.overlays.length > 0 && `, with ${store.overlays.length} overlay(s)`}.
          </span>
        </Toolbar>
        {backtest.error && <Notice tone="error">{apiErrorMessage(backtest.error)}</Notice>}
        {backtest.data?.warnings?.map((w) => (
          <Notice key={w}>{w}</Notice>
        ))}
        {store.backtest && (
          <>
            <Grid2>
              <DataTable
                frame={store.backtest.tables.Fund}
                title="Final Strategy"
                maxHeight="35vh"
              />
              <DataTable
                frame={store.backtest.tables.Core}
                title="Core Strategy"
                maxHeight="35vh"
              />
            </Grid2>
            {store.backtest.tables.Overlay && (
              <DataTable
                frame={store.backtest.tables.Overlay}
                title="Tactical Allocation"
                maxHeight="35vh"
              />
            )}
            <DataTable frame={store.backtest.metrics} title="Backtest Metrics" />
          </>
        )}
      </Panel>

      <Panel title="Performance">
        <Toolbar>
          <RangeFields rangeKey="perf" />
          <RunButton
            onClick={performance.run}
            loading={performance.isFetching}
            disabled={store.allocations.length === 0 && !store.backtest}
          >
            Refresh
          </RunButton>
        </Toolbar>
        <ViewStatus {...performance} />
        {view && (
          <>
            <DataTable frame={view.returns_table} format="percent" />
            <DataTable
              frame={view.risk_table}
              format={(_, row) => (row === 'Date of Max Drawdown' ? 'number' : 'percent')}
            />
            {view.frontier && (
              <DataTable
                frame={view.frontier.indicators}
                format={(_, row) => (row === 'Sharpe Ratio' ? 'number' : 'percent')}
              />
            )}
            <Grid2>
              <FrameChart frame={view.levels} title="Performance" visible={HEADLINE} />
              <FrameChart
                frame={view.drawdown}
                title="Drawdown"
                format="percent"
                visible={HEADLINE}
              />
              <FrameChart
                frame={view.rolling_volatility}
                title="Portfolio Rolling Volatility"
                format="percent"
                visible={HEADLINE}
              />
              {view.frontier && <FrontierChart frontier={view.frontier} />}
            </Grid2>
          </>
        )}
      </Panel>
    </div>
  );
};

const Strategy = () => (
  <RequireUniverse>
    <StrategyPage />
  </RequireUniverse>
);

export default Strategy;
