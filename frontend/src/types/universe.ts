export interface MarketCapData {
  symbol: string;
  long_name: string;
  base_asset: string;
  quote_asset: string;
  price: number;
  supply: number;
  market_cap: number;
}

export interface PositionData {
  asset: string;
  quantity: number;
  value_usdt: number;
  weight: number;
}

export interface PriceHistoryData {
  date: string;
  prices: Record<string, number>;
}
