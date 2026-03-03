import { useEffect, useRef, useState } from 'react';
import { createChart, LineSeries, type IChartApi, type ISeriesApi, type UTCTimestamp } from 'lightweight-charts';

export interface LineChartRow {
  date: string;
  [variable: string]: string | number;
}

export interface LineChartProps {
  data: LineChartRow[];
  variables: string[];
  height?: number;
}

const SERIES_COLORS = [
  '#3b82f6', // blue
  '#f59e0b', // amber
  '#10b981', // emerald
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#14b8a6', // teal
  '#f97316', // orange
];

export const LineChart = ({ data, variables, height = 420 }: LineChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesMapRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());

  const [visibleVariables, setVisibleVariables] = useState<Set<string>>(
    () => new Set([variables[0]])
  );

  // Reset visibility when variables list changes
  useEffect(() => {
    setVisibleVariables(new Set([variables[0]]));
  }, [variables]);

  // Build chart and all series
  useEffect(() => {
    if (!containerRef.current) return;

    chartRef.current = createChart(containerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#94a3b8',
        fontFamily: 'inherit',
      },
      grid: {
        vertLines: { color: 'rgba(148, 163, 184, 0.08)' },
        horzLines: { color: 'rgba(148, 163, 184, 0.08)' },
      },
      crosshair: {
        vertLine: { color: 'rgba(148, 163, 184, 0.4)', width: 1, style: 3 },
        horzLine: { color: 'rgba(148, 163, 184, 0.4)', width: 1, style: 3 },
      },
      leftPriceScale: {
        visible: true,
        borderColor: 'rgba(148, 163, 184, 0.15)',
      },
      rightPriceScale: {
        visible: false,
      },
      timeScale: {
        borderColor: 'rgba(148, 163, 184, 0.15)',
        timeVisible: true,
      },
      width: containerRef.current.clientWidth,
      height,
    });

    seriesMapRef.current.clear();

    variables.forEach((variable, i) => {
      const isVisible = i === 0;

      const series = chartRef.current!.addSeries(LineSeries, {
        color: SERIES_COLORS[i % SERIES_COLORS.length],
        lineWidth: 2,
        title: variable,
        priceLineVisible: false,
        lastValueVisible: isVisible,
        priceScaleId: 'left',
        visible: isVisible,
      });

      const seriesData = data
        .filter((row) => row[variable] != null)
        .map((row) => ({
          time: Math.floor(new Date(row.date).getTime() / 1000) as UTCTimestamp,
          value: row[variable] as number,
        }))
        .sort((a, b) => a.time - b.time);

      series.setData(seriesData);
      seriesMapRef.current.set(variable, series);
    });

    chartRef.current.timeScale().fitContent();

    const observer = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chartRef.current?.remove();
      chartRef.current = null;
      seriesMapRef.current.clear();
    };
  }, [data, variables, height]);

  const toggleVariable = (variable: string) => {
    setVisibleVariables((prev) => {
      const next = new Set(prev);
      const willBeVisible = !next.has(variable);
      willBeVisible ? next.add(variable) : next.delete(variable);

      const series = seriesMapRef.current.get(variable);
      if (series) {
        series.applyOptions({ visible: willBeVisible, lastValueVisible: willBeVisible });
      }

      return next;
    });
  };

  return (
    <div className="bg-card rounded-lg border border-border p-4">
      <div className="mb-3 flex flex-wrap gap-2">
        {variables.map((variable, i) => {
          const isVisible = visibleVariables.has(variable);
          const color = SERIES_COLORS[i % SERIES_COLORS.length];
          return (
            <button
              key={variable}
              onClick={() => toggleVariable(variable)}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                isVisible
                  ? 'bg-muted text-foreground'
                  : 'text-muted-foreground opacity-40 hover:opacity-60'
              }`}
            >
              <span
                className="inline-block h-2 w-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: isVisible ? color : '#6b7280' }}
              />
              {variable}
            </button>
          );
        })}
      </div>
      <div ref={containerRef} />
    </div>
  );
};
