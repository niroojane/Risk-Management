import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { universeService } from '@/services/universeService';
import { useUniverseStore } from '@/stores/universeStore';
import { useFiltersStore } from '@/stores/filtersStore';

export const useMarketData = () => {
  const { symbols } = useUniverseStore();
  const { dateRange } = useFiltersStore();

  return useQuery({
    queryKey: ['prices', symbols, dateRange],
    queryFn: async () => {
      if (!dateRange?.from || !dateRange?.to) {
        throw new Error('Date range is required');
      }
      const startDate = format(dateRange.from, 'yyyy-MM-dd');
      const endDate = format(dateRange.to, 'yyyy-MM-dd');
      return universeService.fetchMarketData(symbols, startDate, endDate);
    },
    enabled: false,
  });
};
