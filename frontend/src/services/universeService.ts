import { apiClient } from './api';
import type { AssetMetrics, MarketCapData } from '../types/universe';
import type { PricesResponse } from '../types/prices';
import type { ViewResponse } from '../types/workspace';

export const universeService = {
  fetchMarketCap: async (): Promise<MarketCapData[]> => {
    const response = await apiClient.post('/api/v1/investment-universe/market-cap', {
      quote: 'USDT',
    });
    return response.data.data;
  },

  fetchAssetMetrics: async (params: {
    symbols: string[];
    start_date: string;
    end_date: string;
  }): Promise<ViewResponse<AssetMetrics[]>> => {
    const response = await apiClient.post('/api/v1/investment-universe/asset-metrics', params);
    return response.data;
  },

  fetchPrices: async (
    symbols: string[],
    startDate: string,
    endDate: string
  ): Promise<PricesResponse> => {
    const response = await apiClient.post(
      '/api/v1/investment-universe/prices',
      { symbols, start_date: startDate, end_date: endDate },
      { timeout: 15 * 60 * 1000 }
    );
    return response.data;
  },
};
