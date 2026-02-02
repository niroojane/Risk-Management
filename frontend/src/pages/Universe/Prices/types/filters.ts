export interface DateRange {
  from: Date | undefined;
  to?: Date | undefined;
}

export interface PricesFilters {
  symbols: string[];
  dateRange: DateRange | undefined;
}
