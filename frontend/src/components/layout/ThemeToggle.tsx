import { Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useThemeStore } from '@/store/themeStore';

/** Switches between the light and dark modes */
export const ThemeToggle = () => {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const label = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';

  return (
    <Button variant="ghost" size="icon-sm" onClick={toggleTheme} title={label} aria-label={label}>
      {theme === 'dark' ? <Sun /> : <Moon />}
    </Button>
  );
};
