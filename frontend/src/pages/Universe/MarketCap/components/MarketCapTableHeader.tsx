import { flexRender, type Table } from '@tanstack/react-table';
import { SortIcon } from '../../../../components/common';
import type { MarketCapData } from '../../../../types/universe';
import { isNumericColumn, getAriaSortValue } from '../../../../utils/table';

interface MarketCapTableHeaderProps {
  table: Table<MarketCapData>;
}

export const MarketCapTableHeader = ({ table }: MarketCapTableHeaderProps) => {
  return (
    <thead className="bg-muted">
      {table.getHeaderGroups().map((headerGroup) => (
        <tr key={headerGroup.id}>
          {headerGroup.headers.map((header) => (
            <th
              key={header.id}
              scope="col"
              aria-sort={
                header.column.getCanSort()
                  ? getAriaSortValue(header.column.getIsSorted())
                  : undefined
              }
              className={`px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider ${
                isNumericColumn(header.id) ? 'text-right' : 'text-left'
              }`}
            >
              {header.isPlaceholder ? null : (
                <div
                  className={`flex items-center gap-2 ${
                    header.column.getCanSort()
                      ? 'cursor-pointer select-none hover:text-foreground transition-colors'
                      : ''
                  } ${isNumericColumn(header.id) ? 'justify-end' : ''}`}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {header.column.getCanSort() && (
                    <SortIcon sortDirection={header.column.getIsSorted()} />
                  )}
                </div>
              )}
            </th>
          ))}
        </tr>
      ))}
    </thead>
  );
};
