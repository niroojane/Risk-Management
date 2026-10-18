import { cn } from '@/utils/cn';
import type { Cell, Frame } from '@/types/workspace';

export type CellFormat = 'number' | 'percent' | 'currency';

export interface DataTableProps {
  frame: Frame | null | undefined;
  title?: string;
  /** Format of every numeric cell, or per column */
  format?: CellFormat | ((column: string, row: string) => CellFormat);
  decimals?: number;
  maxHeight?: string;
  indexLabel?: string;
  className?: string;
}

const formatCell = (value: Cell, format: CellFormat, decimals: number): string => {
  if (value === null || value === undefined) return '—';
  if (typeof value !== 'number') return value;
  if (format === 'percent') return `${(value * 100).toFixed(2)}%`;
  if (format === 'currency') {
    return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: decimals });
};

/** Scrollable table of a frame (index as first column), like the notebook's display_scrollable_df */
export const DataTable = ({
  frame,
  title,
  format = 'number',
  decimals = 4,
  maxHeight = '50vh',
  indexLabel = '',
  className,
}: DataTableProps) => {
  if (!frame || frame.index.length === 0) return null;
  const formatOf = typeof format === 'function' ? format : () => format;

  return (
    <div className={cn('space-y-2', className)}>
      {title && <h3 className="text-sm font-semibold text-foreground">{title}</h3>}
      <div className="overflow-auto rounded-md border border-border" style={{ maxHeight }}>
        <table className="min-w-full text-xs">
          <thead className="sticky top-0 z-10 bg-muted">
            <tr>
              <th className="sticky left-0 z-20 bg-muted px-3 py-2 text-left font-semibold">
                {indexLabel}
              </th>
              {frame.columns.map((column) => (
                <th key={column} className="whitespace-nowrap px-3 py-2 text-right font-semibold">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {frame.index.map((row, i) => (
              <tr
                key={`${row}-${i}`}
                className={cn('hover:bg-accent/50', row === 'Total' && 'font-semibold')}
              >
                <td className="sticky left-0 whitespace-nowrap bg-card px-3 py-1.5 font-medium">
                  {row}
                </td>
                {frame.data[i].map((value, j) => {
                  const negative = typeof value === 'number' && value < 0;
                  return (
                    <td
                      key={frame.columns[j]}
                      className={cn(
                        'whitespace-nowrap px-3 py-1.5 text-right tabular-nums',
                        negative && 'text-red-600 dark:text-red-400'
                      )}
                    >
                      {formatCell(value, formatOf(frame.columns[j], row), decimals)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
