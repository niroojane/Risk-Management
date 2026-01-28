import { useState, useEffect } from 'react';
import { universeService } from '../../services/universeService';
import type { MarketCapData } from '../../types/universe';
import { Slider } from '../../components/ui/slider';

function Universe() {
  const [data, setData] = useState<MarketCapData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [topN, setTopN] = useState(50);

  useEffect(() => {
    const loadMarketCap = async () => {
      try {
        setLoading(true);
        setError(null);
        const marketCapData = await universeService.fetchMarketCap();
        setData(marketCapData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load market cap data');
        console.error('Error loading market cap:', err);
      } finally {
        setLoading(false);
      }
    };

    loadMarketCap();
  }, []);

  const handleTopNChange = (value: number[]) => {
    setTopN(value[0]);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-foreground">Investment Universe</h1>

        <div className="flex items-center gap-4 pr-4">
          <label className="text-sm text-muted-foreground">
            Top {topN} / {data.length}
          </label>
          <Slider
            min={1}
            max={data.length}
            step={1}
            value={[topN]}
            onValueChange={handleTopNChange}
            className="w-58"
          />
        </div>
      </div>

      {loading && (
        <div className="text-center py-8 text-muted-foreground">
          Loading market cap data...
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Rank
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Asset
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Symbol
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Price (USD)
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Supply
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Market Cap
                </th>
              </tr>
            </thead>
            <tbody className="bg-card divide-y divide-border">
              {data.slice(0, topN).map((row, index) => (
                <tr key={row.symbol} className="hover:bg-muted/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                    {index + 1}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-foreground">
                        {row.long_name}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {row.base_asset}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-foreground">
                    {row.symbol}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-foreground">
                    ${row.price.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2
                    })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-foreground">
                    {row.supply.toLocaleString(undefined, {
                      maximumFractionDigits: 0
                    })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-foreground">
                    ${(row.market_cap / 1e9).toFixed(2)}B
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Universe;
