import { chartTheme } from '@/components/data/theme';
import { useThemeStore } from '@/store/themeStore';

/** Axis, legend and grid colours of the current mode: charts re-render when it changes */
export const useChartTheme = () => chartTheme(useThemeStore((s) => s.theme) === 'dark');
