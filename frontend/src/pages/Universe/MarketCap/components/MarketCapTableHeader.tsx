import type { Table } from '@tanstack/react-table';
import { GenericTableHeader } from '@/components/common';
import type { MarketCapData } from '@/types/universe';
import { NUMERIC_COLUMN_IDS } from '../constants/table';

interface MarketCapTableHeaderProps {
  table: Table<MarketCapData>;
}

export const MarketCapTableHeader = ({ table }: MarketCapTableHeaderProps) => {
  return <GenericTableHeader table={table} numericColumnIds={NUMERIC_COLUMN_IDS} />;
};
