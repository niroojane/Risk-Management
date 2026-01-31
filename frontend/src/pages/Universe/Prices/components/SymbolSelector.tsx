import { useState } from 'react';
import { SelectableItem } from '@/components/ui/SelectableItem';
import { Button } from '@/components/ui/button';

const SYMBOLS = [
  'AAVEUSDT',
  'ACEUSDT',
  'ADAUSDT',
  'ALGOUSDT',
  'ANKRUSDT',
  'APEUSDT',
  'APTUSDT',
  'ARBUSDT',
  'ATOMUSDT',
  'AVAXUSDT',
  'AXSUSDT',
  'BALUSDT',
  'BATUSDT',
  'BLZUSDT',
  'BNBUSDT',
];

export const SymbolSelector = () => {
  const [selectedSymbols, setSelectedSymbols] = useState<Set<string>>(new Set(SYMBOLS));

  const handleToggle = (symbol: string, checked: boolean) => {
    const newSelected = new Set(selectedSymbols);
    if (checked) {
      newSelected.add(symbol);
    } else {
      newSelected.delete(symbol);
    }
    setSelectedSymbols(newSelected);
  };

  const handleSelectAll = () => {
    setSelectedSymbols(new Set(SYMBOLS));
  };

  const handleClearAll = () => {
    setSelectedSymbols(new Set());
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

      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 gap-2">
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
