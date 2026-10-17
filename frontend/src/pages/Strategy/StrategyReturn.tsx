import { useWorkspaceStore } from '@/store/workspaceStore';
import { RequireAllocations } from '../shared/Guards';
import { SeriesCalendar } from '../shared/SeriesCalendar';

/** Strategy > Strategy Return: calendar metrics of the strategy series */
const StrategyReturn = () => {
  const frequency = useWorkspaceStore((s) => s.frequency);
  return (
    <RequireAllocations>
      <SeriesCalendar
        viewKey="strategy-calendar"
        selectionKey="strategy-calendar"
        rangeKey="perf"
        frequency={frequency}
        includeHistorical={false}
        defaultFund="Fund"
        defaultBenchmark="Core"
      />
    </RequireAllocations>
  );
};

export default StrategyReturn;
