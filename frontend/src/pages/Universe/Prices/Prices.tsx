import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { universeService } from '@/services/universeService';
import { apiErrorMessage } from '@/hooks/useWorkspace';
import { Button } from '@/components/ui/button';
import { DateField, Notice, Panel, RunButton, Toolbar } from '@/components/ui';
import { DataTable } from '@/components/data';
import { pricesToFrame } from '../InvestmentUniverse/universe';

/** Symbols offered by the Prices explorer */
const SYMBOLS = [
  'BTCUSDT',
  'ETHUSDT',
  'BNBUSDT',
  'TRXUSDT',
  'WLFIUSDT',
  'XLMUSDT',
  'TONUSDT',
  'UNIUSDT',
  'TAOUSDT',
  'POLUSDT',
  'GUNUSDT',
  'GNOUSDT',
  'IOTAUSDT',
];

const isoDaysAgo = (days: number) => {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
};

/** Binance closes of a few symbols over a date range */
const Prices = () => {
  const [symbols, setSymbols] = useState<string[]>(SYMBOLS);
  const [start, setStart] = useState(isoDaysAgo(365));
  const [end, setEnd] = useState(isoDaysAgo(0));
  const prices = useMutation({
    mutationFn: () => universeService.fetchPrices(symbols, start, end),
  });
  const frame = useMemo(() => (prices.data ? pricesToFrame(prices.data) : null), [prices.data]);

  const toggle = (symbol: string) =>
    setSymbols((current) =>
      current.includes(symbol) ? current.filter((s) => s !== symbol) : [...current, symbol]
    );

  return (
    <Panel title="Prices">
      <fieldset className="space-y-1">
        <legend className="text-xs font-medium text-muted-foreground">
          Symbols ({symbols.length})
        </legend>
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          {SYMBOLS.map((symbol) => (
            <label key={symbol} className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={symbols.includes(symbol)}
                onChange={() => toggle(symbol)}
              />
              {symbol}
            </label>
          ))}
          <Button variant="outline" size="sm" onClick={() => setSymbols(SYMBOLS)}>
            Select All
          </Button>
          <Button variant="outline" size="sm" onClick={() => setSymbols([])}>
            Clear All
          </Button>
        </div>
      </fieldset>
      <Toolbar>
        <DateField label="Start" value={start} onChange={setStart} />
        <DateField label="End" value={end} onChange={setEnd} />
        {[7, 30, 90, 365].map((days) => (
          <Button
            key={days}
            variant="outline"
            size="sm"
            onClick={() => {
              setStart(isoDaysAgo(days));
              setEnd(isoDaysAgo(0));
            }}
          >
            {days === 365 ? '1 year' : `${days} days`}
          </Button>
        ))}
        <RunButton
          onClick={() => prices.mutate()}
          loading={prices.isPending}
          disabled={symbols.length === 0}
        >
          Get Prices
        </RunButton>
      </Toolbar>
      {prices.error && <Notice tone="error">{apiErrorMessage(prices.error)}</Notice>}
      <DataTable frame={frame} indexLabel="Date" decimals={6} maxHeight="70vh" />
    </Panel>
  );
};

export default Prices;
