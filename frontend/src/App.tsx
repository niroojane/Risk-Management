import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from '@/components/layout';
import { ErrorBoundary, RouteErrorBoundary } from '@/components/common';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Pages
import Dashboard from '@/pages/Dashboard/Dashboard';
import Universe from '@/pages/Universe/Universe';
import Strategy from '@/pages/Strategy/Strategy';
import Positioning from '@/pages/Positioning/Positioning';
import Performance from '@/pages/Performance/Performance';
import RiskMetrics from '@/pages/RiskMetrics/RiskMetrics';
import MarketRisk from '@/pages/MarketRisk/MarketRisk';

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route
              index
              element={
                <RouteErrorBoundary>
                  <Dashboard />
                </RouteErrorBoundary>
              }
            />
            <Route
              path="universe"
              element={
                <RouteErrorBoundary>
                  <Universe />
                </RouteErrorBoundary>
              }
            />
            <Route
              path="strategy"
              element={
                <RouteErrorBoundary>
                  <Strategy />
                </RouteErrorBoundary>
              }
            />
            <Route
              path="positioning"
              element={
                <RouteErrorBoundary>
                  <Positioning />
                </RouteErrorBoundary>
              }
            />
            <Route
              path="performance"
              element={
                <RouteErrorBoundary>
                  <Performance />
                </RouteErrorBoundary>
              }
            />
            <Route
              path="risk-metrics"
              element={
                <RouteErrorBoundary>
                  <RiskMetrics />
                </RouteErrorBoundary>
              }
            />
            <Route
              path="market-risk"
              element={
                <RouteErrorBoundary>
                  <MarketRisk />
                </RouteErrorBoundary>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
