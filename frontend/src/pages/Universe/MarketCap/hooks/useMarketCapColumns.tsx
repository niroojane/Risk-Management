import { useMemo } from 'react';
import { createColumnHelper } from '@tanstack/react-table';
import type { MarketCapData } from '@/types/universe';
import { formatUSD, formatLargeNumber, formatMarketCap } from '@/utils';
import { COLUMN_HEADERS } from '../constants/table';

const columnHelper = createColumnHelper<MarketCapData>();

export const useMarketCapColumns = () => {
  return useMemo(
    () => [
      columnHelper.display({
        id: 'rank',
        header: COLUMN_HEADERS.RANK,
        cell: (info) => {
          const pageIndex = info.table.getState().pagination.pageIndex;
          const pageSize = info.table.getState().pagination.pageSize;
          const rowIndexInPage = info.table.getRowModel().rows.indexOf(info.row);
          return pageIndex * pageSize + rowIndexInPage + 1;
        },
        enableSorting: false,
      }),
      columnHelper.accessor('long_name', {
        header: COLUMN_HEADERS.ASSET,
        cell: (info) => (
          <div className="flex flex-col">
            <span className="text-sm font-medium text-foreground">{info.getValue()}</span>
            <span className="text-xs text-muted-foreground">{info.row.original.base_asset}</span>
          </div>
        ),
        filterFn: 'includesString',
      }),
      columnHelper.accessor('symbol', {
        header: COLUMN_HEADERS.SYMBOL,
        cell: (info) => <span className="font-mono">{info.getValue()}</span>,
        filterFn: 'includesString',
      }),
      columnHelper.accessor('price', {
        header: COLUMN_HEADERS.PRICE,
        cell: (info) => formatUSD(info.getValue()),
      }),
      columnHelper.accessor('supply', {
        header: COLUMN_HEADERS.SUPPLY,
        cell: (info) => formatLargeNumber(info.getValue()),
      }),
      columnHelper.accessor('market_cap', {
        header: COLUMN_HEADERS.MARKET_CAP,
        cell: (info) => formatMarketCap(info.getValue()),
      }),
    ],
    []
  );
};
