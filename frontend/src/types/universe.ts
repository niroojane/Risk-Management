export interface MarketCapData {
  symbol: string;
  long_name: string;
  base_asset: string;
  quote_asset: string;
  price: number;
  supply: number;
  market_cap: number;
}

export interface AssetMetrics {
  symbol: string;
  total_return: number | null;
  ytd_return: number | null;
  annualized_return: number | null;
  volatility_1y_daily: number | null;
  volatility_3y_weekly: number | null;
  volatility_5y_monthly: number | null;
  volatility_monthly: number | null;
  cvar_parametric_95: number | null;
  max_drawdown: number | null;
  max_drawdown_date: string | null;
}

export interface PricesResponse {
  success: boolean;
  data: {
    symbols: string[];
    start_date: string;
    end_date: string;
    data: {
      [date: string]: {
        [symbol: string]: number;
      };
    };
  };
}
