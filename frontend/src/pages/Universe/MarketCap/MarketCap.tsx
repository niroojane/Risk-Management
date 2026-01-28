import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { universeService } from '../../../services/universeService';
import { MarketCapTable } from './components/MarketCapTable';
import { MarketCapFilter } from './components/MarketCapFilter';
import { ErrorMessage } from '../../../components/common/ErrorMessage';
import { Loading } from '../../../components/common/Loading';

function MarketCap() {
  const [topN, setTopN] = useState(50);

  const {
    data = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['marketCap'],
    queryFn: universeService.fetchMarketCap,
  });

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-foreground">Market Cap</h1>
        <MarketCapFilter topN={topN} maxValue={data.length} onChange={setTopN} />
      </div>

      {isLoading && <Loading text="Loading market cap data..." className="py-8" />}

      {error && (
        <ErrorMessage
          title="Failed to load market cap data"
          message={error instanceof Error ? error.message : 'An unexpected error occurred'}
        />
      )}

      {!isLoading && !error && <MarketCapTable data={data} topN={topN} />}
    </div>
  );
}

export default MarketCap;
