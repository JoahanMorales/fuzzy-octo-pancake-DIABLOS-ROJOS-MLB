import { createHashRouter, RouterProvider, type RouteObject } from 'react-router-dom';
import { PAGES, pageElement } from './routes';
import { Layout } from './shell/Layout';
import { NotFound } from './shell/NotFound';

// Hash routes: the static build works on any host without rewrite rules.
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      ...PAGES.map((p) => (p.path === '/' ? { index: true, element: pageElement(p) } : { path: p.path, element: pageElement(p) })),
      { path: '*', element: <NotFound /> },
    ],
  },
];

export default function App() {
  return <RouterProvider router={createHashRouter(routes)} />;
}
