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
import { useView } from '@/hooks/useWorkspace';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { RequireUniverse } from '../shared/Guards';

/** Market Risk > Market Risk: principal components of the selected universe */
const MarketRiskPage = () => {
  const universe = useWorkspaceStore((s) => s.universe)!;
  const range = useWorkspaceStore((s) => s.ranges.market);
  const symbols = universe.selected.length >= 2 ? universe.selected : universe.symbols;
  const [components, setComponents] = useState(Math.min(5, symbols.length));
  const [component, setComponent] = useState('PC1');
  const [closest, setClosest] = useState(5);

  const params = useMemo(
    () =>
      [components, closest].every(Number.isFinite)
        ? {
            symbols,
            start_date: range.start,
            end_date: range.end,
            num_components: components,
            component,
            num_closest: closest,
          }
        : null,
    [symbols, range, components, component, closest]
  );
  const view = useView('pca', params, workspaceService.pca);
  const data = view.data;
  const componentOptions =
    data?.components ?? Array.from({ length: components }, (_, i) => `PC${i + 1}`);

  return (
    <Panel>
      <Toolbar>
        <RangeFields rangeKey="market" />
        <NumberField
          label="PCA Components"
          value={components}
          min={1}
          max={symbols.length}
          onChange={setComponents}
        />
        <SelectField
          label="Select PCA"
          value={component}
          options={componentOptions}
          onChange={setComponent}
        />
        <NumberField
          label="PCA Closest"
          value={closest}
          min={1}
          max={symbols.length}
          onChange={setClosest}
        />
        <RunButton onClick={view.run} loading={view.isFetching}>
          Market Risk Analysis
        </RunButton>
      </Toolbar>
      <ViewStatus {...view} />
      {data && (
        <Grid2>
          <FrameChart
            frame={data.variance_explained}
            title="Variance Explanation in %"
            kind="bar"
            format="percent"
          />
          <FrameChart frame={data.eigen_index} title="Eigen Index" />
          <FrameChart
            frame={data.eigen_weights}
            title="Eigen Weights"
            kind="bar"
            format="percent"
          />
          <FrameChart frame={data.similarity} title="PCA Similarity" />
        </Grid2>
      )}
    </Panel>
  );
};

const MarketRisk = () => (
  <RequireUniverse>
    <MarketRiskPage />
  </RequireUniverse>
);

export default MarketRisk;
