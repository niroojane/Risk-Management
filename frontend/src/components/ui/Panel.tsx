import type { ReactNode } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/utils/cn';

export const Panel = ({
  title,
  children,
  className,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) => (
  <section className={cn('space-y-4 rounded-lg border border-border bg-card p-4', className)}>
    {title && <h2 className="text-base font-semibold text-foreground">{title}</h2>}
    {children}
  </section>
);

/** Two charts / tables side by side on wide screens, like the notebook's HBox */
export const Grid2 = ({ children }: { children: ReactNode }) => (
  <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">{children}</div>
);

export const RunButton = ({
  onClick,
  loading,
  disabled,
  children,
  variant = 'default',
}: {
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
  children: ReactNode;
  variant?: 'default' | 'outline' | 'secondary' | 'destructive';
}) => (
  <Button onClick={onClick} disabled={disabled || loading} variant={variant}>
    {loading && <Loader2 className="animate-spin" />}
    {children}
  </Button>
);

/** Notebook-style '⚠️' message */
export const Notice = ({
  children,
  tone = 'warning',
}: {
  children: ReactNode;
  tone?: 'warning' | 'error' | 'info';
}) => (
  <div
    className={cn(
      'flex items-start gap-2 rounded-md border px-3 py-2 text-sm',
      tone === 'error' && 'border-destructive/40 bg-destructive/5 text-destructive',
      tone === 'warning' && 'border-amber-500/40 bg-amber-500/5 text-amber-700 dark:text-amber-400',
      tone === 'info' && 'border-border bg-muted text-muted-foreground'
    )}
  >
    <AlertTriangle className="mt-0.5 size-4 shrink-0" />
    <div>{children}</div>
  </div>
);

/** Loading / error / warnings / out-of-date status of a view */
export const ViewStatus = ({
  isFetching,
  error,
  warnings = [],
  stale,
}: {
  isFetching?: boolean;
  error?: string | null;
  warnings?: string[];
  stale?: boolean;
}) => (
  <div className="space-y-2">
    {isFetching && (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Computing…
      </div>
    )}
    {error && <Notice tone="error">{error}</Notice>}
    {warnings.map((w) => (
      <Notice key={w}>{w}</Notice>
    ))}
    {stale && !isFetching && (
      <Notice tone="info">Parameters changed — click the button to refresh the results.</Notice>
    )}
  </div>
);

/** Shown instead of a view whose prerequisites are missing */
export const Prerequisite = ({
  message,
  to,
  action,
}: {
  message: string;
  to: string;
  action: string;
}) => (
  <Notice>
    {message}{' '}
    <Link to={to} className="font-medium underline underline-offset-2">
      {action}
    </Link>
  </Notice>
);
