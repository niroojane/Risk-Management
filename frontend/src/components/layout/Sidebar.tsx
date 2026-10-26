import { useMemo, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/utils/cn';
import { routesFor } from '@/routes';
import { useProfile } from '@/hooks/useProfile';
import { ThemeToggle } from './ThemeToggle';

/** One entry per notebook tab, expanding to its sub-tabs */
export const Sidebar = () => {
  const location = useLocation();
  const profile = useProfile();
  const routes = useMemo(() => routesFor(profile.name), [profile.name]);
  const [openMenus, setOpenMenus] = useState<Record<string, boolean>>({});

  const isOpen = (path: string) => openMenus[path] ?? location.pathname.startsWith(`/${path}`);

  return (
    <aside className="w-64 bg-card border-r border-border h-screen sticky top-0 overflow-y-auto">
      <div className="p-6">
        <h1 className="text-xl font-bold text-foreground">Risk Management</h1>
        <p className="text-xs text-muted-foreground mt-1">Portfolio Analytics</p>
        <div className="mt-3 flex items-center justify-between gap-2">
          <p className="inline-block rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-foreground">
            {profile.label} · {profile.price_source}
          </p>
          <ThemeToggle />
        </div>
      </div>

      <nav className="px-4 pb-4">
        <ul className="space-y-2">
          {routes.map((group) => {
            const Icon = group.icon;
            const open = isOpen(group.path);
            const active = location.pathname.startsWith(`/${group.path}`);
            return (
              <li key={group.path}>
                <button
                  onClick={() => setOpenMenus((prev) => ({ ...prev, [group.path]: !open }))}
                  className={cn(
                    'flex items-center justify-between w-full px-4 py-3 rounded-md text-sm font-medium transition-colors',
                    active
                      ? 'text-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  <span className="flex items-center gap-3">
                    {Icon && <Icon className="h-4 w-4" />}
                    {group.title}
                  </span>
                  {open ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </button>
                {open && (
                  <ul className="mt-1 space-y-1">
                    {group.children?.map((tab) => (
                      <li key={tab.path}>
                        <NavLink
                          to={`/${group.path}/${tab.path}`}
                          className={({ isActive }) =>
                            cn(
                              'flex items-center pl-11 pr-4 py-2 rounded-md text-sm font-medium transition-colors',
                              isActive
                                ? 'bg-primary text-primary-foreground'
                                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                            )
                          }
                        >
                          {tab.title}
                        </NavLink>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
};
