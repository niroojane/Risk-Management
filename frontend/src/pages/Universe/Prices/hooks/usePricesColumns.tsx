import { useMemo } from 'react';
import { createColumnHelper } from '@tanstack/react-table';
import type { PriceRow } from '@/types/prices';
import { formatUSD, formatDate } from '@/utils/formatters';

const columnHelper = createColumnHelper<PriceRow>();

interface UsePricesColumnsProps {
  symbols: string[];
}

export const usePricesColumns = ({ symbols }: UsePricesColumnsProps) => {
  return useMemo(
    () => [
      columnHelper.accessor('date', {
        header: 'Date',
        cell: (info) => formatDate(info.getValue()),
      }),
      ...symbols.map((symbol) =>
        columnHelper.accessor(symbol, {
          header: symbol,
          cell: (info) => {
            const value = info.getValue();
            return typeof value === 'number' ? formatUSD(value) : '-';
          },
        })
      ),
    ],
    [symbols]
  );
};
