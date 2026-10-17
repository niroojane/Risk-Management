import { NavLink, Outlet } from 'react-router-dom';
import { cn } from '@/lib/utils';

export interface TabLink {
  to: string;
  label: string;
}

/** Notebook-style tab bar over the active sub-tab */
export const TabLayout = ({
  title,
  tabs,
  level,
}: {
  title?: string;
  tabs: TabLink[];
  level: number;
}) => (
  <div className={cn(level === 0 ? 'space-y-6' : 'space-y-4')}>
    {title && <h1 className="text-3xl font-bold text-foreground">{title}</h1>}
    <nav
      className={cn('flex flex-wrap gap-1 border-b border-border', level > 0 && 'border-dashed')}
    >
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) =>
            cn(
              '-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
    <Outlet />
  </div>
);
