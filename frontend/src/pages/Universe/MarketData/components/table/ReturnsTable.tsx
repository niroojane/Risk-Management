import type { AssetReturnMetrics } from '@/types/prices';
import { GenericTableHeader, GenericTableBody } from '@/components/common/table';
import { useReturnsTable } from '../../hooks/useReturnsTable';
import { NUMERIC_RETURNS_COLUMN_IDS } from '../../constants/table';

interface ReturnsTableProps {
  data: AssetReturnMetrics[];
}

export const ReturnsTable = ({ data }: ReturnsTableProps) => {
  const { table } = useReturnsTable({ data });
  const columnsLength = table.getAllColumns().length;

  return (
    <div className="bg-card rounded-lg border border-border overflow-x-auto">
      <table className="min-w-full divide-y divide-border">
        <GenericTableHeader table={table} numericColumnIds={NUMERIC_RETURNS_COLUMN_IDS} />
        <GenericTableBody table={table} columnsLength={columnsLength} numericColumnIds={NUMERIC_RETURNS_COLUMN_IDS} />
      </table>
    </div>
  );
};
