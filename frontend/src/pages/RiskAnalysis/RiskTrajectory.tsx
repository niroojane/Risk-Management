import { useMemo, useState } from 'react';
import { FrameChart } from '@/components/data';
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
import {
  HISTORICAL,
  useRangeView,
  useSeriesNames,
  useWorkspacePayload,
} from '@/hooks/useWorkspace';
import { useSeriesPair } from '@/hooks/useSeriesPair';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { DecompositionCharts } from '../shared/DecompositionCharts';
import { RequireAllocations } from '../shared/Guards';

/** Risk Analysis > Volatility Analysis > Risk Trajectory */
const RiskTrajectoryPage = () => {
  const pnlFrequency = useWorkspaceStore((s) => s.pnlFrequency);
  const historical = useWorkspaceStore((s) => s.historicalEnabled);
  const names = useSeriesNames(historical);
  const { fund, setFund } = useSeriesPair('risk-trajectory', names, HISTORICAL, 'Fund');
  const [rollingWindow, setRollingWindow] = useState(252);

  const workspace = useWorkspacePayload('risk', pnlFrequency, historical);
  // Every series is decomposed: changing the fund only picks another one
  const params = useMemo(
    () =>
      workspace && Number.isFinite(rollingWindow) ? { ...workspace, window: rollingWindow } : null,
    [workspace, rollingWindow]
  );
  const view = useRangeView('risk-trajectory', params, workspaceService.riskTrajectory);
  const data = view.data;
  const decomposition = data?.decomposition[fund];

  return (
    <Panel>
      <Toolbar>
        <RangeFields rangeKey="risk" />
        <SelectField
          label="Fund"
          value={fund}
          options={names}
          onChange={setFund}
          selectClassName="w-60"
        />
        <NumberField label="Window" value={rollingWindow} min={10} onChange={setRollingWindow} />
        <RunButton onClick={view.run} loading={view.isFetching}>
          Get Ex Ante Vol
        </RunButton>
      </Toolbar>
      <ViewStatus {...view} />
      {data && !decomposition && (
        <Notice>{fund} has fewer days than the rolling window in this date range.</Notice>
      )}
      {data && (
        <Grid2>
          <FrameChart
            frame={data.volatility}
            title="Ex Ante Volatility"
            format="percent"
            visible={[HISTORICAL, 'Fund']}
          />
          {decomposition && <DecompositionCharts view={decomposition} />}
        </Grid2>
      )}
    </Panel>
  );
};

const RiskTrajectory = () => (
  <RequireAllocations>
    <RiskTrajectoryPage />
  </RequireAllocations>
);

export default RiskTrajectory;
