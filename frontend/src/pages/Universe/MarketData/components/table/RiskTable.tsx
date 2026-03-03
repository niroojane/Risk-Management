import type { AssetRiskMetrics } from '@/types/prices';
import { GenericTableHeader, GenericTableBody } from '@/components/common/table';
import { useRiskTable } from '../../hooks/useRiskTable';
import { NUMERIC_RISK_COLUMN_IDS } from '../../constants/table';

interface RiskTableProps {
  data: AssetRiskMetrics[];
}

export const RiskTable = ({ data }: RiskTableProps) => {
  const { table } = useRiskTable({ data });
  const columnsLength = table.getAllColumns().length;

  return (
    <div className="bg-card rounded-lg border border-border overflow-x-auto">
      <table className="min-w-full divide-y divide-border">
        <GenericTableHeader table={table} numericColumnIds={NUMERIC_RISK_COLUMN_IDS} />
        <GenericTableBody table={table} columnsLength={columnsLength} numericColumnIds={NUMERIC_RISK_COLUMN_IDS} />
      </table>
    </div>
  );
};
