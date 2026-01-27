export interface MarketCapData {
  symbol: string;
  price: number;
  market_cap: number;
  change_24h: number;
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
