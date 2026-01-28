import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Globe,
  Target,
  MapPin,
  TrendingUp,
  BarChart3,
  Activity,
} from 'lucide-react';

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/universe', label: 'Investment Universe', icon: Globe },
  { to: '/strategy', label: 'Strategy', icon: Target },
  { to: '/positioning', label: 'Positioning', icon: MapPin },
  { to: '/performance', label: 'Performance', icon: TrendingUp },
  { to: '/risk-metrics', label: 'Risk Metrics', icon: BarChart3 },
  { to: '/market-risk', label: 'Market Risk', icon: Activity },
];

export const Sidebar = () => {
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
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
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
