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
import { ITEMS_PER_PAGE } from '../constants/table';

interface UsePricesTableProps {
  data: PriceRow[];
  symbols: string[];
}

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
