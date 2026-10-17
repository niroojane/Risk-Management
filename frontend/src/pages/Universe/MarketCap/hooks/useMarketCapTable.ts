import { useState, useMemo, useEffect } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  type SortingState,
  type ColumnFiltersState,
} from '@tanstack/react-table';
import type { MarketCapData } from '@/types/universe';
import { useMarketCapColumns } from './useMarketCapColumns';
import { ITEMS_PER_PAGE } from '../constants/table';

interface UseMarketCapTableProps {
  data: MarketCapData[];
  displayCount: number;
}

export const useMarketCapTable = ({ data, displayCount }: UseMarketCapTableProps) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const columns = useMarketCapColumns();
  const filteredData = useMemo(() => data.slice(0, displayCount), [data, displayCount]);

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
  }, [displayCount, table]);

  return {
    table,
    globalFilter,
    setGlobalFilter,
  };
};
