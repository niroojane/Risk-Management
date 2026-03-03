import { useReactTable, getCoreRowModel, getSortedRowModel } from '@tanstack/react-table';
import type { AssetReturnMetrics } from '@/types/prices';
import { useReturnsColumns } from './useReturnsColumns';

interface UseReturnsTableProps {
  data: AssetReturnMetrics[];
}

export const useReturnsTable = ({ data }: UseReturnsTableProps) => {
  const columns = useReturnsColumns();

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return { table };
};
