import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import type { EChartsCoreOption } from 'echarts/core';
import { BarChart, HeatmapChart, ScatterChart } from 'echarts/charts';
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { chartTheme } from './theme';

// Only the chart types the app uses are bundled
echarts.use([
  BarChart,
  HeatmapChart,
  ScatterChart,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

export interface EChartProps {
  option: EChartsCoreOption;
  /** Shown above the chart, like the Lightweight Charts titles */
  title?: string;
  height?: number;
}

/** Thin wrapper around an ECharts instance: replaces the option on change, resizes with its box */
export const EChart = ({ option, title, height = 400 }: EChartProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const chart = echarts.init(element, chartTheme().dark ? 'dark' : undefined);
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const theme = chartTheme();
    chartRef.current?.setOption(
      {
        backgroundColor: 'transparent',
        textStyle: { color: theme.text },
        ...option,
      },
      true
    );
  }, [option]);

  return (
    <div className="space-y-2">
      {title && <h3 className="text-sm font-semibold text-foreground">{title}</h3>}
      <div ref={ref} style={{ width: '100%', height }} />
    </div>
  );
};
