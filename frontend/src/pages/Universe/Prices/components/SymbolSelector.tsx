import { SelectableItem } from '@/components/ui/SelectableItem';
import { Button } from '@/components/ui/button';

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
  'IOTAUSDT'
];

export const getDefaultSymbols = (): string[] => SYMBOLS;

interface SymbolSelectorProps {
  value?: string[];
  onChange?: (symbols: string[]) => void;
}

export const SymbolSelector = ({ value = SYMBOLS, onChange }: SymbolSelectorProps) => {
  const selectedSymbols = new Set(value);

  const handleToggle = (symbol: string, checked: boolean) => {
    const newSelected = new Set(selectedSymbols);
    if (checked) {
      newSelected.add(symbol);
    } else {
      newSelected.delete(symbol);
    }
    onChange?.(Array.from(newSelected));
  };

  const handleSelectAll = () => {
    onChange?.(SYMBOLS);
  };

  const handleClearAll = () => {
    onChange?.([]);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          <span className="font-semibold text-foreground">{selectedSymbols.size}</span>
          {' / '}
          {SYMBOLS.length} selected
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleSelectAll}>
            Select All
          </Button>
          <Button variant="outline" size="sm" onClick={handleClearAll}>
            Clear All
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2">
        {SYMBOLS.map((symbol) => (
          <SelectableItem
            key={symbol}
            name={symbol}
            isChecked={selectedSymbols.has(symbol)}
            onChange={(checked) => handleToggle(symbol, checked)}
          />
        ))}
      </div>
    </div>
  );
};
