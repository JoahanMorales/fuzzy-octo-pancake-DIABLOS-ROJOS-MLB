import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { routes } from '../App';
import { PAGES, featureLoader, pageElement } from '../routes';

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(<RouterProvider router={router} />);
}

describe('app shell', () => {
  it('declares every page of the product once', () => {
    const paths = PAGES.map((p) => p.path);
    expect(new Set(paths).size).toBe(paths.length);
    for (const p of ['/', '/simulador', '/altitud', '/leaderboard', '/pitcher/:id', '/staff', '/prospecto', '/laboratorio', '/metodologia']) {
      expect(paths).toContain(p);
    }
  });

  it('shows a placeholder for a feature that does not exist yet', () => {
    const page = { path: '/x', feature: 'no-such-feature', title: 'Prueba', nav: false, task: 'HACK-000' };
    expect(featureLoader(page.feature)).toBeUndefined();
    render(<>{pageElement(page)}</>);
    expect(screen.getByRole('heading', { name: 'Prueba' })).toBeInTheDocument();
    expect(screen.getByText(/HACK-000/)).toBeInTheDocument();
  });

  it('loads a feature module from features/<name>/index.tsx when it exists', async () => {
    const mods = { './features/demo/index.tsx': async () => ({ default: () => <h1>Demo cargada</h1> }) };
    const page = { path: '/demo', feature: 'demo', title: 'Demo', nav: false, task: 'HACK-000' };
    render(<>{pageElement(page, mods)}</>);
    expect(await screen.findByRole('heading', { name: 'Demo cargada' })).toBeInTheDocument();
  });

  it('renders the layout with Spanish navigation and a 404 page', async () => {
    renderAt('/');
    expect(screen.getByRole('navigation', { name: 'Secciones' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Simulador' })).toBeInTheDocument();
    renderAt('/no-existe');
    expect(await screen.findByRole('heading', { name: 'Esta página no existe' })).toBeInTheDocument();
  });

  it('routes every declared page without crashing', async () => {
    for (const p of PAGES) {
      const { unmount, container } = renderAt(p.path.replace(':id', 'pitcher_00001'));
      expect(container.querySelector('main')).not.toBeNull();
      unmount();
    }
  });
});
