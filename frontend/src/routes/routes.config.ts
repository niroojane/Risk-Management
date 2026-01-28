import { lazy } from 'react';

export interface RouteConfig {
  path: string;
  component: React.LazyExoticComponent<() => JSX.Element>;
  title: string;
  children?: RouteConfig[];
}

export const routes: RouteConfig[] = [
  {
    path: '/',
    component: lazy(() => import('@/pages/Dashboard/Dashboard')),
    title: 'Dashboard',
  },
  {
    path: 'market-cap',
    component: lazy(() => import('@/pages/Universe/MarketCap/MarketCap')),
    title: 'Market Cap',
  },
  {
    path: 'prices',
    component: lazy(() => import('@/pages/Universe/Prices/Prices')),
    title: 'Prices',
  },
  {
    path: 'strategy',
    component: lazy(() => import('@/pages/Strategy/Strategy')),
    title: 'Strategy',
  },
  {
    path: 'positioning',
    component: lazy(() => import('@/pages/Positioning/Positioning')),
    title: 'Positioning',
  },
  {
    path: 'performance',
    component: lazy(() => import('@/pages/Performance/Performance')),
    title: 'Performance',
  },
  {
    path: 'risk-metrics',
    component: lazy(() => import('@/pages/RiskMetrics/RiskMetrics')),
    title: 'Risk Metrics',
  },
  {
    path: 'market-risk',
    component: lazy(() => import('@/pages/MarketRisk/MarketRisk')),
    title: 'Market Risk',
  },
];
