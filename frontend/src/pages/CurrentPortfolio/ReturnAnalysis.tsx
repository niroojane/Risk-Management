import { useMemo } from 'react';
import { FrameChart } from '@/components/charts';
import { Grid2, Panel, RangeFields, RunButton, Toolbar, ViewStatus } from '@/components/workspace';
import { HISTORICAL, useSeriesNames, useView, useWorkspacePayload } from '@/hooks/useWorkspace';
import { useSeriesPair } from '@/hooks/useSeriesPair';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { RequireUniverse } from '../shared/Guards';
import { PairSelect } from '../shared/PairSelect';

/** Current Portfolio > P&L > Return Analysis */
const ReturnAnalysisPage = () => {
  const pnlFrequency = useWorkspaceStore((s) => s.pnlFrequency);
  const historical = useWorkspaceStore((s) => s.historicalEnabled);
  const names = useSeriesNames(historical);
  const pair = useSeriesPair('expost', names, HISTORICAL, 'Fund');

  const workspace = useWorkspacePayload('expost', pnlFrequency, historical);
  const params = useMemo(
    () => workspace && { ...workspace, fund: pair.fund, benchmark: pair.benchmark },
    [workspace, pair.fund, pair.benchmark]
  );
  const view = useView('return-analysis', params, workspaceService.returnAnalysis);
  const data = view.data;

  return (
    <Panel>
      <Toolbar>
        <RangeFields rangeKey="expost" />
        <PairSelect
          names={names}
          fund={pair.fund}
          benchmark={pair.benchmark}
          onFund={pair.setFund}
          onBenchmark={pair.setBenchmark}
          fundLabel="Select Fund"
        />
        <RunButton onClick={view.run} loading={view.isFetching}>
          Refresh
        </RunButton>
      </Toolbar>
      <ViewStatus {...view} />
      {data && (
        <Grid2>
          <FrameChart
            frame={data.contribution}
            title="Return Contribution"
            format="percent"
            visible={['Total Return']}
          />
          <FrameChart
            frame={data.drawdown}
            title="Drawdown"
            format="percent"
            visible={[pair.fund]}
          />
          <FrameChart
            frame={data.benchmark_contribution}
            title="Benchmark Return Contribution"
            format="percent"
            visible={['Total Return']}
          />
          <FrameChart
            frame={data.active_contribution}
            title="Active Return Contribution"
            format="percent"
            visible={['Total Return']}
          />
        </Grid2>
      )}
    </Panel>
  );
};

const ReturnAnalysis = () => (
  <RequireUniverse>
    <ReturnAnalysisPage />
  </RequireUniverse>
);

export default ReturnAnalysis;
