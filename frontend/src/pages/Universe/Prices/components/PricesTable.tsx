import { SearchBar, Pagination } from '@/components/common';
import type { PriceRow } from '@/types/prices';
import { usePricesTable } from '../hooks/usePricesTable';
import { PricesTableHeader } from './PricesTableHeader';
import { PricesTableBody } from './PricesTableBody';

interface PricesTableProps {
  data: PriceRow[];
  symbols: string[];
}

const ITEMS_PER_PAGE = 20;
const SEARCH_PLACEHOLDER = 'Search by symbol or date...';

export const PricesTable = ({ data, symbols }: PricesTableProps) => {
  const { table, globalFilter, setGlobalFilter } = usePricesTable({ data, symbols });

  const totalFilteredItems = table.getFilteredRowModel().rows.length;
  const currentPage = table.getState().pagination.pageIndex + 1;
  const columnsLength = table.getAllColumns().length;

  return (
    <div className="space-y-4">
      <SearchBar
        id="prices-search"
        name="pricesSearch"
        value={globalFilter}
        onChange={setGlobalFilter}
        placeholder={SEARCH_PLACEHOLDER}
        showResultCount={true}
        resultCount={totalFilteredItems}
      />

      <div className="bg-card rounded-lg border border-border overflow-x-auto">
        <table className="min-w-full divide-y divide-border">
          <PricesTableHeader table={table} />
          <PricesTableBody table={table} columnsLength={columnsLength} />
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
