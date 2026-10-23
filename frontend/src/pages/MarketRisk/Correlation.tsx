import { useMemo, useState } from 'react';
import { FrameChart, HeatmapChart } from '@/components/data';
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
import { useView } from '@/hooks/useWorkspace';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { RequireUniverse } from '../shared/Guards';

/** Market Risk > Correlation */
const CorrelationPage = () => {
  const universe = useWorkspaceStore((s) => s.universe)!;
  const range = useWorkspaceStore((s) => s.ranges.market);
  const symbols = universe.symbols;
  const [asset1, setAsset1] = useState(symbols[0]);
  const [asset2, setAsset2] = useState(symbols[1]);
  const [rollingWindow, setRollingWindow] = useState(252);
  const first = symbols.includes(asset1) ? asset1 : symbols[0];
  const second = symbols.includes(asset2) ? asset2 : symbols[1];

  const params = useMemo(
    () =>
      first !== second && Number.isFinite(rollingWindow)
        ? {
            symbols,
            // the rolling charts reach back one window before the start date
            history_start: universe.start,
            start_date: range.start,
            end_date: range.end,
            asset1: first,
            asset2: second,
            window: rollingWindow,
          }
        : null,
    [symbols, universe.start, range, first, second, rollingWindow]
  );
  const view = useView('correlation', params, workspaceService.correlation);
  const data = view.data;

  return (
    <Panel>
      <Toolbar>
        <RangeFields rangeKey="market" />
        <SelectField label="Asset 1" value={first} options={symbols} onChange={setAsset1} />
        <SelectField label="Asset 2" value={second} options={symbols} onChange={setAsset2} />
        <NumberField
          label="Rolling Correlation"
          value={rollingWindow}
          min={2}
          onChange={setRollingWindow}
        />
        <RunButton onClick={view.run} loading={view.isFetching} disabled={!params}>
          Get Correlation
        </RunButton>
      </Toolbar>
      {first === second && <Notice>⚠️ Same asset.</Notice>}
      <ViewStatus {...view} />
      {data && (
        <Grid2>
          <FrameChart frame={data.rolling_correlation} title={`${first}/${second} Correlation`} />
          <FrameChart
            frame={data.first_component}
            title="First principal component (Variance Explained in %)"
            format="percent"
          />
          <FrameChart
            frame={data.rolling_mean_returns}
            title="Mean Return"
            format="percent"
            visible={[first, second]}
          />
          <HeatmapChart frame={data.matrix} title="Correlation Matrix" />
        </Grid2>
      )}
    </Panel>
  );
};

const Correlation = () => (
  <RequireUniverse>
    <CorrelationPage />
  </RequireUniverse>
);

export default Correlation;
