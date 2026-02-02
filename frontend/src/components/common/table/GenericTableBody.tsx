import { flexRender, type Table, type Cell } from '@tanstack/react-table';
import { isNumericColumn } from '@/utils';

interface GenericTableBodyProps<TData> {
  table: Table<TData>;
  columnsLength: number;
  noResultsMessage?: string;
  getCellClassName?: (cell: Cell<TData, unknown>) => string;
  stickyColumnId?: string;
}

const DEFAULT_NO_RESULTS_MESSAGE = 'No data available';

export const GenericTableBody = <TData,>({
  table,
  columnsLength,
  noResultsMessage = DEFAULT_NO_RESULTS_MESSAGE,
  getCellClassName,
  stickyColumnId,
}: GenericTableBodyProps<TData>) => {
  const rows = table.getRowModel().rows;

  if (rows.length === 0) {
    return (
      <tbody className="bg-card divide-y divide-border">
        <tr>
          <td
            colSpan={columnsLength}
            className="px-6 py-8 text-center text-sm text-muted-foreground"
          >
            {noResultsMessage}
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
            const customClassName = getCellClassName?.(cell) || '';
            const isSticky = stickyColumnId && cell.column.id === stickyColumnId;

            return (
              <td
                key={cell.id}
                className={`px-6 py-4 whitespace-nowrap text-sm text-foreground ${
                  isNumeric ? 'text-right' : ''
                } ${customClassName} ${isSticky ? 'sticky left-0 z-10 bg-card shadow-[2px_0_4px_rgba(0,0,0,0.1)]' : ''}`}
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
