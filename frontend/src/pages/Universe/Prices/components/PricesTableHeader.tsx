import type { Table } from '@tanstack/react-table';
import { GenericTableHeader } from '@/components/common';
import type { PriceRow } from '@/types/prices';

interface PricesTableHeaderProps {
  table: Table<PriceRow>;
}

export const PricesTableHeader = ({ table }: PricesTableHeaderProps) => {
  return <GenericTableHeader table={table} stickyColumnId="date" />;
};
