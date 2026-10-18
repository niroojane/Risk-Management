import { lazy } from 'react';
import type { LazyExoticComponent, ComponentType } from 'react';
import { Activity, Globe, ShieldAlert, Target, Wallet } from 'lucide-react';
import type { MarketName } from '@/types/profile';

/**
 * A page, or a group of tabs (children) shown under a tab bar.
 * The groups and their order mirror the Crypto App notebook's tabs and sub-tabs.
 */
export interface RouteConfig {
  path: string;
  title: string;
  component?: LazyExoticComponent<ComponentType>;
  children?: RouteConfig[];
  icon?: ComponentType<{ className?: string }>;
  /** Markets the page exists for (default: all) */
  markets?: MarketName[];
}

/** The routes of a market (the Binance explorer pages only exist for crypto) */
export const routesFor = (market: MarketName, list: RouteConfig[] = routes): RouteConfig[] =>
  list
    .filter((route) => !route.markets || route.markets.includes(market))
    .map((route) =>
      route.children ? { ...route, children: routesFor(market, route.children) } : route
    );

const Positioning = lazy(() => import('@/pages/shared/Positioning'));

export const routes: RouteConfig[] = [
  {
    path: 'universe',
    title: 'Investment Universe',
    icon: Globe,
    children: [
      {
        path: 'overview',
        title: 'Investment Universe',
        component: lazy(() => import('@/pages/Universe/InvestmentUniverse/InvestmentUniverse')),
      },
      {
        path: 'market-cap',
        title: 'Market Cap',
        component: lazy(() => import('@/pages/Universe/MarketCap/MarketCap')),
        markets: ['crypto'],
      },
      {
        path: 'prices',
        title: 'Prices',
        component: lazy(() => import('@/pages/Universe/Prices/Prices')),
        markets: ['crypto'],
      },
    ],
  },
  {
    path: 'strategy',
    title: 'Strategy',
    icon: Target,
    children: [
      {
        path: 'builder',
        title: 'Strategy',
        component: lazy(() => import('@/pages/Strategy/Strategy')),
      },
      { path: 'positioning', title: 'Positioning', component: Positioning },
      {
        path: 'returns',
        title: 'Strategy Return',
        component: lazy(() => import('@/pages/Strategy/StrategyReturn')),
      },
    ],
  },
  {
    path: 'portfolio',
    title: 'Current Portfolio',
    icon: Wallet,
    children: [
      {
        path: 'pnl',
        title: 'P&L',
        children: [
          {
            path: 'analysis',
            title: 'P&L Analysis',
            component: lazy(() => import('@/pages/CurrentPortfolio/PnLAnalysis')),
          },
          {
            path: 'returns',
            title: 'Return Analysis',
            component: lazy(() => import('@/pages/CurrentPortfolio/ReturnAnalysis')),
          },
          {
            path: 'beta',
            title: 'Beta Analysis',
            component: lazy(() => import('@/pages/CurrentPortfolio/BetaAnalysis')),
          },
        ],
      },
      { path: 'positioning', title: 'Positioning', component: Positioning },
      {
        path: 'calendar',
        title: 'Calendar Return',
        component: lazy(() => import('@/pages/CurrentPortfolio/CalendarReturn')),
      },
    ],
  },
  {
    path: 'risk',
    title: 'Risk Analysis',
    icon: ShieldAlert,
    children: [
      {
        path: 'volatility',
        title: 'Volatility Analysis',
        children: [
          {
            path: 'contribution',
            title: 'Risk Contribution',
            component: lazy(() => import('@/pages/RiskAnalysis/RiskContribution')),
          },
          {
            path: 'trajectory',
            title: 'Risk Trajectory',
            component: lazy(() => import('@/pages/RiskAnalysis/RiskTrajectory')),
          },
          {
            path: 'tracking-error',
            title: 'Tracking Error',
            component: lazy(() => import('@/pages/RiskAnalysis/TrackingError')),
          },
        ],
      },
      {
        path: 'var',
        title: 'Value at Risk',
        children: [
          {
            path: 'simulation',
            title: 'Value at Risk',
            component: lazy(() => import('@/pages/RiskAnalysis/ValueAtRisk')),
          },
          {
            path: 'history',
            title: 'Value at Risk History',
            component: lazy(() => import('@/pages/RiskAnalysis/VaRHistory')),
          },
        ],
      },
    ],
  },
  {
    path: 'market-risk',
    title: 'Market Risk',
    icon: Activity,
    children: [
      {
        path: 'pca',
        title: 'Market Risk',
        component: lazy(() => import('@/pages/MarketRisk/MarketRisk')),
      },
      {
        path: 'correlation',
        title: 'Correlation',
        component: lazy(() => import('@/pages/MarketRisk/Correlation')),
      },
      {
        path: 'drivers',
        title: 'Market Drivers',
        component: lazy(() => import('@/pages/MarketRisk/MarketDrivers')),
      },
    ],
  },
];
