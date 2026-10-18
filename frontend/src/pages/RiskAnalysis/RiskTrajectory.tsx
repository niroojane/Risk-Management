import { useMemo, useState } from 'react';
import { FrameChart } from '@/components/data';
import {
  Grid2,
  NumberField,
  Panel,
  RangeFields,
  RunButton,
  SelectField,
  Toolbar,
  ViewStatus,
} from '@/components/ui';
import { HISTORICAL, useSeriesNames, useView, useWorkspacePayload } from '@/hooks/useWorkspace';
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
  const params = useMemo(
    () =>
      workspace && Number.isFinite(rollingWindow)
        ? { ...workspace, selected: fund, window: rollingWindow }
        : null,
    [workspace, fund, rollingWindow]
  );
  const view = useView('risk-trajectory', params, workspaceService.riskTrajectory);
  const data = view.data;

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
      {data && (
        <Grid2>
          <FrameChart
            frame={data.volatility}
            title="Ex Ante Volatility"
            format="percent"
            visible={[HISTORICAL, 'Fund']}
          />
          <DecompositionCharts view={data} />
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
