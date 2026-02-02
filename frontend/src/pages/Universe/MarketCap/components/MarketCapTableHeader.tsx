import type { Table } from '@tanstack/react-table';
import { GenericTableHeader } from '@/components/common';
import type { MarketCapData } from '@/types/universe';

interface MarketCapTableHeaderProps {
  table: Table<MarketCapData>;
}

export const MarketCapTableHeader = ({ table }: MarketCapTableHeaderProps) => {
  return <GenericTableHeader table={table} />;
};
