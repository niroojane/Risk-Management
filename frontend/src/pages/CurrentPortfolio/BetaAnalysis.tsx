import { useMemo, useState } from 'react';
import { FrameChart } from '@/components/charts';
import {
  Grid2,
  NumberField,
  Panel,
  RangeFields,
  RunButton,
  Toolbar,
  ViewStatus,
} from '@/components/workspace';
import {
  HISTORICAL,
  useBenchmark,
  useSeriesNames,
  useView,
  useWorkspacePayload,
} from '@/hooks/useWorkspace';
import { useSeriesPair } from '@/hooks/useSeriesPair';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { RequireUniverse } from '../shared/Guards';
import { PairSelect } from '../shared/PairSelect';

/** Current Portfolio > P&L > Beta Analysis */
const BetaAnalysisPage = () => {
  const pnlFrequency = useWorkspaceStore((s) => s.pnlFrequency);
  const historical = useWorkspaceStore((s) => s.historicalEnabled);
  const names = useSeriesNames(historical);
  const pair = useSeriesPair('expost', names, HISTORICAL, 'Fund');
  const [rollingWindow, setRollingWindow] = useState(252);
  const benchmark = useBenchmark();

  const workspace = useWorkspacePayload('risk', pnlFrequency, historical);
  const params = useMemo(
    () =>
      workspace && Number.isFinite(rollingWindow)
        ? { ...workspace, fund: pair.fund, benchmark: pair.benchmark, window: rollingWindow }
        : null,
    [workspace, pair.fund, pair.benchmark, rollingWindow]
  );
  const view = useView('beta', params, workspaceService.beta);
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
          fundLabel="Select Fund"
        />
        <NumberField label="Window" value={rollingWindow} min={2} onChange={setRollingWindow} />
        <RunButton onClick={view.run} loading={view.isFetching}>
          Get Beta
        </RunButton>
      </Toolbar>
      <ViewStatus {...view} />
      {data && (
        <Grid2>
          <FrameChart
            frame={data.asset_beta}
            title="Rolling Asset Beta"
            visible={[benchmark.ticker]}
          />
          <FrameChart
            frame={data.portfolio_beta}
            title={`Portfolio Rolling Beta vs ${pair.benchmark}`}
            visible={[HISTORICAL, 'Fund']}
          />
          <FrameChart frame={data.weights} title="Historical Weights" format="percent" />
          <FrameChart
            frame={data.beta_contribution}
            title="Beta Contribution"
            visible={['Total Beta']}
          />
        </Grid2>
      )}
    </Panel>
  );
};

const BetaAnalysis = () => (
  <RequireUniverse>
    <BetaAnalysisPage />
  </RequireUniverse>
);

export default BetaAnalysis;
