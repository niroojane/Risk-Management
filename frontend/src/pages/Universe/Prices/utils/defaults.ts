import type { DateRange } from '../types/filters';

/** Symbols offered by the Prices explorer */
export const SYMBOLS = [
  'BTCUSDT',
  'ETHUSDT',
  'BNBUSDT',
  'TRXUSDT',
  'WLFIUSDT',
  'XLMUSDT',
  'TONUSDT',
  'UNIUSDT',
  'TAOUSDT',
  'POLUSDT',
  'GUNUSDT',
  'GNOUSDT',
  'IOTAUSDT',
];

export const getDefaultSymbols = (): string[] => SYMBOLS;

/** Last twelve months */
export const getDefaultDateRange = (): DateRange => {
  const today = new Date();
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(today.getFullYear() - 1);

  return {
    from: oneYearAgo,
    to: today,
  };
};
