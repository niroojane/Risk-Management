export interface AssetReturnMetrics {
  symbol: string;
  total_return: number;
  ytd_return: number;
  annualized_return: number;
}

export interface MarketReturnsData {
  period_start_date: string;
  ytd_start_date: string;
  assets: AssetReturnMetrics[];
}

export interface MarketDataSnapshot {
  symbols: string[];
  start_date: string;
  end_date: string;
  prices: {
    [date: string]: {
      [symbol: string]: number;
    };
  };
  count: number;
  returns?: MarketReturnsData;
  timestamp: string;
}

export interface PricesResponse {
  success: boolean;
  data: MarketDataSnapshot;
  message: string;
  timestamp: string;
}

export interface PriceRow {
  date: string;
  [symbol: string]: string | number;
}
