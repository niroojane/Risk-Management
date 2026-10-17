import { useMemo } from 'react';
import { DataTable, RangeFields, RunButton, Toolbar, ViewStatus } from '@/components/workspace';
import { useView } from '@/hooks/useWorkspace';
import { universeService } from '@/services/universeService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { buildAssetTables } from '../Universe/InvestmentUniverse/universe';

/**
 * Return and risk metrics of every asset of the universe over the analysis window
 * (the notebook's asset_returns / asset_risk tables, shown in Investment Universe and Strategy).
 * Both pages share the cached result for the same dates.
 */
export const AssetMetricsTables = ({ withRange = true }: { withRange?: boolean }) => {
  const universe = useWorkspaceStore((s) => s.universe);
  const perf = useWorkspaceStore((s) => s.ranges.perf);

  const params = universe
    ? { symbols: universe.symbols, start_date: perf.start, end_date: perf.end }
    : null;
  // Loaded as soon as prices are, like the notebook's tables after 'Get Prices'
  const metrics = useView('asset-metrics', params, universeService.fetchAssetMetrics, true);
  const tables = useMemo(
    () => (metrics.data ? buildAssetTables(metrics.data, perf.start, perf.end) : null),
    [metrics.data, perf]
  );

  return (
    <div className="space-y-4">
      <Toolbar>
        {withRange && <RangeFields rangeKey="perf" />}
        <RunButton onClick={metrics.run} loading={metrics.isFetching} disabled={!params}>
          Refresh
        </RunButton>
      </Toolbar>
      <ViewStatus {...metrics} />
      {tables && (
        <>
          <DataTable frame={tables.returns} title="Asset Returns" format="percent" />
          <DataTable
            frame={tables.risk}
            title="Asset Risk"
            format={(_, row) => (row === 'Date of Max Drawdown' ? 'number' : 'percent')}
          />
        </>
      )}
    </div>
  );
};
