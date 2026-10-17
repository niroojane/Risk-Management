import { FrameChart } from '@/components/charts';
import { Grid2 } from '@/components/workspace';
import type { CalendarView } from '@/types/workspace';

/** Returns / Volatility / Tracking Error / Sharpe Ratio bars by period (notebook's get_calendar_graph) */
export const CalendarCharts = ({
  view,
  period,
}: {
  view: CalendarView;
  period: 'Year' | 'Month';
}) => (
  <Grid2>
    <FrameChart frame={view.returns} title={`Returns by ${period}`} kind="bar" format="percent" />
    <FrameChart
      frame={view.volatility}
      title={`Volatility by ${period}`}
      kind="bar"
      format="percent"
    />
    <FrameChart
      frame={view.tracking_error}
      title={`Tracking Error by ${period}`}
      kind="bar"
      format="percent"
    />
    <FrameChart frame={view.sharpe_ratio} title={`Sharpe Ratio by ${period}`} kind="bar" />
  </Grid2>
);
