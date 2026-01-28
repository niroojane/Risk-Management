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
  topN: number;
}

export const useMarketCapTable = ({ data, topN }: UseMarketCapTableProps) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const columns = useMarketCapColumns();
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

  return {
    table,
    globalFilter,
    setGlobalFilter,
  };
};
