import { X } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { AllocationRow } from '@/store/workspaceStore';

interface AllocationGridProps {
  rows: AllocationRow[];
  symbols: string[];
  onChange: (rows: AllocationRow[]) => void;
}

/** Editable allocations x assets grid (the notebook's DataGrid); flags rows not summing to 100% */
export const AllocationGrid = ({ rows, symbols, onChange }: AllocationGridProps) => {
  const setWeight = (r: number, symbol: string, value: number) =>
    onChange(
      rows.map((row, i) =>
        i === r
          ? { ...row, weights: { ...row.weights, [symbol]: Number.isFinite(value) ? value : 0 } }
          : row
      )
    );
  const rename = (r: number, name: string) => {
    if (!name.trim() || rows.some((row, i) => i !== r && row.name === name.trim())) return;
    onChange(rows.map((row, i) => (i === r ? { ...row, name: name.trim() } : row)));
  };
  const remove = (r: number) => onChange(rows.filter((_, i) => i !== r));

  return (
    <div className="overflow-auto rounded-md border border-border" style={{ maxHeight: '50vh' }}>
      <table className="min-w-full text-xs">
        <thead className="sticky top-0 z-10 bg-muted">
          <tr>
            <th className="sticky left-0 z-20 bg-muted px-2 py-2 text-left">Allocation</th>
            {symbols.map((s) => (
              <th key={s} className="px-2 py-2 text-right font-semibold">
                {s}
              </th>
            ))}
            <th className="px-2 py-2 text-right font-semibold">Sum</th>
            <th />
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row, r) => {
            const sum = symbols.reduce((total, s) => total + (row.weights[s] ?? 0), 0);
            const valid = Math.abs(sum - 1) < 1e-3;
            return (
              <tr key={row.name}>
                <td className="sticky left-0 bg-card px-2 py-1">
                  <input
                    defaultValue={row.name}
                    onBlur={(e) => rename(r, e.target.value)}
                    className="w-52 rounded border border-transparent bg-transparent px-1 py-0.5 font-medium hover:border-input focus:border-input focus:outline-none"
                    aria-label="Allocation name"
                  />
                </td>
                {symbols.map((s) => (
                  <td key={s} className="px-1 py-1">
                    <input
                      type="number"
                      step={0.01}
                      value={row.weights[s] ?? 0}
                      onChange={(e) => setWeight(r, s, Number(e.target.value))}
                      className="w-20 rounded border border-input bg-transparent px-1 py-0.5 text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-ring/50"
                      aria-label={`${row.name} ${s}`}
                    />
                  </td>
                ))}
                <td
                  className={cn(
                    'px-2 py-1 text-right font-semibold tabular-nums',
                    !valid && 'text-red-600 dark:text-red-400'
                  )}
                  title={valid ? undefined : 'Weights should sum to 100%'}
                >
                  {(sum * 100).toFixed(2)}%
                </td>
                <td className="px-1">
                  <button
                    onClick={() => remove(r)}
                    className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
                    aria-label={`Remove ${row.name}`}
                  >
                    <X className="size-3.5" />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
