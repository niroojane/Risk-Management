import { useMemo } from 'react';
import { DataTable, Notice, Panel, RunButton, Toolbar, ViewStatus } from '@/components/workspace';
import type { CellFormat } from '@/components/workspace/DataTable';
import { useView } from '@/hooks/useWorkspace';
import { useIsMultiAsset } from '@/hooks/useProfile';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { Weights } from '@/types/workspace';

/** Latest weights of the Fund: its last scheduled allocation */
const useModelWeights = (): Weights | null => {
  const backtest = useWorkspaceStore((s) => s.backtest);
  return useMemo(() => {
    const fund = backtest?.schedules.Fund;
    if (!fund) return null;
    const dates = Object.keys(fund).sort();
    return fund[dates[dates.length - 1]];
  }, [backtest]);
};

const percentColumns = ['Weights Model', 'Current Weights', 'Weights'];
/** Plain numbers: units, FX rates and the multi-asset 'Total P&L %' (already in percent) */
const numberColumns = ['Quantity', 'Units (trades)', 'FX Rate', 'Cost FX Rate', 'Total P&L %'];

const cellFormat = (column: string): CellFormat =>
  percentColumns.includes(column)
    ? 'percent'
    : numberColumns.includes(column)
      ? 'number'
      : 'currency';

/** Strategy > Positioning and Current Portfolio > Positioning: holdings vs model, and P&L */
const Positioning = () => {
  const model = useModelWeights();
  const multiAsset = useIsMultiAsset();
  const positions = useView('positioning', model ? { model } : null, ({ model }) =>
    workspaceService.positioning(model)
  );
  const holdings = useView('holdings', {}, () => workspaceService.holdings());
  const pnl = useView('account-pnl', {}, () => workspaceService.accountPnl());

  return (
    <div className="space-y-6">
      <Panel>
        <Toolbar>
          <RunButton
            onClick={() => (model ? positions.run() : holdings.run())}
            loading={positions.isFetching || holdings.isFetching}
          >
            Get Positions
          </RunButton>
          <RunButton onClick={pnl.run} loading={pnl.isFetching}>
            Get P&L
          </RunButton>
        </Toolbar>
        {!model && (
          <Notice>⚠️ Load Model (Strategy › Get Results) to compare the holdings with it.</Notice>
        )}
      </Panel>

      <Panel title="Positioning">
        <ViewStatus {...(model ? positions : holdings)} />
        <DataTable
          frame={model ? positions.data?.positioning : holdings.data?.holdings}
          format={cellFormat}
        />
      </Panel>

      <Panel title="P&L">
        <ViewStatus {...pnl} />
        {!pnl.data && !pnl.isFetching && <Notice tone="info">⚠️ P&L not computed.</Notice>}
        {pnl.data && (
          <>
            <DataTable frame={pnl.data.pnl} format={cellFormat} />
            <DataTable
              frame={pnl.data.trades}
              title="Trades"
              indexLabel={multiAsset ? '' : 'Date(UTC)'}
              decimals={8}
            />
          </>
        )}
      </Panel>
    </div>
  );
};

export default Positioning;
