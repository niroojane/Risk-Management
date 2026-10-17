import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  DataTable,
  DateField,
  Field,
  Notice,
  Panel,
  RunButton,
  SelectField,
  Toolbar,
  ViewStatus,
} from '@/components/workspace';
import { Loading } from '@/components/common';
import { PROFILE_KEY, useProfile } from '@/hooks/useProfile';
import { apiErrorMessage, useView } from '@/hooks/useWorkspace';
import { profileService } from '@/services/profileService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { Profile, UniverseTicker } from '@/types/profile';
import type { Frame } from '@/types/workspace';
import { LoadStatus } from './LoadUniverse';
import { useLoadUniverse } from './useLoadUniverse';

const AUTO = '';

const defaultTickers = (profile: Profile): UniverseTicker[] =>
  Object.entries(profile.default_universe).flatMap(([assetClass, tickers]) =>
    tickers.map((ticker) => ({ ticker, assetClass }))
  );

/** Value of a frame cell by row / column name */
const cell = (frame: Frame | undefined, row: string, column: string) => {
  if (!frame) return null;
  const i = frame.index.indexOf(row);
  const j = frame.columns.indexOf(column);
  return i < 0 || j < 0 ? null : frame.data[i][j];
};

/** Multi-asset universe: Yahoo tickers by asset class, kept in the browser */
export const YahooScope = () => {
  const profile = useProfile();
  const queryClient = useQueryClient();
  const { startDate, setStartDate, unchecked, toggleTicker, yahooTickers, setYahooTickers } =
    useWorkspaceStore();
  const tickers = useMemo(() => yahooTickers ?? defaultTickers(profile), [yahooTickers, profile]);
  const names = useMemo(() => tickers.map((t) => t.ticker), [tickers]);
  const selected = names.filter((t) => !unchecked.includes(t));
  const classes = useMemo(
    () => Array.from(new Set([...profile.asset_classes, ...tickers.map((t) => t.assetClass)])),
    [profile.asset_classes, tickers]
  );
  const load = useLoadUniverse();

  const setTickers = (next: UniverseTicker[]) => setYahooTickers(next);
  const remove = (ticker: string) => setTickers(tickers.filter((t) => t.ticker !== ticker));
  const changeClass = (ticker: string, assetClass: string) =>
    setTickers(tickers.map((t) => (t.ticker === ticker ? { ...t, assetClass } : t)));

  // Add a ticker once Yahoo confirms it has prices
  const [newTicker, setNewTicker] = useState('');
  const [newClass, setNewClass] = useState(AUTO);
  const add = useMutation({
    mutationFn: ({ ticker, assetClass }: { ticker: string; assetClass: string }) =>
      profileService.check(ticker, assetClass || undefined),
    onSuccess: ({ data }) => {
      const ticker = data.ticker.toUpperCase();
      if (!names.includes(ticker))
        setTickers([...tickers, { ticker, assetClass: data.asset_class }]);
      setNewTicker('');
    },
  });
  const addTicker = (ticker: string, assetClass = newClass) => {
    const symbol = ticker.trim().toUpperCase();
    if (symbol && !names.includes(symbol)) add.mutate({ ticker: symbol, assetClass });
  };

  // Yahoo symbol search
  const [query, setQuery] = useState('');
  const [submitted, setSubmitted] = useState('');
  const search = useQuery({
    queryKey: ['yahoo-search', submitted],
    queryFn: () => profileService.search(submitted),
    enabled: submitted.length > 0,
    staleTime: Infinity,
    retry: false,
  });
  const results = search.data?.data.results;

  // Ticker details (name, currency, sector, liquidity, fees...)
  const detailParams = useMemo(() => (names.length ? { tickers: names } : null), [names]);
  const details = useView('yahoo-details', detailParams, profileService.details, true);
  const refreshDetails = useMutation({
    mutationFn: () => profileService.details({ tickers: names, refresh: true }),
    onSuccess: (response) =>
      queryClient.setQueryData(['view', 'yahoo-details', detailParams], response),
  });
  const detailFrame = details.data?.details;

  // Base currency: prices and every result are reported in it
  const currency = useMutation({
    mutationFn: profileService.updateCurrency,
    onSuccess: (updated) => {
      queryClient.setQueryData(PROFILE_KEY, updated);
      // results computed in the previous currency are dropped
      void queryClient.resetQueries({
        predicate: (q) =>
          !['profile', 'yahoo-search'].includes(String(q.queryKey[0])) &&
          q.queryKey[1] !== 'yahoo-details',
      });
    },
  });

  const grouped = classes
    .map((assetClass) => ({
      assetClass,
      rows: tickers.filter((t) => t.assetClass === assetClass),
    }))
    .filter((g) => g.rows.length > 0);

  return (
    <>
      <Panel title="Scope">
        <Toolbar>
          <DateField label="Starting Date of Backtest" value={startDate} onChange={setStartDate} />
          <SelectField
            label="Base currency"
            value={profile.currency.base_currency}
            options={profile.currency.choices}
            onChange={(base_currency) => currency.mutate({ base_currency })}
            selectClassName="w-28"
          />
          <label className="flex h-9 items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={profile.currency.convert_to_base}
              onChange={(e) => currency.mutate({ convert_to_base: e.target.checked })}
            />
            Convert prices to {profile.currency.base_currency}
          </label>
          <RunButton
            onClick={() => {
              currency.reset();
              load.mutate(selected);
            }}
            loading={load.isPending}
          >
            Get Prices
          </RunButton>
        </Toolbar>
        {currency.error && <Notice tone="error">{apiErrorMessage(currency.error)}</Notice>}
        {currency.isSuccess && (
          <Notice tone="info">
            Prices are now{' '}
            {profile.currency.convert_to_base
              ? `in ${profile.currency.base_currency}`
              : 'in their own currencies'}{' '}
            — click Get Prices to reload them.
          </Notice>
        )}
        <LoadStatus load={load} />

        <div
          className="overflow-auto rounded-md border border-border"
          style={{ maxHeight: '45vh' }}
        >
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 z-10 bg-muted">
              <tr>
                <th className="px-3 py-2 text-left">Selected</th>
                <th className="px-3 py-2 text-left">Ticker</th>
                <th className="px-3 py-2 text-left">Name</th>
                <th className="px-3 py-2 text-left">Currency</th>
                <th className="px-3 py-2 text-left">Asset Class</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            {grouped.map(({ assetClass, rows }) => (
              <tbody key={assetClass} className="divide-y divide-border">
                <tr className="bg-muted/50">
                  <td colSpan={6} className="px-3 py-1.5 font-semibold text-foreground">
                    {assetClass} ({rows.length})
                  </td>
                </tr>
                {rows.map(({ ticker }) => (
                  <tr key={ticker} className="hover:bg-accent/50">
                    <td className="px-3 py-1.5">
                      <input
                        type="checkbox"
                        checked={!unchecked.includes(ticker)}
                        onChange={() => toggleTicker(ticker)}
                        aria-label={`Select ${ticker}`}
                      />
                    </td>
                    <td className="px-3 py-1.5 font-medium">{ticker}</td>
                    <td className="px-3 py-1.5">{cell(detailFrame, ticker, 'Name') ?? '—'}</td>
                    <td className="px-3 py-1.5">{cell(detailFrame, ticker, 'Currency') ?? '—'}</td>
                    <td className="px-3 py-1">
                      <select
                        className="h-7 rounded-md border border-input bg-transparent px-1 text-xs dark:bg-input/30"
                        value={assetClass}
                        onChange={(e) => changeClass(ticker, e.target.value)}
                        aria-label={`Asset class of ${ticker}`}
                      >
                        {classes.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-1 text-right">
                      <button
                        type="button"
                        onClick={() => remove(ticker)}
                        className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
                        aria-label={`Remove ${ticker}`}
                        title="Remove from the universe"
                      >
                        <X className="size-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            ))}
          </table>
        </div>
        <Toolbar>
          <p className="text-xs text-muted-foreground">
            Selected tickers ({selected.length}): {selected.join(', ')}
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto"
            onClick={() => {
              if (window.confirm('Replace the universe with the default tickers?'))
                setTickers(defaultTickers(profile));
            }}
          >
            Reset to default
          </Button>
        </Toolbar>
      </Panel>

      <Panel title="Add Tickers">
        <Toolbar>
          <Field label="Search Yahoo Finance">
            <Input
              className="w-64"
              value={query}
              placeholder="e.g. gold, S&P 500, Vanguard"
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && setSubmitted(query.trim())}
            />
          </Field>
          <RunButton
            onClick={() => setSubmitted(query.trim())}
            loading={search.isFetching}
            variant="secondary"
          >
            Search
          </RunButton>
          <Field label="Ticker">
            <Input
              className="w-36"
              value={newTicker}
              placeholder="e.g. XLK, GOLD.PA"
              onChange={(e) => setNewTicker(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addTicker(newTicker)}
            />
          </Field>
          <SelectField
            label="Asset class"
            value={newClass}
            options={[
              { value: AUTO, label: 'From Yahoo' },
              ...classes.map((c) => ({ value: c, label: c })),
            ]}
            onChange={setNewClass}
            selectClassName="w-36"
          />
          <RunButton onClick={() => addTicker(newTicker)} loading={add.isPending}>
            Add to Universe
          </RunButton>
        </Toolbar>
        {add.error && <Notice tone="error">{apiErrorMessage(add.error)}</Notice>}
        {add.isSuccess && <Notice tone="info">✅ {add.data.message}</Notice>}
        {search.error && <Notice tone="error">{apiErrorMessage(search.error)}</Notice>}
        {results && results.index.length === 0 && (
          <Notice>No Yahoo Finance result for “{submitted}”.</Notice>
        )}
        {results && results.index.length > 0 && (
          <div
            className="overflow-auto rounded-md border border-border"
            style={{ maxHeight: '35vh' }}
          >
            <table className="min-w-full text-xs">
              <thead className="sticky top-0 bg-muted">
                <tr>
                  <th className="px-3 py-2 text-left">Symbol</th>
                  {results.columns.map((c) => (
                    <th key={c} className="px-3 py-2 text-left">
                      {c}
                    </th>
                  ))}
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {results.index.map((symbol, i) => {
                  const suggested = String(cell(results, symbol, 'Asset Class') ?? AUTO);
                  const inUniverse = names.includes(symbol.toUpperCase());
                  return (
                    <tr key={symbol} className="hover:bg-accent/50">
                      <td className="px-3 py-1.5 font-medium">{symbol}</td>
                      {results.data[i].map((value, j) => (
                        <td key={results.columns[j]} className="px-3 py-1.5">
                          {value ?? '—'}
                        </td>
                      ))}
                      <td className="px-3 py-1 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={inUniverse || add.isPending}
                          onClick={() => addTicker(symbol, newClass || suggested)}
                        >
                          {inUniverse ? 'In universe' : 'Add'}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Ticker Details">
        <Toolbar>
          <RunButton
            variant="secondary"
            onClick={() => refreshDetails.mutate()}
            loading={refreshDetails.isPending}
          >
            Refresh Details
          </RunButton>
          <p className="text-xs text-muted-foreground">
            From Yahoo Finance; prices, volumes and sizes in each ticker's currency.
          </p>
        </Toolbar>
        {details.isFetching && !detailFrame && <Loading text="Loading ticker details..." />}
        <ViewStatus
          error={
            details.error ?? (refreshDetails.error ? apiErrorMessage(refreshDetails.error) : null)
          }
        />
        <DataTable frame={detailFrame} indexLabel="Ticker" decimals={2} maxHeight="45vh" />
      </Panel>
    </>
  );
};
