import { HISTORICAL } from '@/hooks/useWorkspace';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { RequireUniverse } from '../shared/Guards';
import { SeriesCalendar } from '../shared/SeriesCalendar';

/** Current Portfolio > Calendar Return: realized portfolio vs the strategy series */
const CalendarReturn = () => {
  const pnlFrequency = useWorkspaceStore((s) => s.pnlFrequency);
  const historical = useWorkspaceStore((s) => s.historicalEnabled);
  return (
    <RequireUniverse>
      <SeriesCalendar
        viewKey="expost-calendar"
        selectionKey="expost"
        rangeKey="expost"
        frequency={pnlFrequency}
        includeHistorical={historical}
        defaultFund={HISTORICAL}
        defaultBenchmark="Fund"
      />
    </RequireUniverse>
  );
};

export default CalendarReturn;
