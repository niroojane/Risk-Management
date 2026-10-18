import type { ReactNode } from 'react';
import { Input } from '@/components/ui/input';
import { cn } from '@/utils/cn';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { RangeKey } from '@/store/workspaceStore';

interface FieldProps {
  label: string;
  children: ReactNode;
  className?: string;
}

export const Field = ({ label, children, className }: FieldProps) => (
  <label className={cn('flex flex-col gap-1 text-xs font-medium text-muted-foreground', className)}>
    {label}
    {children}
  </label>
);

export interface Option<T extends string = string> {
  value: T;
  label: string;
}

interface SelectFieldProps<T extends string> {
  label: string;
  value: T | null | undefined;
  options: Option<T>[] | T[];
  onChange: (value: T) => void;
  placeholder?: string;
  className?: string;
  /** Width of the select (fixed, so long option names don't push the next fields onto a new row) */
  selectClassName?: string;
}

const selectClass =
  'h-9 rounded-md border border-input bg-transparent px-2 text-sm text-foreground shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30';

export const SelectField = <T extends string>({
  label,
  value,
  options,
  onChange,
  placeholder,
  className,
  selectClassName = 'w-44',
}: SelectFieldProps<T>) => {
  const normalized: Option<T>[] = options.map((o) =>
    typeof o === 'string' ? { value: o, label: o } : o
  );
  return (
    <Field label={label} className={className}>
      <select
        className={cn(selectClass, 'truncate', selectClassName)}
        title={value ?? undefined}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value as T)}
      >
        {(value === null || value === undefined || value === '') && (
          <option value="" disabled>
            {placeholder ?? 'Select…'}
          </option>
        )}
        {normalized.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </Field>
  );
};

interface NumberFieldProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  step?: number;
  min?: number;
  max?: number;
  className?: string;
}

export const NumberField = ({
  label,
  value,
  onChange,
  step = 1,
  min,
  max,
  className,
}: NumberFieldProps) => (
  <Field label={label} className={className}>
    <Input
      type="number"
      className="w-32"
      value={Number.isFinite(value) ? value : ''}
      step={step}
      min={min}
      max={max}
      onChange={(e) => onChange(e.target.value === '' ? NaN : Number(e.target.value))}
    />
  </Field>
);

interface DateFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
}

export const DateField = ({ label, value, onChange }: DateFieldProps) => (
  <Field label={label}>
    <Input
      type="date"
      className="w-40"
      value={value}
      max={new Date().toISOString().slice(0, 10)}
      onChange={(e) => e.target.value && onChange(e.target.value)}
    />
  </Field>
);

/** Start / end date pickers bound to one of the workspace's date ranges */
export const RangeFields = ({ rangeKey }: { rangeKey: RangeKey }) => {
  const range = useWorkspaceStore((s) => s.ranges[rangeKey]);
  const setRange = useWorkspaceStore((s) => s.setRange);
  return (
    <>
      <DateField
        label="Start date"
        value={range.start}
        onChange={(start) => setRange(rangeKey, { ...range, start })}
      />
      <DateField
        label="End date"
        value={range.end}
        onChange={(end) => setRange(rangeKey, { ...range, end })}
      />
    </>
  );
};

/** Row of controls */
export const Toolbar = ({ children, className }: { children: ReactNode; className?: string }) => (
  <div className={cn('flex flex-wrap items-end gap-3', className)}>{children}</div>
);
