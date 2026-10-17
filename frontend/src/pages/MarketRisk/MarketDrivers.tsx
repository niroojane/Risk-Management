import { useMemo, useState } from 'react';
import { FrameChart } from '@/components/charts';
import {
  Grid2,
  NumberField,
  Panel,
  RangeFields,
  RunButton,
  SelectField,
  Toolbar,
  ViewStatus,
} from '@/components/workspace';
import { HISTORICAL, useBenchmark, useView, useWorkspacePayload } from '@/hooks/useWorkspace';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { RebalancingFrequency } from '@/types/workspace';
import { RequireUniverse } from '../shared/Guards';

const FREQUENCIES: RebalancingFrequency[] = ['Yearly', 'Quarterly', 'Monthly'];

/** Market Risk > Market Drivers: eigen-portfolio market index vs the portfolios */
const MarketDriversPage = () => {
  const frequency = useWorkspaceStore((s) => s.frequency);
  const historical = useWorkspaceStore((s) => s.historicalEnabled);
  const [eigenFrequency, setEigenFrequency] = useState<RebalancingFrequency>('Quarterly');
  const [component, setComponent] = useState('PC1');
  const [rollingWindow, setRollingWindow] = useState(252);
  const benchmark = useBenchmark();

  const workspace = useWorkspacePayload('market', frequency, historical);
  const params = useMemo(
    () =>
      workspace && Number.isFinite(rollingWindow)
        ? { ...workspace, eigen_frequency: eigenFrequency, component, window: rollingWindow }
        : null,
    [workspace, eigenFrequency, component, rollingWindow]
  );
  const view = useView('market-drivers', params, workspaceService.marketDrivers);
  const data = view.data;

  return (
    <Panel>
      <Toolbar>
        <RangeFields rangeKey="market" />
        <SelectField
          label="Frequency"
          value={eigenFrequency}
          options={FREQUENCIES}
          onChange={setEigenFrequency}
        />
        <SelectField
          label="PCA"
          value={component}
          options={['PC1', 'PC2', 'PC3']}
          onChange={setComponent}
        />
        <NumberField label="Window" value={rollingWindow} min={10} onChange={setRollingWindow} />
        <RunButton onClick={view.run} loading={view.isFetching}>
          Get Market Drivers
        </RunButton>
      </Toolbar>
      <ViewStatus {...view} />
      {data && (
        <Grid2>
          <FrameChart
            frame={data.performance}
            title="Performance Comparison"
            visible={['Market Index', 'Fund', benchmark.label, HISTORICAL]}
          />
          <FrameChart
            frame={data.vol_contribution}
            title="Market Volatility"
            format="percent"
            visible={['Total Vol']}
          />
          <FrameChart frame={data.drivers} title="Market Drivers" visible={['Market Index']} />
          <FrameChart
            frame={data.idiosyncratic_contribution}
            title="Market Intrinsic Volatility"
            format="percent"
            visible={['Total Idiosyncratic Vol']}
          />
          <FrameChart
            frame={data.correlation_contribution}
            title="Market Correlation"
            format="percent"
            visible={['Total Correlation']}
          />
          <FrameChart
            frame={data.weights}
            title="Market Weights"
            format="percent"
            visible={[benchmark.ticker]}
          />
        </Grid2>
      )}
    </Panel>
  );
};

const MarketDrivers = () => (
  <RequireUniverse>
    <MarketDriversPage />
  </RequireUniverse>
);

export default MarketDrivers;
