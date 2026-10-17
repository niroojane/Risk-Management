import { apiClient } from './api';
import type { Profile, TickerCheck } from '../types/profile';
import type { Frame, ViewResponse } from '../types/workspace';

const YAHOO_TIMEOUT = 5 * 60 * 1000;

export const profileService = {
  fetchProfile: async (): Promise<Profile> => {
    const response = await apiClient.get('/api/v1/profile');
    return response.data.data;
  },

  updateCurrency: async (patch: {
    base_currency?: string;
    convert_to_base?: boolean;
  }): Promise<Profile> => {
    const response = await apiClient.put('/api/v1/profile/currency', patch);
    return response.data.data;
  },

  /** Yahoo symbol search: Symbol (index), Name, Type, Exchange, Asset Class */
  search: async (q: string): Promise<ViewResponse<{ results: Frame }>> => {
    const response = await apiClient.get('/api/v1/universe/search', {
      params: { q },
      timeout: YAHOO_TIMEOUT,
    });
    return response.data;
  },

  /** Ticker details from Yahoo (one row per ticker) */
  details: async (params: {
    tickers: string[];
    refresh?: boolean;
  }): Promise<ViewResponse<{ details: Frame }>> => {
    const response = await apiClient.post('/api/v1/universe/details', params, {
      timeout: YAHOO_TIMEOUT,
    });
    return response.data;
  },

  check: async (ticker: string, assetClass?: string): Promise<ViewResponse<TickerCheck>> => {
    const response = await apiClient.post(
      '/api/v1/universe/check',
      { ticker, asset_class: assetClass || null },
      { timeout: YAHOO_TIMEOUT }
    );
    return response.data;
  },
};
