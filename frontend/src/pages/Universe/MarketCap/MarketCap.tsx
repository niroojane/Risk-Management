import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { universeService } from '@/services/universeService';
import { apiErrorMessage } from '@/hooks/useWorkspace';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Field, Loading, Notice, Panel, Toolbar } from '@/components/ui';
import { DataTable } from '@/components/data';
import type { Frame } from '@/types/workspace';

/** Binance market caps, largest first */
const MarketCap = () => {
  const [displayCount, setDisplayCount] = useState(100);
  const [search, setSearch] = useState('');
  const marketCap = useQuery({
    queryKey: ['marketCap'],
    queryFn: universeService.fetchMarketCap,
  });

  const frame = useMemo<Frame | null>(() => {
    if (!marketCap.data) return null;
    const term = search.trim().toLowerCase();
    const rows = marketCap.data
      .slice(0, displayCount)
      .filter(
        (item) =>
          !term ||
          item.symbol.toLowerCase().includes(term) ||
          item.long_name.toLowerCase().includes(term)
      );
    return {
      index: rows.map((item) => item.long_name),
      columns: ['Symbol', 'Price (USD)', 'Supply', 'Market Cap'],
      data: rows.map((item) => [item.symbol, item.price, item.supply, item.market_cap]),
    };
  }, [marketCap.data, displayCount, search]);

  const total = marketCap.data?.length ?? 0;
  return (
    <Panel title="Market Cap">
      <Toolbar>
        <Field label={`Number of assets: ${Math.min(displayCount, total)}`} className="w-80">
          <Slider
            min={1}
            max={Math.max(total, 1)}
            value={[displayCount]}
            onValueChange={([value]) => setDisplayCount(value)}
            className="py-3"
          />
        </Field>
        <Field label="Search">
          <Input
            className="w-60"
            placeholder="Symbol or name"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </Field>
      </Toolbar>
      {marketCap.isLoading && <Loading text="Loading market caps..." />}
      {marketCap.error && <Notice tone="error">{apiErrorMessage(marketCap.error)}</Notice>}
      <DataTable frame={frame} indexLabel="Asset" decimals={2} maxHeight="70vh" />
    </Panel>
  );
};

export default MarketCap;
