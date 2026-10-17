import { Suspense } from 'react';
import { RouteErrorBoundary } from './RouteErrorBoundary';
import { Loading } from './Loading';

export interface LazyRouteProps {
  children: React.ReactNode;
  loadingText?: string;
}

export const LazyRoute = ({ children, loadingText }: LazyRouteProps) => {
  return (
    <RouteErrorBoundary>
      <Suspense fallback={<Loading text={loadingText} fullScreen />}>{children}</Suspense>
    </RouteErrorBoundary>
  );
};
