import { create } from 'zustand';

const DEFAULT_SYMBOLS = [
  'BNBUSDT',
  'BTCUSDT',
  'ETHUSDT',
  'GNOUSDT',
  'GUNUSDT',
  'IOTAUSDT',
  'POLUSDT',
  'TAOUSDT',
  'TONUSDT',
  'TRXUSDT',
  'UNIUSDT',
  'WLFIUSDT',
  'XLMUSDT',
];

interface UniverseState {
  symbols: string[];
  displayCount: number;
  setSymbols: (symbols: string[]) => void;
  setDisplayCount: (count: number) => void;
}

export const useUniverseStore = create<UniverseState>()((set) => ({
  symbols: DEFAULT_SYMBOLS,
  displayCount: 100,
  setSymbols: (symbols) => set({ symbols }),
  setDisplayCount: (displayCount) => set({ displayCount }),
}));
