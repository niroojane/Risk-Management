export interface AssetReturnMetrics {
  symbol: string;
  total_return: number;
  ytd_return: number;
  annualized_return: number;
}

export interface AssetRiskMetrics {
  symbol: string;
  annualized_vol_daily: number;
  annualized_vol_3y_weekly: number;
  annualized_vol_5y_monthly: number;
  annualized_vol_since_inception_monthly: number;
  inception_year: number;
  cvar_parametric_95: number;
  max_drawdown: number;
  date_of_max_drawdown: string;
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
  risk?: AssetRiskMetrics[];
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
