import { useMemo } from 'react';
import { createColumnHelper } from '@tanstack/react-table';
import type { AssetReturnMetrics } from '@/types/prices';
import { formatPercentage } from '@/utils/formatters';

const columnHelper = createColumnHelper<AssetReturnMetrics>();

const formatReturn = (value: number) => formatPercentage(value * 100);

export const useReturnsColumns = () => {
  return useMemo(
    () => [
      columnHelper.accessor('symbol', {
        header: 'Symbol',
        cell: (info) => info.getValue(),
      }),
      columnHelper.accessor('total_return', {
        header: 'Total Return',
        cell: (info) => formatReturn(info.getValue()),
      }),
      columnHelper.accessor('ytd_return', {
        header: 'YTD Return',
        cell: (info) => formatReturn(info.getValue()),
      }),
      columnHelper.accessor('annualized_return', {
        header: 'Annualized Return',
        cell: (info) => formatReturn(info.getValue()),
      }),
    ],
    []
  );
};
