import { Route } from 'react-router-dom';
import { LazyRoute } from '@/components/common';
import type { RouteConfig } from './routes.config';

export const generateRoutes = (routes: RouteConfig[]) => {
  return routes.map((route) => {
    const { path, component: Component, title, children } = route;

    if (children && children.length > 0) {
      return (
        <Route key={path} path={path}>
          {generateRoutes(children)}
        </Route>
      );
    }

    const isIndexRoute = path === '/';
    const element = (
      <LazyRoute loadingText={`Loading ${title}...`}>
        <Component />
      </LazyRoute>
    );

    if (isIndexRoute) {
      return <Route key="index" index element={element} />;
    }

    return <Route key={path} path={path} element={element} />;
  });
};
