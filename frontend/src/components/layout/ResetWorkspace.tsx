import { RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useWorkspaceStore } from '@/store/workspaceStore';

const LABEL = 'Reset workspace';

/** Clears the workspace saved in this browser (universe, constraints, allocations, backtest...) */
export const ResetWorkspace = () => {
  const reset = () => {
    if (
      !window.confirm(
        'Reset the workspace? The universe, dates, constraints, overlays, allocation grid and ' +
          'results saved in this browser are cleared (the theme, the Excel files and the HMM ' +
          'scenarios are kept).'
      )
    )
      return;
    useWorkspaceStore.persist.clearStorage();
    // reload so no page keeps the old state in memory
    window.location.reload();
  };

  return (
    <Button variant="ghost" size="icon-sm" onClick={reset} title={LABEL} aria-label={LABEL}>
      <RotateCcw />
    </Button>
  );
};
