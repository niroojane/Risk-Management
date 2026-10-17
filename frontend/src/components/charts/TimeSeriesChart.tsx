import { useEffect, useMemo, useRef, useState } from 'react';
import { ColorType, LineSeries, createChart } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, MouseEventParams, Time } from 'lightweight-charts';
import { cn } from '@/lib/utils';
import type { Frame } from '@/types/workspace';
import { chartTheme, formatValue, seriesColor } from './theme';
import type { ValueFormat } from './theme';

export interface TimeSeriesChartProps {
  frame: Frame;
  title: string;
  /** Series shown at first; the others start hidden and can be toggled from the legend */
  visible?: string[];
  format?: ValueFormat;
  height?: number;
}

/**
 * Date-indexed lines drawn with TradingView Lightweight Charts, with a clickable
 * legend (show / hide a series) that also displays the values under the crosshair.
 */
export const TimeSeriesChart = ({
  frame,
  title,
  visible,
  format = 'number',
  height = 360,
}: TimeSeriesChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const seriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());
  const [shown, setShown] = useState<Set<string>>(
    () => new Set(visible ? frame.columns.filter((c) => visible.includes(c)) : frame.columns)
  );
  // Read by the chart-building effect so a rebuild keeps the series the user toggled
  const shownRef = useRef(shown);
  const [hover, setHover] = useState<Map<string, number> | null>(null);

  const columns = frame.columns;
  const lastValues = useMemo(() => {
    const values = new Map<string, number>();
    columns.forEach((column, j) => {
      for (let i = frame.data.length - 1; i >= 0; i -= 1) {
        const v = frame.data[i][j];
        if (typeof v === 'number') {
          values.set(column, v);
          break;
        }
      }
    });
    return values;
  }, [frame, columns]);

  // (Re)build the chart when the data changes
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const theme = chartTheme();
    const chart: IChartApi = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: theme.text,
        fontSize: 11,
      },
      grid: { vertLines: { color: theme.grid }, horzLines: { color: theme.grid } },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.08, bottom: 0.08 } },
      timeScale: { borderVisible: false },
      localization: { priceFormatter: (price: number) => formatValue(price, format) },
    });

    const map = new Map<string, ISeriesApi<'Line'>>();
    frame.columns.forEach((column, j) => {
      const series = chart.addSeries(LineSeries, {
        color: seriesColor(j),
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        visible: shownRef.current.has(column),
      });
      series.setData(
        frame.index.map((time, i) => {
          const value = frame.data[i][j];
          return typeof value === 'number' ? { time: time as Time, value } : { time: time as Time };
        })
      );
      map.set(column, series);
    });
    seriesRef.current = map;
    chart.timeScale().fitContent();

    const onMove = (param: MouseEventParams) => {
      if (!param.time) {
        setHover(null);
        return;
      }
      const values = new Map<string, number>();
      map.forEach((series, column) => {
        const point = param.seriesData.get(series);
        if (point && 'value' in point) values.set(column, point.value);
      });
      setHover(values);
    };
    chart.subscribeCrosshairMove(onMove);

    return () => {
      chart.unsubscribeCrosshairMove(onMove);
      chart.remove();
      seriesRef.current = new Map();
    };
  }, [frame, format]);

  // Visibility changes are applied without rebuilding the chart
  useEffect(() => {
    shownRef.current = shown;
    seriesRef.current.forEach((series, column) =>
      series.applyOptions({ visible: shown.has(column) })
    );
  }, [shown]);

  const toggle = (column: string) =>
    setShown((prev) => {
      const next = new Set(prev);
      if (next.has(column)) next.delete(column);
      else next.add(column);
      return next;
    });

  const values = hover ?? lastValues;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      <div ref={containerRef} style={{ height }} />
      <div className="flex max-h-28 flex-wrap gap-x-3 gap-y-1 overflow-y-auto text-xs">
        {columns.map((column, j) => {
          const on = shown.has(column);
          const value = values.get(column);
          return (
            <button
              key={column}
              onClick={() => toggle(column)}
              className={cn(
                'flex items-center gap-1.5 rounded px-1 py-0.5 hover:bg-accent',
                !on && 'opacity-40'
              )}
              title={on ? 'Hide' : 'Show'}
            >
              <span
                className="inline-block size-2.5 rounded-sm"
                style={{ background: seriesColor(j) }}
              />
              <span>{column}</span>
              {on && value !== undefined && (
                <span className="tabular-nums text-muted-foreground">
                  {formatValue(value, format)}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
