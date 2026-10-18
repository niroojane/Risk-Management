import { useMemo, useState } from 'react';
import { FrameChart } from '@/components/data';
import {
  Grid2,
  Notice,
  NumberField,
  Panel,
  RangeFields,
  RunButton,
  Toolbar,
  ViewStatus,
} from '@/components/ui';
import { HISTORICAL, useSeriesNames, useView, useWorkspacePayload } from '@/hooks/useWorkspace';
import { useSeriesPair } from '@/hooks/useSeriesPair';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { DecompositionCharts } from '../shared/DecompositionCharts';
import { RequireAllocations } from '../shared/Guards';
import { PairSelect } from '../shared/PairSelect';

/** Risk Analysis > Volatility Analysis > Tracking Error */
const TrackingErrorPage = () => {
  const pnlFrequency = useWorkspaceStore((s) => s.pnlFrequency);
  const historical = useWorkspaceStore((s) => s.historicalEnabled);
  const names = useSeriesNames(historical);
  const pair = useSeriesPair('tracking-error', names, HISTORICAL, 'Fund');
  const [rollingWindow, setRollingWindow] = useState(252);

  const workspace = useWorkspacePayload('risk', pnlFrequency, historical);
  const params = useMemo(
    () =>
      workspace && Number.isFinite(rollingWindow)
        ? { ...workspace, selected: pair.fund, benchmark: pair.benchmark, window: rollingWindow }
        : null,
    [workspace, pair.fund, pair.benchmark, rollingWindow]
  );
  const view = useView('tracking-error', params, workspaceService.trackingError);
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
        <NumberField label="Window" value={rollingWindow} min={10} onChange={setRollingWindow} />
        <RunButton onClick={view.run} loading={view.isFetching}>
          Get Ex Ante TE
        </RunButton>
      </Toolbar>
      {pair.fund === pair.benchmark && (
        <Notice>The fund is its own benchmark: its tracking error is zero.</Notice>
      )}
      <ViewStatus {...view} />
      {data && (
        <Grid2>
          <FrameChart
            frame={data.tracking_error}
            title="Ex Ante Tracking Error"
            format="percent"
            visible={[HISTORICAL, 'Fund']}
          />
          <DecompositionCharts view={data} volatilityTitle="Tracking Error Contribution" />
        </Grid2>
      )}
    </Panel>
  );
};

const TrackingError = () => (
  <RequireAllocations>
    <TrackingErrorPage />
  </RequireAllocations>
);

export default TrackingError;
