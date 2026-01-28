import { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table';
import { ChevronUp, ChevronDown, ChevronsUpDown, Search } from 'lucide-react';
import { Input } from '../../../components/ui/input';
import type { MarketCapData } from '../../../types/universe';

interface MarketCapTableProps {
  data: MarketCapData[];
  topN: number;
}

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
        cell: (info) => info.row.index + 1,
        enableSorting: false,
      }),
      columnHelper.accessor('long_name', {
        header: 'Asset',
        cell: (info) => (
          <div className="flex flex-col">
            <span className="text-sm font-medium text-foreground">
              {info.getValue()}
            </span>
            <span className="text-xs text-muted-foreground">
              {info.row.original.base_asset}
            </span>
          </div>
        ),
        filterFn: 'includesString',
      }),
      columnHelper.accessor('symbol', {
        header: 'Symbol',
        cell: (info) => (
          <span className="font-mono">{info.getValue()}</span>
        ),
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
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn: 'includesString',
  });

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by assets or symbols"
            value={globalFilter ?? ''}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="pl-9"
          />
        </div>
        {globalFilter && (
          <span className="text-sm text-muted-foreground">
            {table.getFilteredRowModel().rows.length} result(s)
          </span>
        )}
      </div>

      {/* Table */}
      <div className="bg-card rounded-lg border border-border overflow-hidden">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-muted">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className={`px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider ${
                      header.id === 'price' ||
                      header.id === 'supply' ||
                      header.id === 'market_cap'
                        ? 'text-right'
                        : 'text-left'
                    }`}
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={`flex items-center gap-2 ${
                          header.column.getCanSort()
                            ? 'cursor-pointer select-none hover:text-foreground transition-colors'
                            : ''
                        } ${
                          header.id === 'price' ||
                          header.id === 'supply' ||
                          header.id === 'market_cap'
                            ? 'justify-end'
                            : ''
                        }`}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {header.column.getCanSort() && (
                          <span className="text-muted-foreground">
                            {{
                              asc: <ChevronUp className="h-4 w-4" />,
                              desc: <ChevronDown className="h-4 w-4" />,
                            }[header.column.getIsSorted() as string] ?? (
                              <ChevronsUpDown className="h-4 w-4 opacity-50" />
                            )}
                          </span>
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
                <tr
                  key={row.id}
                  className="hover:bg-muted/50 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className={`px-6 py-4 whitespace-nowrap text-sm text-foreground ${
                        cell.column.id === 'price' ||
                        cell.column.id === 'supply' ||
                        cell.column.id === 'market_cap'
                          ? 'text-right'
                          : ''
                      } ${
                        cell.column.id === 'rank' ? 'text-muted-foreground' : ''
                      } ${
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
    </div>
  );
};
