import { Notice, Panel, RunButton, Toolbar, ViewStatus } from '@/components/ui';
import { DataTable } from '@/components/data';
import type { CellFormat } from '@/components/data/DataTable';
import { useView } from '@/hooks/useWorkspace';
import { useIsMultiAsset } from '@/hooks/useProfile';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';

/** The Fund's units since its last rebalancing: the model drifts with prices, as in the notebooks */
const useModelUnits = () => {
  const backtest = useWorkspaceStore((s) => s.backtest);
  if (!backtest?.model_units) return null;
  return { model_units: backtest.model_units, model_prices: backtest.model_prices };
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
  const model = useModelUnits();
  const multiAsset = useIsMultiAsset();
  // The buttons always read the live account, not the backend cache
  const positions = useView('positioning', model, (model) =>
    workspaceService.positioning(model, true)
  );
  const holdings = useView('holdings', {}, () => workspaceService.holdings(true));
  const pnl = useView('account-pnl', {}, () => workspaceService.accountPnl(true));

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
