import { useState } from 'react';
import { FilterComponent } from './components/FilterComponent';
import { FilterDialog } from './components/FilterDialog';
import { PricesTable } from './components/table/PricesTable';
import { PricesChart } from './components/charts/PricesChart';
import { CumulativeChart } from './components/charts/CumulativeChart';
import { transformPricesData } from './utils/transformPricesData';
import { Loading, ErrorMessage, ViewChartToggle, useViewToggle, ReturnsTable, RiskTable } from '@/components/common';
import { useUniverseStore } from '@/stores/universeStore';
import { useFiltersStore } from '@/stores/filtersStore';
import { useMarketData } from '@/hooks/useMarketData';

const Prices = () => {
  const { symbols, setSymbols } = useUniverseStore();
  const { dateRange, setDateRange, showTable, setShowTable } = useFiltersStore();
  const [validationError, setValidationError] = useState<string | null>(null);
  const { view: pricesView, setView: setPricesView } = useViewToggle('chart');

  const { data: pricesData, isLoading, error, refetch } = useMarketData();

  const handleGenerateTable = (): boolean => {
    setValidationError(null);

    if (symbols.length === 0) {
      setValidationError('Please select at least one symbol');
      return false;
    }

    if (!dateRange?.from || !dateRange?.to) {
      setValidationError('Please select a date range');
      return false;
    }

    setShowTable(true);
    refetch();
    return true;
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
            validationError={validationError}
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
          validationError={validationError}
        />
      ) : (
        <div>
          {isLoading && <Loading />}
          {error && <ErrorMessage message="Failed to fetch prices data" />}
          {!isLoading && !error && pricesData && (
            <div className="space-y-8">
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-foreground">Prices</h2>
                  <ViewChartToggle view={pricesView} onChange={setPricesView} />
                </div>
                {pricesView === 'table' ? (
                  <PricesTable data={tableData} symbols={symbols} />
                ) : (
                  <PricesChart data={tableData} symbols={symbols} />
                )}
              </section>

              {pricesData.data.returns && (
                <section className="space-y-3">
                  <h2 className="text-lg font-semibold text-foreground">Returns</h2>
                  <ReturnsTable data={pricesData.data.returns.assets} />
                </section>
              )}

              <section className="space-y-3">
                <h2 className="text-lg font-semibold text-foreground">Cumulative Performance</h2>
                <CumulativeChart data={tableData} symbols={symbols} />
              </section>

              {pricesData.data.risk && (
                <section className="space-y-3">
                  <h2 className="text-lg font-semibold text-foreground">Risk Metrics</h2>
                  <RiskTable data={pricesData.data.risk} />
                </section>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Prices;
