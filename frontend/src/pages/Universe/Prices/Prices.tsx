import { SymbolSelector } from './components/SymbolSelector';
import { DateRangeSelector } from './components/DateRangeSelector';

const Prices = () => {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Prices Data</h1>
        <p className="text-muted-foreground mt-2">
          Select crypto symbols and date range to view price history
        </p>
      </div>

      <div className="space-y-6 rounded-lg border border-border bg-card p-6 shadow-sm">
        <div>
          <h2 className="text-lg font-semibold mb-3">Symbols</h2>
          <SymbolSelector />
        </div>

        <div>
          <h2 className="text-lg font-semibold mb-3">Date Range</h2>
          <DateRangeSelector />
        </div>
      </div>
    </div>
  );
};

export default Prices;
