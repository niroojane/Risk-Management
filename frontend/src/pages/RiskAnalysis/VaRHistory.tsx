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
import type { VaRMethod } from '@/types/workspace';
import { RequireAllocations } from '../shared/Guards';

const METHODS: { value: VaRMethod; label: string }[] = [
  { value: 'multivariate', label: 'Multivariate' },
  { value: 'gaussian_copula', label: 'Gaussian Copula' },
  { value: 'monte_carlo', label: 'Monte Carlo' },
  { value: 'gumbel_copula', label: 'Gumbel Copula' },
  { value: 't_copula', label: 'T-Copula' },
];

/** Risk Analysis > Value at Risk > Value at Risk History */
const VaRHistoryPage = () => {
  const pnlFrequency = useWorkspaceStore((s) => s.pnlFrequency);
  const historical = useWorkspaceStore((s) => s.historicalEnabled);
  const names = useSeriesNames(historical);
  const { fund, setFund } = useSeriesPair('var-history', names, 'Fund', '');
  const [method, setMethod] = useState<VaRMethod>('gumbel_copula');
  const [rollingWindow, setRollingWindow] = useState(252);
  const [centile, setCentile] = useState(0.05);
  // Every window runs `iterations` draws per series: kept lower than the one-off simulation
  const [iterations, setIterations] = useState(1000);
  const [stressFactor, setStressFactor] = useState(1);
  const [meanFactor, setMeanFactor] = useState(1);

  const workspace = useWorkspacePayload('risk', pnlFrequency, historical);
  // Every series keeps its per-asset VaR: changing the fund only picks another one
  const params = useMemo(
    () =>
      workspace &&
      [rollingWindow, centile, iterations, stressFactor, meanFactor].every(Number.isFinite)
        ? {
            ...workspace,
            method,
            window: rollingWindow,
            var_centile: centile,
            iterations,
            stress_factor: stressFactor,
            mean_factor: meanFactor,
          }
        : null,
    [workspace, method, rollingWindow, centile, iterations, stressFactor, meanFactor]
  );
  const view = useRangeView('var-history', params, workspaceService.varHistory);
  const data = view.data;
  const selected = data?.contributions[fund];

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
        <SelectField label="Method" value={method} options={METHODS} onChange={setMethod} />
        <NumberField label="Window" value={rollingWindow} min={10} onChange={setRollingWindow} />
        <NumberField
          label="VaR Centile"
          value={centile}
          step={0.01}
          min={0.01}
          max={0.49}
          onChange={setCentile}
        />
        <NumberField
          label="Iterations"
          value={iterations}
          step={500}
          min={100}
          onChange={setIterations}
        />
        <NumberField
          label="Stress Factor"
          value={stressFactor}
          step={0.1}
          min={1}
          max={3}
          onChange={setStressFactor}
        />
        <NumberField
          label="Mean Factor"
          value={meanFactor}
          step={0.1}
          min={0}
          max={3}
          onChange={setMeanFactor}
        />
        <RunButton onClick={view.run} loading={view.isFetching}>
          Get VaR
        </RunButton>
      </Toolbar>
      <ViewStatus {...view} />
      {data && !selected && <Notice>No Value at Risk history for {fund}: see the warnings.</Notice>}
      {data && (
        <Grid2>
          <FrameChart
            frame={data.var}
            title="Portfolios Value At Risk"
            format="percent"
            visible={[HISTORICAL, 'Fund']}
          />
          <FrameChart
            frame={data.cvar}
            title="Portfolio Expected Shortfall"
            format="percent"
            visible={[HISTORICAL, 'Fund']}
          />
          {selected && (
            <>
              <FrameChart
                frame={selected.var}
                title={`Value at Risk History — ${fund}`}
                format="percent"
                visible={['Portfolio']}
              />
              <FrameChart
                frame={selected.cvar}
                title={`Expected Shortfall History — ${fund}`}
                format="percent"
                visible={['Portfolio']}
              />
            </>
          )}
        </Grid2>
      )}
    </Panel>
  );
};

const VaRHistory = () => (
  <RequireAllocations>
    <VaRHistoryPage />
  </RequireAllocations>
);

export default VaRHistory;
