import { FrameChart } from '@/components/charts';
import type { DecompositionView } from '@/types/workspace';

/** Volatility / correlation / idiosyncratic contribution charts of a rolling decomposition */
export const DecompositionCharts = ({
  view,
  volatilityTitle = 'Volatility Contribution',
}: {
  view: DecompositionView;
  volatilityTitle?: string;
}) => (
  <>
    <FrameChart
      frame={view.vol_contribution}
      title={volatilityTitle}
      format="percent"
      visible={['Total Vol']}
    />
    <FrameChart
      frame={view.correlation_contribution}
      title="Correlation Contribution"
      format="percent"
      visible={['Total Correlation']}
    />
    <FrameChart
      frame={view.idiosyncratic_contribution}
      title="Idiosyncratic Contribution"
      format="percent"
      visible={['Total Idiosyncratic Vol']}
    />
  </>
);
