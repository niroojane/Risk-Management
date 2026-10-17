import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { universeService } from '@/services/universeService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { apiErrorMessage, useBenchmark } from '@/hooks/useWorkspace';
import { useProfile } from '@/hooks/useProfile';
import { Slider } from '@/components/ui/slider';
import { FrameChart } from '@/components/charts';
import {
  DataTable,
  DateField,
  Field,
  Grid2,
  Notice,
  Panel,
  RunButton,
  Toolbar,
} from '@/components/workspace';
import { Loading } from '@/components/common';
import { formatMarketCap, formatUSD } from '@/utils/formatters';
import type { Profile } from '@/types/profile';
import { AssetMetricsTables } from '../../shared/AssetMetricsTables';
import { cumulativePerformance, pricesToFrame, windowFrame } from './universe';
import { LoadStatus } from './LoadUniverse';
import { useLoadUniverse } from './useLoadUniverse';
import { YahooScope } from './YahooScope';

/** Crypto: top N of the Binance market caps */
const CryptoScope = () => {
  const { nCrypto, startDate, unchecked, setNCrypto, setStartDate, toggleTicker } =
    useWorkspaceStore();
  const load = useLoadUniverse();

  const marketCap = useQuery({
    queryKey: ['marketCap'],
    queryFn: universeService.fetchMarketCap,
  });
  const topN = useMemo(
    () =>
      (marketCap.data ?? [])
        .filter((item) => !item.long_name.includes('(bStocks)'))
        .slice(0, nCrypto),
    [marketCap.data, nCrypto]
  );
  const selected = topN.map((item) => item.symbol).filter((t) => !unchecked.includes(t));

  return (
    <Panel title="Scope">
      <Toolbar>
        <Field label={`Number of Crypto: ${nCrypto}`} className="w-80">
          <Slider
            min={1}
            max={100}
            value={[nCrypto]}
            onValueChange={([value]) => setNCrypto(value)}
            className="py-3"
          />
        </Field>
        <DateField label="Starting Date of Backtest" value={startDate} onChange={setStartDate} />
        <RunButton onClick={() => load.mutate(selected)} loading={load.isPending}>
          Get Prices
        </RunButton>
      </Toolbar>

      <LoadStatus load={load} />

      {marketCap.isLoading && <Loading text="Loading market caps..." />}
      {marketCap.error && <Notice tone="error">{apiErrorMessage(marketCap.error)}</Notice>}
      {topN.length > 0 && (
        <div
          className="overflow-auto rounded-md border border-border"
          style={{ maxHeight: '40vh' }}
        >
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 bg-muted">
              <tr>
                <th className="px-3 py-2 text-left">Selected</th>
                <th className="px-3 py-2 text-left">Ticker</th>
                <th className="px-3 py-2 text-left">Long name</th>
                <th className="px-3 py-2 text-right">Close</th>
                <th className="px-3 py-2 text-right">Market Cap</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {topN.map((item) => (
                <tr key={item.symbol} className="hover:bg-accent/50">
                  <td className="px-3 py-1.5">
                    <input
                      type="checkbox"
                      checked={!unchecked.includes(item.symbol)}
                      onChange={() => toggleTicker(item.symbol)}
                      aria-label={`Select ${item.symbol}`}
                    />
                  </td>
                  <td className="px-3 py-1.5 font-medium">{item.symbol}</td>
                  <td className="px-3 py-1.5">{item.long_name}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{formatUSD(item.price)}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {formatMarketCap(item.market_cap)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-muted-foreground">
        Selected tickers ({selected.length}): {selected.join(', ')}
      </p>
    </Panel>
  );
};

const currencyKey = (profile: Profile) =>
  profile.currency.convert_to_base ? profile.currency.base_currency : 'local';

const InvestmentUniverse = () => {
  const profile = useProfile();
  const benchmark = useBenchmark();
  const universe = useWorkspaceStore((s) => s.universe);
  const perf = useWorkspaceStore((s) => s.ranges.perf);

  // Prices of the loaded universe (refetched from the backend cache if evicted)
  const prices = useQuery({
    queryKey: [
      'universe-prices',
      universe?.symbols,
      universe?.start,
      universe?.end,
      currencyKey(profile),
    ],
    queryFn: () => universeService.fetchPrices(universe!.symbols, universe!.start, universe!.end),
    enabled: !!universe,
    staleTime: Infinity,
  });
  const priceFrame = useMemo(
    () => (prices.data ? pricesToFrame(prices.data) : null),
    [prices.data]
  );
  const windowPrices = useMemo(
    () => (priceFrame ? windowFrame(priceFrame, perf.start, perf.end) : null),
    [priceFrame, perf]
  );
  const cumulative = useMemo(
    () => (windowPrices ? cumulativePerformance(windowPrices) : null),
    [windowPrices]
  );
  const visible = windowPrices?.columns.includes(benchmark.ticker)
    ? [benchmark.ticker]
    : windowPrices?.columns.slice(0, 1);

  return (
    <div className="space-y-6">
      {profile.name === 'multi_asset' ? <YahooScope /> : <CryptoScope />}

      {universe && (
        <Panel title="Assets">
          <AssetMetricsTables />

          {prices.isFetching && <Loading text="Loading prices..." />}
          {prices.error && <Notice tone="error">{apiErrorMessage(prices.error)}</Notice>}
          {windowPrices && (
            <>
              <Grid2>
                <FrameChart frame={windowPrices} title="Price" visible={visible} />
                <FrameChart frame={cumulative} title="Cumulative Performance" visible={visible} />
              </Grid2>
              <DataTable frame={windowPrices} indexLabel="Date" decimals={6} />
            </>
          )}
        </Panel>
      )}
    </div>
  );
};

export default InvestmentUniverse;
