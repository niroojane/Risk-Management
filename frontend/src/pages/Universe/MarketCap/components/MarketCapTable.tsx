import { SearchBar, Pagination } from '@/components/common';
import type { MarketCapData } from '@/types/universe';
import { useMarketCapTable } from '../hooks/useMarketCapTable';
import { MarketCapTableHeader } from './MarketCapTableHeader';
import { MarketCapTableBody } from './MarketCapTableBody';
import { ITEMS_PER_PAGE, SEARCH_PLACEHOLDER } from '../constants/table';

interface MarketCapTableProps {
  data: MarketCapData[];
  displayCount: number;
}

export const MarketCapTable = ({ data, displayCount }: MarketCapTableProps) => {
  const { table, globalFilter, setGlobalFilter } = useMarketCapTable({ data, displayCount });

  const totalFilteredItems = table.getFilteredRowModel().rows.length;
  const currentPage = table.getState().pagination.pageIndex + 1;
  const columnsLength = table.getAllColumns().length;

  return (
    <div className="space-y-4">
      <SearchBar
        id="market-cap-search"
        name="marketCapSearch"
        value={globalFilter}
        onChange={setGlobalFilter}
        placeholder={SEARCH_PLACEHOLDER}
        showResultCount={true}
        resultCount={totalFilteredItems}
      />

      <div className="bg-card rounded-lg border border-border overflow-hidden">
        <table className="min-w-full divide-y divide-border">
          <MarketCapTableHeader table={table} />
          <MarketCapTableBody table={table} columnsLength={columnsLength} />
        </table>
      </div>

      <Pagination
        totalItems={totalFilteredItems}
        itemsPerPage={ITEMS_PER_PAGE}
        currentPage={currentPage}
        onPageChange={(page) => table.setPageIndex(page - 1)}
        showItemRange={false}
        showNavigationArrows={false}
      />
    </div>
  );
};
