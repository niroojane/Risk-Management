import type { PricesResponse, PriceRow } from '@/types/prices';

export const transformPricesData = (response: PricesResponse): PriceRow[] => {
  const pricesData = response.data.prices;

  return Object.entries(pricesData).map(([date, prices]) => ({
    date,
    ...prices,
  }));
};
