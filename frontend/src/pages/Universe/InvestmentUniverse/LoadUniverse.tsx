import { useWorkspaceStore } from '@/store/workspaceStore';
import { apiErrorMessage } from '@/hooks/useWorkspace';
import { Notice } from '@/components/ui';
import type { useLoadUniverse } from './useLoadUniverse';

/** Result of 'Get Prices' */
export const LoadStatus = ({ load }: { load: ReturnType<typeof useLoadUniverse> }) => {
  const universe = useWorkspaceStore((s) => s.universe);
  return (
    <>
      {load.error && <Notice tone="error">{apiErrorMessage(load.error)}</Notice>}
      {universe && (
        <Notice tone="info">
          ✅ Loaded prices for {universe.symbols.length} assets from {universe.start} to{' '}
          {universe.end}
          {universe.holdings.length > 0 && ` (including ${universe.holdings.length} held assets)`}
          {universe.excluded.length > 0 && ` — not enough history: ${universe.excluded.join(', ')}`}
        </Notice>
      )}
    </>
  );
};
