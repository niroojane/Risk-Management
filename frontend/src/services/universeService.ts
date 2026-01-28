import { apiClient } from './api';
import type { MarketCapData, PositionData } from '../types/universe';

export const universeService = {
  fetchMarketCap: async (): Promise<MarketCapData[]> => {
    const response = await apiClient.post('/api/v1/investment-universe/market-cap', {
      quote: "USDT"
    });
    return response.data.data;
  },

  fetchPositions: async (
    symbols: string[],
    startDate: string,
    endDate: string
  ): Promise<PositionData[]> => {
    const response = await apiClient.post('/api/v1/investment-universe/positions', {
      symbols,
      start_date: startDate,
      end_date: endDate,
    });
    return response.data;
  },
};
