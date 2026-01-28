import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { universeService } from '../../services/universeService';
import { MarketCapTable } from './components/MarketCapTable';
import { UniverseFilters } from './components/UniverseFilters';

function Universe() {
  const [topN, setTopN] = useState(50);

  const {
    data = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['marketCap'],
    queryFn: universeService.fetchMarketCap,
  });

  const handleTopNChange = (value: number[]) => {
    setTopN(value[0]);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-foreground">Investment Universe</h1>
        <UniverseFilters topN={topN} maxValue={data.length} onChange={handleTopNChange} />
      </div>

      {isLoading && (
        <div className="text-center py-8 text-muted-foreground">
          Loading market cap data...
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error instanceof Error ? error.message : 'Failed to load market cap data'}
        </div>
      )}

      {!isLoading && !error && <MarketCapTable data={data} topN={topN} />}
    </div>
  );
}

export default Universe;
