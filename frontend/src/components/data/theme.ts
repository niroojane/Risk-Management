/** Colours shared by the Lightweight Charts and ECharts charts, so a series keeps its colour */
export const PALETTE = [
  '#2563eb',
  '#f97316',
  '#16a34a',
  '#dc2626',
  '#9333ea',
  '#0891b2',
  '#ca8a04',
  '#db2777',
  '#4b5563',
  '#65a30d',
  '#7c3aed',
  '#0d9488',
  '#ea580c',
  '#be123c',
  '#1d4ed8',
  '#a16207',
  '#15803d',
  '#6d28d9',
  '#0369a1',
  '#b91c1c',
];

export const seriesColor = (i: number) => PALETTE[i % PALETTE.length];

export type ValueFormat = 'percent' | 'number';

export const formatValue = (value: number, format: ValueFormat): string =>
  format === 'percent'
    ? `${(value * 100).toFixed(2)}%`
    : value.toLocaleString(undefined, { maximumFractionDigits: Math.abs(value) < 10 ? 4 : 2 });

const CHART_THEMES = {
  light: { dark: false, text: '#262626', muted: '#737373', grid: 'rgba(0,0,0,0.07)' },
  dark: { dark: true, text: '#e5e5e5', muted: '#a3a3a3', grid: 'rgba(255,255,255,0.08)' },
};

export type ChartTheme = (typeof CHART_THEMES)['light'];

/** The same object for a given mode, so it can be a memo dependency (read it with useChartTheme) */
export const chartTheme = (dark: boolean): ChartTheme =>
  dark ? CHART_THEMES.dark : CHART_THEMES.light;
