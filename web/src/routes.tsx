import { lazy, Suspense, type ComponentType, type ReactNode } from 'react';
import { Placeholder } from './shell/Placeholder';

/** Every page of the product. A feature task only creates `src/features/<feature>/index.tsx` (default export);
 *  until it exists the route shows the placeholder, so no feature task ever edits this file. */
export interface PageDef {
  path: string;
  feature: string;
  title: string;
  nav: boolean;
  task: string;
}

export const PAGES: PageDef[] = [
  { path: '/', feature: 'landing', title: 'Inicio', nav: true, task: 'HACK-043' },
  { path: '/simulador', feature: 'simulador', title: 'Simulador', nav: true, task: 'HACK-044/045' },
  { path: '/altitud', feature: 'altitud', title: 'Altitud', nav: true, task: 'HACK-046' },
  { path: '/leaderboard', feature: 'leaderboard', title: 'Leaderboard', nav: true, task: 'HACK-047' },
  { path: '/pitcher/:id', feature: 'pitcher', title: 'Pitcher', nav: false, task: 'HACK-047' },
  { path: '/staff', feature: 'staff', title: 'Staff Diablos', nav: true, task: 'HACK-048' },
  { path: '/prospecto', feature: 'prospecto', title: 'Prospecto', nav: true, task: 'HACK-048' },
  { path: '/laboratorio', feature: 'laboratorio', title: 'Laboratorio', nav: true, task: 'HACK-048' },
  { path: '/metodologia', feature: 'metodologia', title: 'Metodología', nav: true, task: 'HACK-049' },
];

type Loader = () => Promise<{ default: ComponentType }>;
const modules = import.meta.glob('./features/*/index.tsx') as Record<string, Loader>;

export function featureLoader(feature: string, mods: Record<string, Loader> = modules): Loader | undefined {
  return mods[`./features/${feature}/index.tsx`];
}

const cache = new Map<string, ComponentType>();

export function pageElement(page: PageDef, mods: Record<string, Loader> = modules): ReactNode {
  const loader = featureLoader(page.feature, mods);
  if (!loader) return <Placeholder title={page.title} task={page.task} />;
  let Lazy = cache.get(page.feature);
  if (!Lazy) {
    Lazy = lazy(loader);
    cache.set(page.feature, Lazy);
  }
  return (
    <Suspense fallback={<div className="page-loading" role="status">Cargando…</div>}>
      <Lazy />
    </Suspense>
  );
}
