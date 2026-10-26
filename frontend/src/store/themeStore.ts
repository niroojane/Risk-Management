import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark';

/** localStorage key, also read by the inline script of index.html before the first paint */
export const THEME_STORAGE_KEY = 'risk-management-theme';

const systemTheme = (): Theme =>
  window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

/** Tailwind's `dark:` variant and the `.dark` tokens of index.css key off this class */
const applyTheme = (theme: Theme) =>
  document.documentElement.classList.toggle('dark', theme === 'dark');

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
}

/** Light / dark mode, kept in this browser: the OS preference until the user picks one */
export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: systemTheme(),
      toggleTheme: () => {
        const theme = get().theme === 'dark' ? 'light' : 'dark';
        // the page's colours (CSS) and the charts' (state) switch together
        applyTheme(theme);
        set({ theme });
      },
    }),
    {
      name: THEME_STORAGE_KEY,
      onRehydrateStorage: () => (state) => applyTheme(state?.theme ?? systemTheme()),
    }
  )
);
