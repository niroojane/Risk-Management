import { useReactTable, getCoreRowModel, getSortedRowModel } from '@tanstack/react-table';
import type { AssetRiskMetrics } from '@/types/prices';
import { useRiskColumns } from './useRiskColumns';

interface UseRiskTableProps {
  data: AssetRiskMetrics[];
}

export const useRiskTable = ({ data }: UseRiskTableProps) => {
  const columns = useRiskColumns();

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return { table };
};
