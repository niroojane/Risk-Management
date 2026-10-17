import { useMemo } from 'react';
import type { EChartsCoreOption } from 'echarts/core';
import type { Frame } from '@/types/workspace';
import { EChart } from './EChart';
import { TimeSeriesChart } from './TimeSeriesChart';
import { PALETTE, chartTheme, formatValue } from './theme';
import type { ValueFormat } from './theme';

export interface FrameChartProps {
  frame: Frame | null | undefined;
  title: string;
  kind?: 'line' | 'bar';
  /** Series shown at first; the others start hidden and can be toggled from the legend */
  visible?: string[];
  format?: ValueFormat;
  barmode?: 'group' | 'relative' | 'stack';
  height?: number;
}

/**
 * One series per column of a frame, x = index.
 * Lines over dates use TradingView Lightweight Charts, bars use ECharts.
 */
export const FrameChart = ({
  frame,
  title,
  kind = 'line',
  visible,
  format = 'number',
  barmode = 'group',
  height,
}: FrameChartProps) => {
  if (!frame || frame.index.length === 0) return null;
  if (kind === 'line') {
    return (
      <TimeSeriesChart
        // a new set of series starts again from the default visibility
        key={frame.columns.join('|')}
        frame={frame}
        title={title}
        visible={visible}
        format={format}
        height={height}
      />
    );
  }
  return (
    <BarFrameChart
      frame={frame}
      title={title}
      visible={visible}
      format={format}
      barmode={barmode}
      height={height}
    />
  );
};

const BarFrameChart = ({
  frame,
  title,
  visible,
  format = 'number',
  barmode,
  height = 400,
}: FrameChartProps & { frame: Frame }) => {
  // Compared by content: pages pass a new array on every render, and rebuilding the
  // option would undo the series the user toggled in the legend
  const visibleKey = visible?.join('\u0000');
  const option = useMemo<EChartsCoreOption>(() => {
    const shown = visibleKey?.split('\u0000');
    const theme = chartTheme();
    const long = frame.index.length > 60;
    const stacked = barmode === 'relative' || barmode === 'stack';
    return {
      color: PALETTE,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        valueFormatter: (v: number) => (typeof v === 'number' ? formatValue(v, format) : '—'),
      },
      legend: {
        type: 'scroll',
        bottom: 0,
        textStyle: { color: theme.text },
        selected: shown
          ? Object.fromEntries(frame.columns.map((c) => [c, shown.includes(c)]))
          : undefined,
      },
      grid: { left: 64, right: 16, top: 16, bottom: long ? 84 : 48 },
      xAxis: { type: 'category', data: frame.index, axisLabel: { color: theme.muted } },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: theme.muted,
          formatter: (v: number) => formatValue(v, format),
        },
        splitLine: { lineStyle: { color: theme.grid } },
      },
      dataZoom: long ? [{ type: 'inside' }, { type: 'slider', bottom: 28, height: 18 }] : undefined,
      series: frame.columns.map((column, j) => ({
        name: column,
        type: 'bar',
        stack: stacked ? 'total' : undefined,
        stackStrategy: barmode === 'relative' ? 'samesign' : undefined,
        large: long,
        data: frame.data.map((row) => row[j]),
      })),
    };
  }, [frame, visibleKey, format, barmode]);

  return <EChart option={option} title={title} height={height} />;
};

export interface HeatmapChartProps {
  frame: Frame | null | undefined;
  title: string;
  height?: number;
}

/** Annotated heatmap (correlation matrices) */
export const HeatmapChart = ({ frame, title, height = 450 }: HeatmapChartProps) => {
  const option = useMemo<EChartsCoreOption | null>(() => {
    if (!frame) return null;
    const theme = chartTheme();
    const cells: [number, number, number | null][] = [];
    const numbers: number[] = [];
    frame.data.forEach((row, y) =>
      row.forEach((value, x) => {
        const v = typeof value === 'number' ? value : null;
        cells.push([x, y, v]);
        if (v !== null) numbers.push(v);
      })
    );
    return {
      tooltip: {
        formatter: (p: { value: [number, number, number] }) =>
          `${frame.index[p.value[1]]} / ${frame.columns[p.value[0]]}: ${p.value[2]?.toFixed(2)}`,
      },
      grid: { left: 90, right: 16, top: 8, bottom: 70 },
      xAxis: {
        type: 'category',
        data: frame.columns,
        axisLabel: { color: theme.muted, rotate: 45 },
        splitArea: { show: true },
      },
      yAxis: {
        type: 'category',
        data: frame.index,
        inverse: true,
        axisLabel: { color: theme.muted },
        splitArea: { show: true },
      },
      // colour only: every cell is labelled with its value
      visualMap: {
        show: false,
        min: Math.min(...numbers),
        max: Math.max(...numbers),
        inRange: { color: ['#f7fbff', '#6baed6', '#08306b'] },
      },
      series: [
        {
          type: 'heatmap',
          data: cells,
          label: {
            show: frame.columns.length <= 15,
            formatter: (p: { value: [number, number, number] }) => p.value[2]?.toFixed(2) ?? '',
          },
          itemStyle: { borderColor: 'transparent', borderWidth: 2 },
        },
      ],
    };
  }, [frame]);

  if (!option) return null;
  return <EChart option={option} title={title} height={height} />;
};
