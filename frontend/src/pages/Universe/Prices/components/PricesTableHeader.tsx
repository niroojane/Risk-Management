import type { Table } from '@tanstack/react-table';
import { GenericTableHeader } from '@/components/common';
import type { PriceRow } from '@/types/prices';
import { NON_NUMERIC_PRICES_COLUMN_IDS } from '../constants/table';

interface PricesTableHeaderProps {
  table: Table<PriceRow>;
}

export const PricesTableHeader = ({ table }: PricesTableHeaderProps) => {
  const numericColumnIds = table.getAllColumns()
    .map((c) => c.id)
    .filter((id) => !NON_NUMERIC_PRICES_COLUMN_IDS.includes(id));

  return <GenericTableHeader table={table} stickyColumnId="date" numericColumnIds={numericColumnIds} />;
};
