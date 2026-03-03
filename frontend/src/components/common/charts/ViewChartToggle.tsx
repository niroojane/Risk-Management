import { TableIcon, LineChartIcon } from 'lucide-react';

export type ViewMode = 'table' | 'chart';

export interface ViewChartToggleProps {
  view: ViewMode;
  onChange: (view: ViewMode) => void;
}

export const ViewChartToggle = ({ view, onChange }: ViewChartToggleProps) => {
  return (
    <div className="flex items-center gap-1 rounded-md border border-border bg-muted p-1">
      <button
        onClick={() => onChange('table')}
        aria-label="Table view"
        aria-pressed={view === 'table'}
        className={`flex items-center justify-center rounded p-1.5 transition-colors ${
          view === 'table'
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        <TableIcon size={15} />
      </button>
      <button
        onClick={() => onChange('chart')}
        aria-label="Chart view"
        aria-pressed={view === 'chart'}
        className={`flex items-center justify-center rounded p-1.5 transition-colors ${
          view === 'chart'
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        <LineChartIcon size={15} />
      </button>
    </div>
  );
};
