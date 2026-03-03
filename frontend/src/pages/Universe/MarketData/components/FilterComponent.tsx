import { AlertCircle } from 'lucide-react';
import { SymbolSelector } from './SymbolSelector';
import { DateRangeSelector } from './DateRangeSelector';
import { Button } from '@/components/ui/button';
import type { DateRange } from '../types/filters';

interface FilterComponentProps {
  symbols?: string[];
  onSymbolsChange?: (symbols: string[]) => void;
  dateRange?: DateRange;
  onDateRangeChange?: (dateRange: DateRange | undefined) => void;
  onGenerateTable?: () => void;
  validationError?: string | null;
}

export const FilterComponent = ({
  symbols,
  onSymbolsChange,
  dateRange,
  onDateRangeChange,
  onGenerateTable,
  validationError,
}: FilterComponentProps) => {
  return (
    <div className="space-y-6 rounded-lg border border-border bg-card p-6 shadow-sm">
      <div>
        <h2 className="text-lg font-semibold mb-3">Symbols</h2>
        <SymbolSelector value={symbols} onChange={onSymbolsChange} />
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3">Date Range</h2>
        <DateRangeSelector value={dateRange} onChange={onDateRangeChange} />
      </div>

      {onGenerateTable && (
        <div className="pt-2 border-t border-border space-y-3">
          {validationError && (
            <p className="flex items-center gap-1.5 text-sm text-destructive">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {validationError}
            </p>
          )}
          <Button
            onClick={onGenerateTable}
            className="w-full sm:w-auto cursor-pointer"
            size="lg"
          >
            Generate Table
          </Button>
        </div>
      )}
    </div>
  );
};
