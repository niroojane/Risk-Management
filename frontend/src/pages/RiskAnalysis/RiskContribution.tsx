import { useMemo } from 'react';
import { Panel, RangeFields, RunButton, SelectField, Toolbar, ViewStatus } from '@/components/ui';
import { DataTable } from '@/components/data';
import { useAllocationMap, useView } from '@/hooks/useWorkspace';
import { useSeriesPair } from '@/hooks/useSeriesPair';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { RebalancingFrequency } from '@/types/workspace';
import { RequireAllocations } from '../shared/Guards';
import { PairSelect } from '../shared/PairSelect';

const FREQUENCIES: RebalancingFrequency[] = ['Yearly', 'Quarterly', 'Monthly'];

/** Risk Analysis > Volatility Analysis > Risk Contribution */
const RiskContributionPage = () => {
  const universe = useWorkspaceStore((s) => s.universe)!;
  const range = useWorkspaceStore((s) => s.ranges.risk);
  const pnlFrequency = useWorkspaceStore((s) => s.pnlFrequency);
  const setPnlFrequency = useWorkspaceStore((s) => s.setPnlFrequency);
  const allocations = useAllocationMap();
  const names = Object.keys(allocations);
  const pair = useSeriesPair('risk-contribution', names, 'Optimal Portfolio', 'Equal Weighted');

  const params = useMemo(
    () => ({
      symbols: universe.symbols,
      start_date: range.start,
      end_date: range.end,
      allocations,
      fund: pair.fund,
      benchmark: pair.benchmark,
      frequency: pnlFrequency,
    }),
    [universe, range, allocations, pair.fund, pair.benchmark, pnlFrequency]
  );
  const view = useView('risk-contribution', params, workspaceService.riskContribution);
  const data = view.data;

  return (
    <Panel>
      <Toolbar>
        <RangeFields rangeKey="risk" />
        <PairSelect
          names={names}
          fund={pair.fund}
          benchmark={pair.benchmark}
          onFund={pair.setFund}
          onBenchmark={pair.setBenchmark}
        />
        <SelectField
          label="Frequency"
          value={pnlFrequency}
          options={FREQUENCIES}
          onChange={setPnlFrequency}
        />
        <RunButton onClick={view.run} loading={view.isFetching}>
          Refresh
        </RunButton>
      </Toolbar>
      <ViewStatus {...view} />
      {data && (
        <>
          <DataTable
            frame={data.contribution}
            title="Performance and Risk Contribution"
            decimals={2}
          />
          <DataTable frame={data.excess} title="Excess P&L and TE Contribution" decimals={2} />
          <DataTable
            frame={data.ex_ante}
            title="Ex Ante Metrics"
            format={(column) => (column === 'Beta Ex Ante' ? 'number' : 'percent')}
          />
        </>
      )}
    </Panel>
  );
};

const RiskContribution = () => (
  <RequireAllocations>
    <RiskContributionPage />
  </RequireAllocations>
);

export default RiskContribution;
