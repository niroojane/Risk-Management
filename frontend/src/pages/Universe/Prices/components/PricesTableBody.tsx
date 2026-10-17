import type { Table, Cell } from '@tanstack/react-table';
import { GenericTableBody } from '@/components/common';
import type { PriceRow } from '@/types/prices';

interface PricesTableBodyProps {
  table: Table<PriceRow>;
  columnsLength: number;
}

const NO_RESULTS_MESSAGE = 'No price data available';

export const PricesTableBody = ({ table, columnsLength }: PricesTableBodyProps) => {
  const getCellClassName = (cell: Cell<PriceRow, unknown>): string => {
    const isDate = cell.column.id === 'date';
    return isDate ? 'font-medium' : '';
  };

  return (
    <GenericTableBody
      table={table}
      columnsLength={columnsLength}
      noResultsMessage={NO_RESULTS_MESSAGE}
      getCellClassName={getCellClassName}
      stickyColumnId="date"
    />
  );
};
