/** Off-diagonal correlation shocks at or above this are reset to 0 (notebook's set_symmetric) */
const SHOCK_LIMIT = 2;

interface StressGridProps {
  symbols: string[];
  matrix: number[][];
  onChange: (matrix: number[][]) => void;
}

/**
 * Editable stress grid: the diagonal holds volatility multipliers, the
 * off-diagonal correlation shocks, kept symmetric.
 */
export const StressGrid = ({ symbols, matrix, onChange }: StressGridProps) => {
  const edit = (i: number, j: number, value: number) => {
    const v = Number.isFinite(value) ? value : 0;
    const next = matrix.map((row) => [...row]);
    if (i === j) {
      next[i][j] = v;
    } else {
      const symmetric = v < SHOCK_LIMIT ? v : 0;
      next[i][j] = symmetric;
      next[j][i] = symmetric;
    }
    onChange(next);
  };

  return (
    <div className="overflow-auto rounded-md border border-border" style={{ maxHeight: '45vh' }}>
      <table className="text-xs">
        <thead className="sticky top-0 z-10 bg-muted">
          <tr>
            <th className="sticky left-0 z-20 bg-muted px-2 py-2" />
            {symbols.map((s) => (
              <th key={s} className="px-2 py-2 font-semibold">
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {symbols.map((row, i) => (
            <tr key={row}>
              <td className="sticky left-0 bg-card px-2 py-1 font-medium">{row}</td>
              {symbols.map((column, j) => (
                <td key={column} className="px-1 py-1">
                  <input
                    type="number"
                    step={0.1}
                    value={matrix[i]?.[j] ?? 0}
                    onChange={(e) => edit(i, j, Number(e.target.value))}
                    className={
                      'w-16 rounded border border-input bg-transparent px-1 py-0.5 text-right tabular-nums focus:outline-none ' +
                      (i === j ? 'font-semibold' : 'text-muted-foreground')
                    }
                    aria-label={`${row} / ${column}`}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
