import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { FilterComponent } from './components/FilterComponent';
import { FilterDialog } from './components/FilterDialog';
import { PricesTable } from './components/PricesTable';
import { getDefaultDateRange } from './components/DateRangeSelector';
import { getDefaultSymbols } from './components/SymbolSelector';
import { transformPricesData } from './utils/transformPricesData';
import { universeService } from '@/services/universeService';
import { Loading, ErrorMessage } from '@/components/common';
import type { DateRange } from './types/filters';

const Prices = () => {
  const [showTable, setShowTable] = useState(false);
  const [symbols, setSymbols] = useState<string[]>(getDefaultSymbols());
  const [dateRange, setDateRange] = useState<DateRange | undefined>(getDefaultDateRange());

  const {
    data: pricesData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['prices', symbols, dateRange],
    queryFn: async () => {
      if (!dateRange?.from || !dateRange?.to) {
        throw new Error('Date range is required');
      }

      const startDate = format(dateRange.from, 'yyyy-MM-dd');
      const endDate = format(dateRange.to, 'yyyy-MM-dd');

      return universeService.fetchMarketData(symbols, startDate, endDate);
    },
    enabled: false,
  });

  const handleGenerateTable = () => {
    if (symbols.length === 0) {
      alert('Please select at least one symbol');
      return;
    }

    if (!dateRange?.from || !dateRange?.to) {
      alert('Please select a date range');
      return;
    }

    setShowTable(true);
    refetch();
  };

  const tableData = pricesData ? transformPricesData(pricesData) : [];

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Prices Data</h1>
          <p className="text-muted-foreground mt-2">
            Select crypto symbols and date range to view price history
          </p>
        </div>

        {showTable && (
          <FilterDialog
            symbols={symbols}
            onSymbolsChange={setSymbols}
            dateRange={dateRange}
            onDateRangeChange={setDateRange}
            onGenerateTable={handleGenerateTable}
          />
        )}
      </div>

      {!showTable ? (
        <FilterComponent
          symbols={symbols}
          onSymbolsChange={setSymbols}
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
          onGenerateTable={handleGenerateTable}
        />
      ) : (
        <div>
          {isLoading && <Loading />}
          {error && <ErrorMessage message="Failed to fetch prices data" />}
          {!isLoading && !error && pricesData && (
            <PricesTable data={tableData} symbols={symbols} />
          )}
        </div>
      )}
    </div>
  );
};

export default Prices;
