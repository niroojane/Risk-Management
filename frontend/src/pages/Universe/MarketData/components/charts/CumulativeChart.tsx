import { useMemo } from 'react';
import { LineChart } from '@/components/common';
import type { LineChartRow } from '@/components/common';
import type { PriceRow } from '@/types/prices';

interface CumulativeChartProps {
  data: PriceRow[];
  symbols: string[];
}

export const CumulativeChart = ({ data, symbols }: CumulativeChartProps) => {
  const cumulativeData = useMemo<LineChartRow[]>(() => {
    const firstRow = data[0];
    if (!firstRow) return [];

    return data.map((row) => {
      const point: LineChartRow = { date: row.date as string };
      symbols.forEach((symbol) => {
        const firstPrice = firstRow[symbol] as number;
        const currentPrice = row[symbol] as number;
        if (firstPrice && currentPrice) {
          point[symbol] = ((currentPrice / firstPrice) - 1) * 100;
        }
      });
      return point;
    });
  }, [data, symbols]);

  return <LineChart data={cumulativeData} variables={symbols} />;
};
