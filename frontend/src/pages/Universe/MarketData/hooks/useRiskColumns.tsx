import { useMemo } from 'react';
import { createColumnHelper } from '@tanstack/react-table';
import type { AssetRiskMetrics } from '@/types/prices';
import { formatPercentage, formatDate } from '@/utils/formatters';

const columnHelper = createColumnHelper<AssetRiskMetrics>();

const formatVol = (value: number) => formatPercentage(value * 100);

export const useRiskColumns = () => {
  return useMemo(
    () => [
      columnHelper.accessor('symbol', {
        header: 'Symbol',
        cell: (info) => info.getValue(),
      }),
      columnHelper.accessor('annualized_vol_daily', {
        header: 'Vol (Daily)',
        cell: (info) => formatVol(info.getValue()),
      }),
      columnHelper.accessor('annualized_vol_3y_weekly', {
        header: 'Vol (3Y Weekly)',
        cell: (info) => formatVol(info.getValue()),
      }),
      columnHelper.accessor('annualized_vol_5y_monthly', {
        header: 'Vol (5Y Monthly)',
        cell: (info) => formatVol(info.getValue()),
      }),
      columnHelper.accessor('annualized_vol_since_inception_monthly', {
        header: 'Vol (Since Inception)',
        cell: (info) => formatVol(info.getValue()),
      }),
      columnHelper.accessor('inception_year', {
        header: 'Inception Year',
        cell: (info) => info.getValue(),
      }),
      columnHelper.accessor('cvar_parametric_95', {
        header: 'CVaR 95%',
        cell: (info) => formatVol(info.getValue()),
      }),
      columnHelper.accessor('max_drawdown', {
        header: 'Max Drawdown',
        cell: (info) => formatVol(info.getValue()),
      }),
      columnHelper.accessor('date_of_max_drawdown', {
        header: 'Date Max Drawdown',
        cell: (info) => formatDate(info.getValue()),
      }),
    ],
    []
  );
};
