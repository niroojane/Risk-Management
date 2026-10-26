import { useMemo } from 'react';
import type { EChartsCoreOption } from 'echarts/core';
import { EChart, formatValue } from '@/components/data';
import { useChartTheme } from '@/hooks/useTheme';
import type { Frame, PerformanceView } from '@/types/workspace';
import { frameColumn } from '@/utils/frame';

type Frontier = NonNullable<PerformanceView['frontier']>;

const points = (frame: Frame) => {
  const vol = frameColumn(frame, 'Volatility');
  const ret = frameColumn(frame, 'Returns');
  const sharpe = frameColumn(frame, 'Sharpe Ratio');
  return vol.map((v, i) => [v, ret[i], sharpe[i]]);
};

/** Efficient frontier coloured by Sharpe ratio, constrained frontier and the allocations */
export const FrontierChart = ({ frontier }: { frontier: Frontier }) => {
  const theme = useChartTheme();
  const option = useMemo<EChartsCoreOption>(() => {
    const indicators = frontier.indicators;
    const volatility = indicators.data[indicators.index.indexOf('Volatility')] ?? [];
    const returns = indicators.data[indicators.index.indexOf('Returns')] ?? [];
    const allocations = indicators.columns.map((name, j) => ({
      name,
      value: [volatility[j], returns[j]],
      itemStyle: { color: name === 'Optimal Portfolio' ? '#dc2626' : '#f97316' },
    }));
    const frontierPoints = points(frontier.frontier);
    const sharpe = frontierPoints
      .map((p) => p[2])
      .filter((v): v is number => typeof v === 'number');
    const percentAxis = {
      type: 'value',
      scale: true,
      axisLabel: { color: theme.muted, formatter: (v: number) => formatValue(v, 'percent') },
      splitLine: { lineStyle: { color: theme.grid } },
    };

    return {
      tooltip: {
        trigger: 'item',
        formatter: (p: { seriesName: string; name: string; value: number[] }) =>
          `${p.name || p.seriesName}<br/>Volatility: ${formatValue(p.value[0], 'percent')}` +
          `<br/>Returns: ${formatValue(p.value[1], 'percent')}`,
      },
      legend: { bottom: 0, textStyle: { color: theme.text } },
      grid: { left: 72, right: 16, top: 32, bottom: 56 },
      xAxis: { ...percentAxis, name: 'Volatility', nameLocation: 'middle', nameGap: 28 },
      yAxis: { ...percentAxis, name: 'Expected Return' },
      visualMap: sharpe.length
        ? {
            show: false,
            seriesIndex: 0,
            dimension: 2,
            min: Math.min(...sharpe),
            max: Math.max(...sharpe),
            inRange: { color: ['#c6dbef', '#08306b'] },
          }
        : undefined,
      series: [
        { name: 'Efficient Frontier', type: 'scatter', symbolSize: 7, data: frontierPoints },
        ...(frontier.constrained
          ? [
              {
                name: 'Frontier Constrained',
                type: 'scatter',
                symbolSize: 5,
                itemStyle: { color: '#ef4444', opacity: 0.6 },
                data: points(frontier.constrained),
              },
            ]
          : []),
        {
          name: 'Allocations',
          type: 'scatter',
          symbol: 'diamond',
          symbolSize: 11,
          data: allocations,
        },
      ],
    };
  }, [frontier, theme]);

  return <EChart option={option} title="Efficient Frontier" />;
};
