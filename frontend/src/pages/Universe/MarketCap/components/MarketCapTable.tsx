import { useMemo, useState, useEffect } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table';
import { SearchBar, SortIcon, Pagination } from '../../../../components/common';
import type { MarketCapData } from '../../../../types/universe';

interface MarketCapTableProps {
  data: MarketCapData[];
  topN: number;
}

const NUMERIC_COLUMNS = ['price', 'supply', 'market_cap'] as const;
const ITEMS_PER_PAGE = 50;

const isNumericColumn = (columnId: string): boolean => {
  return NUMERIC_COLUMNS.includes(columnId as (typeof NUMERIC_COLUMNS)[number]);
};

const getAriaSortValue = (
  isSorted: false | 'asc' | 'desc'
): 'ascending' | 'descending' | 'none' => {
  if (isSorted === 'asc') return 'ascending';
  if (isSorted === 'desc') return 'descending';
  return 'none';
};

const columnHelper = createColumnHelper<MarketCapData>();

export const MarketCapTable = ({ data, topN }: MarketCapTableProps) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const columns = useMemo(
    () => [
      columnHelper.display({
        id: 'rank',
        header: 'Rank',
        cell: (info) => {
          const pageIndex = info.table.getState().pagination.pageIndex;
          const pageSize = info.table.getState().pagination.pageSize;
          return pageIndex * pageSize + info.row.index + 1;
        },
        enableSorting: false,
      }),
      columnHelper.accessor('long_name', {
        header: 'Asset',
        cell: (info) => (
          <div className="flex flex-col">
            <span className="text-sm font-medium text-foreground">{info.getValue()}</span>
            <span className="text-xs text-muted-foreground">{info.row.original.base_asset}</span>
          </div>
        ),
        filterFn: 'includesString',
      }),
      columnHelper.accessor('symbol', {
        header: 'Symbol',
        cell: (info) => <span className="font-mono">{info.getValue()}</span>,
        filterFn: 'includesString',
      }),
      columnHelper.accessor('price', {
        header: 'Price (USD)',
        cell: (info) =>
          `$${info.getValue().toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}`,
      }),
      columnHelper.accessor('supply', {
        header: 'Supply',
        cell: (info) =>
          info.getValue().toLocaleString(undefined, {
            maximumFractionDigits: 0,
          }),
      }),
      columnHelper.accessor('market_cap', {
        header: 'Market Cap',
        cell: (info) => `$${(info.getValue() / 1e9).toFixed(2)}B`,
      }),
    ],
    []
  );

  const filteredData = useMemo(() => data.slice(0, topN), [data, topN]);

  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    initialState: {
      pagination: {
        pageIndex: 0,
        pageSize: ITEMS_PER_PAGE,
      },
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: (value) => {
      setGlobalFilter(value);
      table.setPageIndex(0);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    globalFilterFn: 'includesString',
  });

  useEffect(() => {
    table.setPageIndex(0);
  }, [topN, table]);

  const totalFilteredItems = table.getFilteredRowModel().rows.length;
  const currentPage = table.getState().pagination.pageIndex + 1;

  return (
    <div className="space-y-4">
      <SearchBar
        value={globalFilter}
        onChange={setGlobalFilter}
        placeholder="Search by assets or symbols"
        showResultCount={true}
        resultCount={totalFilteredItems}
      />

      {/* Table */}
      <div className="bg-card rounded-lg border border-border overflow-hidden">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-muted">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    scope="col"
                    aria-sort={
                      header.column.getCanSort()
                        ? getAriaSortValue(header.column.getIsSorted())
                        : undefined
                    }
                    className={`px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider ${
                      isNumericColumn(header.id) ? 'text-right' : 'text-left'
                    }`}
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={`flex items-center gap-2 ${
                          header.column.getCanSort()
                            ? 'cursor-pointer select-none hover:text-foreground transition-colors'
                            : ''
                        } ${isNumericColumn(header.id) ? 'justify-end' : ''}`}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getCanSort() && (
                          <SortIcon sortDirection={header.column.getIsSorted()} />
                        )}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="bg-card divide-y divide-border">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-6 py-8 text-center text-sm text-muted-foreground"
                >
                  No results found.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-muted/50 transition-colors">
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className={`px-6 py-4 whitespace-nowrap text-sm text-foreground ${
                        isNumericColumn(cell.column.id) ? 'text-right' : ''
                      } ${cell.column.id === 'rank' ? 'text-muted-foreground' : ''} ${
                        cell.column.id === 'market_cap' ? 'font-medium' : ''
                      }`}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        totalItems={totalFilteredItems}
        itemsPerPage={ITEMS_PER_PAGE}
        currentPage={currentPage}
        onPageChange={(page) => table.setPageIndex(page - 1)}
        isShowingItem={false}
      />
    </div>
  );
};
