import { useMemo } from 'react';
import {
  Notice,
  Panel,
  RangeFields,
  RunButton,
  SelectField,
  Toolbar,
  ViewStatus,
} from '@/components/ui';
import { useSeriesNames, useView, useWorkspacePayload } from '@/hooks/useWorkspace';
import { useSeriesPair } from '@/hooks/useSeriesPair';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { RangeKey } from '@/store/workspaceStore';
import type { RebalancingFrequency } from '@/types/workspace';
import { CalendarCharts } from './CalendarCharts';
import { PairSelect } from './PairSelect';

interface SeriesCalendarProps {
  viewKey: string;
  /** Store key of the fund / benchmark choice (shared by the views using the same key) */
  selectionKey: string;
  rangeKey: RangeKey;
  frequency: RebalancingFrequency;
  includeHistorical: boolean;
  defaultFund: string;
  defaultBenchmark: string;
}

/** Calendar returns of a fund series vs a benchmark series (Strategy Return / Calendar Return) */
export const SeriesCalendar = ({
  viewKey,
  selectionKey,
  rangeKey,
  frequency,
  includeHistorical,
  defaultFund,
  defaultBenchmark,
}: SeriesCalendarProps) => {
  const names = useSeriesNames(includeHistorical);
  const pair = useSeriesPair(selectionKey, names, defaultFund, defaultBenchmark);
  const period = useWorkspaceStore((s) => s.selections[viewKey]?.period) ?? 'Year';
  const setSelection = useWorkspaceStore((s) => s.setSelection);
  const setPeriod = (value: 'Year' | 'Month') => setSelection(viewKey, { period: value });
  const distinct = pair.fund !== pair.benchmark;

  const workspace = useWorkspacePayload(rangeKey, frequency, includeHistorical);
  const params = useMemo(
    () =>
      workspace && distinct
        ? { ...workspace, fund: pair.fund, benchmark: pair.benchmark, period }
        : null,
    [workspace, distinct, pair.fund, pair.benchmark, period]
  );
  const view = useView(viewKey, params, workspaceService.calendar);

  return (
    <Panel>
      <Toolbar>
        <RangeFields rangeKey={rangeKey} />
        <SelectField
          label="Frequency"
          value={period}
          options={['Year', 'Month']}
          onChange={setPeriod}
        />
        <PairSelect
          names={names}
          fund={pair.fund}
          benchmark={pair.benchmark}
          onFund={pair.setFund}
          onBenchmark={pair.setBenchmark}
        />
        <RunButton onClick={view.run} loading={view.isFetching} disabled={!params}>
          Update Perf
        </RunButton>
      </Toolbar>
      {!distinct && <Notice>⚠️ Benchmark and Fund must be different.</Notice>}
      <ViewStatus {...view} />
      {view.data && <CalendarCharts view={view.data} period={period} />}
    </Panel>
  );
};
