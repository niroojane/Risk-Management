import { cn } from '@/lib/utils';

interface SelectableItemProps {
  name: string;
  isChecked: boolean;
  onChange: (checked: boolean) => void;
  className?: string;
}

export const SelectableItem = ({ name, isChecked, onChange, className }: SelectableItemProps) => {
  return (
    <label
      className={cn(
        'flex items-center gap-2 px-2 py-1.5 rounded border transition-all cursor-pointer',
        'hover:bg-accent hover:border-primary/50',
        isChecked ? 'border-primary/30 bg-background' : 'border-border/50 bg-muted/30 opacity-50',
        className
      )}
    >
      <input
        type="checkbox"
        checked={isChecked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-3.5 h-3.5 rounded border-border text-primary focus:ring-1 focus:ring-primary focus:ring-offset-0 cursor-pointer"
      />
      <span
        className={cn(
          'font-mono text-xs font-medium transition-colors',
          isChecked ? 'text-foreground' : 'text-muted-foreground'
        )}
      >
        {name}
      </span>
    </label>
  );
};
