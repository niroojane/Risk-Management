import { create } from 'zustand';
import type { DateRange } from '@/pages/Universe/MarketData/types/filters';

const getInitialDateRange = (): DateRange => {
  const today = new Date();
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(today.getFullYear() - 1);
  return { from: oneYearAgo, to: today };
};

interface FiltersState {
  dateRange: DateRange | undefined;
  setDateRange: (dateRange: DateRange | undefined) => void;
  showTable: boolean;
  setShowTable: (showTable: boolean) => void;
}

export const useFiltersStore = create<FiltersState>()((set) => ({
  dateRange: getInitialDateRange(),
  setDateRange: (dateRange) => set({ dateRange }),
  showTable: false,
  setShowTable: (showTable) => set({ showTable }),
}));
