import { Navigate, Route } from 'react-router-dom';
import { LazyRoute } from '@/components/ui';
import { TabLayout } from '@/components/layout';
import type { RouteConfig } from './routes.config';

/** Pages become routes; groups become a tab bar whose index redirects to the first tab */
export const generateRoutes = (routes: RouteConfig[], level = 0) => {
  return routes.map((route) => {
    const { path, component: Component, title, children } = route;

    if (children && children.length > 0) {
      return (
        <Route
          key={path}
          path={path}
          element={
            <TabLayout
              title={level === 0 ? title : undefined}
              tabs={children.map((child) => ({ to: child.path, label: child.title }))}
              level={level}
            />
          }
        >
          <Route index element={<Navigate to={children[0].path} replace />} />
          {generateRoutes(children, level + 1)}
        </Route>
      );
    }

    if (!Component) return null;
    return (
      <Route
        key={path}
        path={path}
        element={
          <LazyRoute loadingText={`Loading ${title}...`}>
            <Component />
          </LazyRoute>
        }
      />
    );
  });
};
