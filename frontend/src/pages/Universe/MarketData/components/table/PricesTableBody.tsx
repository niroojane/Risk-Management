import type { Table, Cell } from '@tanstack/react-table';
import { GenericTableBody } from '@/components/common';
import type { PriceRow } from '@/types/prices';
import { NON_NUMERIC_PRICES_COLUMN_IDS } from '../../constants/table';

interface PricesTableBodyProps {
  table: Table<PriceRow>;
  columnsLength: number;
}

const NO_RESULTS_MESSAGE = 'No price data available';

export const PricesTableBody = ({ table, columnsLength }: PricesTableBodyProps) => {
  const numericColumnIds = table.getAllColumns()
    .map((c) => c.id)
    .filter((id) => !NON_NUMERIC_PRICES_COLUMN_IDS.includes(id));

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
      numericColumnIds={numericColumnIds}
    />
  );
};
