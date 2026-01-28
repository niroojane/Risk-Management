import { flexRender, type Table } from '@tanstack/react-table';
import type { MarketCapData } from '../../../../types/universe';
import { isNumericColumn } from '../../../../utils/table';
import { NO_RESULTS_MESSAGE } from '../constants/table';

interface MarketCapTableBodyProps {
  table: Table<MarketCapData>;
  columnsLength: number;
}

export const MarketCapTableBody = ({ table, columnsLength }: MarketCapTableBodyProps) => {
  const rows = table.getRowModel().rows;

  if (rows.length === 0) {
    return (
      <tbody className="bg-card divide-y divide-border">
        <tr>
          <td
            colSpan={columnsLength}
            className="px-6 py-8 text-center text-sm text-muted-foreground"
          >
            {NO_RESULTS_MESSAGE}
          </td>
        </tr>
      </tbody>
    );
  }

  return (
    <tbody className="bg-card divide-y divide-border">
      {rows.map((row) => (
        <tr key={row.id} className="hover:bg-muted/50 transition-colors">
          {row.getVisibleCells().map((cell) => {
            const isNumeric = isNumericColumn(cell.column.id);
            const isRank = cell.column.id === 'rank';
            const isMarketCap = cell.column.id === 'market_cap';

            return (
              <td
                key={cell.id}
                className={`px-6 py-4 whitespace-nowrap text-sm text-foreground ${
                  isNumeric ? 'text-right' : ''
                } ${isRank ? 'text-muted-foreground' : ''} ${isMarketCap ? 'font-medium' : ''}`}
              >
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </td>
            );
          })}
        </tr>
      ))}
    </tbody>
  );
};
