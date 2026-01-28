import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Globe,
  Target,
  MapPin,
  TrendingUp,
  BarChart3,
  Activity,
  DollarSign,
  TrendingDown,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';

interface SubNavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavItem {
  to?: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  children?: SubNavItem[];
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  {
    label: 'Investment Universe',
    icon: Globe,
    children: [
      { to: '/market-cap', label: 'Market Cap', icon: DollarSign },
      { to: '/prices', label: 'Prices', icon: TrendingDown },
    ],
  },
  { to: '/strategy', label: 'Strategy', icon: Target },
  { to: '/positioning', label: 'Positioning', icon: MapPin },
  { to: '/performance', label: 'Performance', icon: TrendingUp },
  { to: '/risk-metrics', label: 'Risk Metrics', icon: BarChart3 },
  { to: '/market-risk', label: 'Market Risk', icon: Activity },
];

export const Sidebar = () => {
  const [openMenus, setOpenMenus] = useState<{ [key: string]: boolean }>({});
  const location = useLocation();

  const toggleMenu = (label: string) => {
    setOpenMenus((prev) => ({
      ...prev,
      [label]: !prev[label],
    }));
  };

  const isChildActive = (children?: SubNavItem[]) => {
    if (!children) return false;
    return children.some((child) => location.pathname === child.to);
  };

  return (
    <aside className="w-64 bg-card border-r border-border h-screen sticky top-0 overflow-y-auto">
      <div className="p-6">
        <h1 className="text-xl font-bold text-foreground">Risk Management</h1>
        <p className="text-xs text-muted-foreground mt-1">Portfolio Analytics</p>
      </div>

      <nav className="px-4 pb-4">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const hasChildren = !!item.children;
            const isOpen = openMenus[item.label];
            const childIsActive = isChildActive(item.children);

            if (hasChildren) {
              return (
                <li key={item.label}>
                  <button
                    onClick={() => toggleMenu(item.label)}
                    className={cn(
                      'flex items-center justify-between w-full px-4 py-3 rounded-md text-sm font-medium transition-colors',
                      childIsActive
                        ? 'text-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </div>
                    {isOpen ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </button>
                  {isOpen && (
                    <ul className="mt-1 space-y-1">
                      {item.children?.map((child) => {
                        const ChildIcon = child.icon;
                        return (
                          <li key={child.to}>
                            <NavLink
                              to={child.to}
                              className={({ isActive }) =>
                                cn(
                                  'flex items-center gap-3 pl-11 pr-4 py-2 rounded-md text-sm font-medium transition-colors',
                                  isActive
                                    ? 'bg-primary text-primary-foreground'
                                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                                )
                              }
                            >
                              <ChildIcon className="h-4 w-4" />
                              {child.label}
                            </NavLink>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </li>
              );
            }

            return (
              <li key={item.to}>
                <NavLink
                  to={item.to!}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    )
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
};
