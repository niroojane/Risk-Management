import type { AssetRiskMetrics } from '@/types/prices';
import { formatPercentage, formatDate } from '@/utils/formatters';

interface RiskTableProps {
  data: AssetRiskMetrics[];
}

const formatVol = (value: number) => formatPercentage(value * 100);

const ROWS: { key: keyof Omit<AssetRiskMetrics, 'symbol'>; label: string; format: (v: never) => string }[] = [
  { key: 'annualized_vol_daily', label: 'Vol (Daily)', format: (v: number) => formatVol(v) },
  { key: 'annualized_vol_3y_weekly', label: 'Vol (3Y Weekly)', format: (v: number) => formatVol(v) },
  { key: 'annualized_vol_5y_monthly', label: 'Vol (5Y Monthly)', format: (v: number) => formatVol(v) },
  { key: 'annualized_vol_since_inception_monthly', label: 'Vol (Since Inception)', format: (v: number) => formatVol(v) },
  { key: 'inception_year', label: 'Inception Year', format: (v: number) => String(v) },
  { key: 'cvar_parametric_95', label: 'CVaR 95%', format: (v: number) => formatVol(v) },
  { key: 'max_drawdown', label: 'Max Drawdown', format: (v: number) => formatVol(v) },
  { key: 'date_of_max_drawdown', label: 'Date Max Drawdown', format: (v: string) => formatDate(v) },
];

export const RiskTable = ({ data }: RiskTableProps) => {
  return (
    <div className="bg-card rounded-lg border border-border overflow-x-auto">
      <table className="min-w-full divide-y divide-border">
        <thead className="bg-muted">
          <tr>
            <th className="px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider text-left">
              Metric
            </th>
            {data.map((asset) => (
              <th key={asset.symbol} className="px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider text-right">
                {asset.symbol}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-card divide-y divide-border">
          {data.length === 0 ? (
            <tr>
              <td className="px-6 py-8 text-center text-sm text-muted-foreground" colSpan={1}>
                No data available
              </td>
            </tr>
          ) : (
            ROWS.map(({ key, label, format }) => (
              <tr key={key} className="hover:bg-muted/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">{label}</td>
                {data.map((asset) => (
                  <td key={asset.symbol} className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                    {format(asset[key] as never)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};
