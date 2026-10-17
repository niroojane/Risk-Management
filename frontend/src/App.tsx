import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/config/queryClient';
import { Layout } from '@/components/layout';
import { ErrorBoundary } from '@/components/common';
import { ProfileProvider } from '@/components/layout/ProfileProvider';
import { useProfile } from '@/hooks/useProfile';
import { routesFor, generateRoutes } from '@/routes';

const AppRoutes = () => {
  const profile = useProfile();
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/universe" replace />} />
        {generateRoutes(routesFor(profile.name))}
        {/* Former top-level explorer pages */}
        <Route path="market-cap" element={<Navigate to="/universe/market-cap" replace />} />
        <Route path="prices" element={<Navigate to="/universe/prices" replace />} />
        <Route path="*" element={<Navigate to="/universe" replace />} />
      </Route>
    </Routes>
  );
};

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ProfileProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </ProfileProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
