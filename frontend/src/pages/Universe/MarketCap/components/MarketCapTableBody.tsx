import type { Table, Cell } from '@tanstack/react-table';
import { GenericTableBody } from '@/components/common';
import type { MarketCapData } from '@/types/universe';
import { NO_RESULTS_MESSAGE } from '../constants/table';

interface MarketCapTableBodyProps {
  table: Table<MarketCapData>;
  columnsLength: number;
}

export const MarketCapTableBody = ({ table, columnsLength }: MarketCapTableBodyProps) => {
  const getCellClassName = (cell: Cell<MarketCapData, unknown>): string => {
    const columnId = cell.column.id;
    const isRank = columnId === 'rank';
    const isMarketCap = columnId === 'market_cap';

    return `${isRank ? 'text-muted-foreground' : ''} ${isMarketCap ? 'font-medium' : ''}`;
  };

  return (
    <GenericTableBody
      table={table}
      columnsLength={columnsLength}
      noResultsMessage={NO_RESULTS_MESSAGE}
      getCellClassName={getCellClassName}
    />
  );
};
