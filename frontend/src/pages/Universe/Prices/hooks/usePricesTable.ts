import { useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
} from '@tanstack/react-table';
import type { PriceRow } from '@/types/prices';
import { usePricesColumns } from './usePricesColumns';

interface UsePricesTableProps {
  data: PriceRow[];
  symbols: string[];
}

const ITEMS_PER_PAGE = 20;

export const usePricesTable = ({ data, symbols }: UsePricesTableProps) => {
  const [globalFilter, setGlobalFilter] = useState('');
  const columns = usePricesColumns({ symbols });

  const table = useReactTable({
    data,
    columns,
    state: {
      globalFilter,
    },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: ITEMS_PER_PAGE,
      }
    },
  });

  return {
    table,
    globalFilter,
    setGlobalFilter,
  };
};
