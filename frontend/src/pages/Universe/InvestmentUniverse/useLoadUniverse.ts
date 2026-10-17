import { useMutation } from '@tanstack/react-query';
import { universeService } from '@/services/universeService';
import { workspaceService } from '@/services/workspaceService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import type { LoadedUniverse } from '@/store/workspaceStore';
import { useProfile } from '@/hooks/useProfile';
import { validSymbols } from './universe';

const today = () => new Date().toISOString().slice(0, 10);

/**
 * 'Get Prices': prices of the selected tickers (plus the held assets when the profile
 * says so), keeping the assets with enough history. Cash / stablecoins never join.
 */
export const useLoadUniverse = () => {
  const profile = useProfile();
  const startDate = useWorkspaceStore((s) => s.startDate);
  const setUniverse = useWorkspaceStore((s) => s.setUniverse);
  return useMutation({
    mutationFn: async (selected: string[]): Promise<LoadedUniverse> => {
      let holdings: string[] = [];
      if (profile.include_holdings_in_universe) {
        try {
          holdings = (await workspaceService.holdings()).data.tickers;
        } catch {
          // account not reachable: the universe is just the selected tickers
        }
      }
      const skip = new Set([...profile.cash_assets, ...profile.excluded_symbols]);
      const tickers = Array.from(new Set([...selected, ...holdings]))
        .filter((t) => !skip.has(t))
        .sort();
      if (tickers.length === 0)
        throw new Error('No tickers available. Please select tickers first.');
      const end = today();
      const response = await universeService.fetchPrices(tickers, startDate, end);
      const { valid, excluded } = validSymbols(response, tickers);
      if (valid.length < 2) throw new Error('Not enough assets with price history on this period.');
      return {
        symbols: valid,
        selected: selected.filter((t) => valid.includes(t)),
        start: startDate,
        end,
        holdings,
        excluded,
      };
    },
    onSuccess: setUniverse,
  });
};
