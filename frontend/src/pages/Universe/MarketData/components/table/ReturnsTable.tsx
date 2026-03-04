import type { AssetReturnMetrics } from '@/types/prices';
import { formatPercentage } from '@/utils/formatters';

interface ReturnsTableProps {
  data: AssetReturnMetrics[];
}

const formatReturn = (value: number) => formatPercentage(value * 100);

const ROWS = [
  { key: 'total_return' as const, label: 'Total Return' },
  { key: 'ytd_return' as const, label: 'YTD Return' },
  { key: 'annualized_return' as const, label: 'Annualized Return' },
];

export const ReturnsTable = ({ data }: ReturnsTableProps) => {
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
            ROWS.map(({ key, label }) => (
              <tr key={key} className="hover:bg-muted/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">{label}</td>
                {data.map((asset) => (
                  <td key={asset.symbol} className="px-6 py-4 whitespace-nowrap text-sm text-foreground text-right">
                    {formatReturn(asset[key])}
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
