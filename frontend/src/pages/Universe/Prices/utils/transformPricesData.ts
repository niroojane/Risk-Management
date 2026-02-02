import type { PricesResponse, PriceRow } from '@/types/prices';

export const transformPricesData = (response: PricesResponse): PriceRow[] => {
  const pricesData = response.data.data;

  return Object.entries(pricesData).map(([date, prices]) => ({
    date,
    ...prices,
  }));
};
