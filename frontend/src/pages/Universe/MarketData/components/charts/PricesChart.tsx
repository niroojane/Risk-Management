import { LineChart } from '@/components/common';
import type { PriceRow } from '@/types/prices';

interface PricesChartProps {
  data: PriceRow[];
  symbols: string[];
}

export const PricesChart = ({ data, symbols }: PricesChartProps) => {
  return <LineChart data={data} variables={symbols} />;
};
