import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/layout';
import { ErrorBoundary, RouteErrorBoundary } from '@/components/common';

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
    </ErrorBoundary>
  );
}

export default App;
