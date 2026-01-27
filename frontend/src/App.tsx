import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/layout';

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
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="universe" element={<Universe />} />
          <Route path="strategy" element={<Strategy />} />
          <Route path="positioning" element={<Positioning />} />
          <Route path="performance" element={<Performance />} />
          <Route path="risk-metrics" element={<RiskMetrics />} />
          <Route path="market-risk" element={<MarketRisk />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
