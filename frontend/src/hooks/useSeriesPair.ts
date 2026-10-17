import { useWorkspaceStore } from '@/store/workspaceStore';

const pick = (options: string[], wanted: string, fallback: number) =>
  options.includes(wanted) ? wanted : (options[fallback] ?? options[0] ?? '');

/**
 * Fund / benchmark picked among `names`, stored under `key` so the choice survives tab
 * switches and reloads (views sharing a key share the choice, like the notebook's widgets).
 *
 * A choice is kept while it is available. Until the user picks one (or while their pick is
 * unavailable) the preferred defaults apply, so a default that becomes available later -
 * e.g. 'Historical Portfolio' after 'Get P&L' - is selected automatically.
 */
export const useSeriesPair = (
  key: string,
  names: string[],
  defaultFund: string,
  defaultBenchmark: string
) => {
  const selection = useWorkspaceStore((s) => s.selections[key]);
  const setSelection = useWorkspaceStore((s) => s.setSelection);
  const fund = selection?.fund;
  const benchmark = selection?.benchmark;

  return {
    fund: fund && names.includes(fund) ? fund : pick(names, defaultFund, 0),
    benchmark:
      benchmark && names.includes(benchmark) ? benchmark : pick(names, defaultBenchmark, 1),
    setFund: (value: string) => setSelection(key, { fund: value }),
    setBenchmark: (value: string) => setSelection(key, { benchmark: value }),
  };
};
