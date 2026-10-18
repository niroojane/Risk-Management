import type { ReactNode } from 'react';
import { Prerequisite } from '@/components/ui';
import { useWorkspaceStore } from '@/store/workspaceStore';

/** Renders children once 'Get Prices' has loaded the universe */
export const RequireUniverse = ({ children }: { children: ReactNode }) => {
  const universe = useWorkspaceStore((s) => s.universe);
  if (!universe) {
    return (
      <Prerequisite
        message="⚠️ Load prices first."
        to="/universe/overview"
        action="Investment Universe →"
      />
    );
  }
  return <>{children}</>;
};

/** Renders children once the allocation grid has rows ('Optimize Portfolio') */
export const RequireAllocations = ({ children }: { children: ReactNode }) => {
  const allocations = useWorkspaceStore((s) => s.allocations);
  return (
    <RequireUniverse>
      {allocations.length === 0 ? (
        <Prerequisite
          message="⚠️ Please compute optimization results first."
          to="/strategy/builder"
          action="Strategy →"
        />
      ) : (
        children
      )}
    </RequireUniverse>
  );
};
