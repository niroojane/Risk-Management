import type { PricesResponse } from '@/types/universe';
import type { AssetMetrics } from '@/types/universe';
import type { Cell, Frame } from '@/types/workspace';

/** The notebook keeps assets with fewer than 30 missing daily returns */
const MAX_MISSING_RETURNS = 30;

export const pricesToFrame = (response: PricesResponse): Frame => {
  const byDate = response.data.data;
  const index = Object.keys(byDate).sort();
  const columns = response.data.symbols.filter((s) => index.some((d) => byDate[d][s] != null));
  return {
    index,
    columns,
    data: index.map((d) => columns.map((s) => byDate[d][s] ?? null)),
  };
};

export const validSymbols = (response: PricesResponse, tickers: string[]) => {
  const byDate = response.data.data;
  const dates = Object.keys(byDate);
  const valid: string[] = [];
  const excluded: string[] = [];
  for (const ticker of tickers) {
    const missing = dates.filter((d) => byDate[d][ticker] == null).length;
    // + 1: the first return of every asset is missing
    (dates.length > 0 && missing + 1 < MAX_MISSING_RETURNS ? valid : excluded).push(ticker);
  }
  return { valid, excluded };
};

export const windowFrame = (frame: Frame, start: string, end: string): Frame => {
  const rows = frame.index
    .map((date, i) => [date, i] as const)
    .filter(([date]) => date >= start && date <= end);
  return {
    index: rows.map(([date]) => date),
    columns: frame.columns,
    data: rows.map(([, i]) => frame.data[i]),
  };
};

/** Base 100 at the first date, compounding daily returns (missing returns count as 0) */
export const cumulativePerformance = (prices: Frame): Frame => {
  const data: Cell[][] = [];
  prices.data.forEach((row, i) => {
    if (i === 0) {
      data.push(row.map(() => 100));
      return;
    }
    data.push(
      row.map((price, j) => {
        const previousPrice = prices.data[i - 1][j];
        const level = data[i - 1][j] as number;
        return typeof price === 'number' && typeof previousPrice === 'number' && previousPrice
          ? level * (price / previousPrice)
          : level;
      })
    );
  });
  return { index: prices.index, columns: prices.columns, data };
};

/** Asset return and risk tables (metrics as rows, assets as columns) as in the notebook */
export const buildAssetTables = (metrics: AssetMetrics[], start: string, end: string) => {
  const columns = metrics.map((m) => m.symbol);
  const table = (rows: [string, keyof AssetMetrics][]): Frame => ({
    index: rows.map(([label]) => label),
    columns,
    data: rows.map(([, key]) => metrics.map((m) => m[key] as Cell)),
  });
  return {
    returns: table([
      [`Returns since ${start}`, 'total_return'],
      [`Returns since ${end.slice(0, 4)}-01-01`, 'ytd_return'],
      ['Annualized Returns', 'annualized_return'],
    ]),
    risk: table([
      ['Annualized Volatility (daily)', 'volatility_1y_daily'],
      ['Annualized Volatility 3Y (Weekly)', 'volatility_3y_weekly'],
      ['Annualized Volatility 5Y (Monthly)', 'volatility_5y_monthly'],
      [`Annualized Volatility since ${start.slice(0, 4)} (Monthly)`, 'volatility_monthly'],
      ['CVar Parametric 95%', 'cvar_parametric_95'],
      ['Max Drawdown', 'max_drawdown'],
      ['Date of Max Drawdown', 'max_drawdown_date'],
    ]),
  };
};
