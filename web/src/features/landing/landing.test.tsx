import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import parks from '../../../public/data/mock/parks.json';
import shapes from '../../../public/data/mock/shapes.json';
import staff from '../../../public/data/mock/staff.json';
import validation from '../../../public/data/mock/validation.json';
import { loadLanding } from './load';
import Landing from './index';

function fetchMock(input: RequestInfo | URL): Promise<Response> {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
  if (url.includes('manifest.json')) {
    return Promise.resolve(new Response('', { status: 404 }));
  }
  const name = url.split('/').pop() ?? '';
  const files: Record<string, unknown> = {
    'validation.json': validation,
    'shapes.json': shapes,
    'staff.json': staff,
    'parks.json': parks,
  };
  const body = files[name];
  if (!body) return Promise.resolve(new Response('', { status: 404 }));
  return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
}

function renderLanding(loader: () => ReturnType<typeof loadLanding> | Promise<never>) {
  return render(
    <MemoryRouter>
      <Landing loader={loader} motion="reduce" />
    </MemoryRouter>,
  );
}

describe('landing', () => {
  it('shows the three contract numbers, the simulator link and a still diagram', async () => {
    renderLanding(() => loadLanding(fetchMock));
    expect(await screen.findByTestId('league-delta')).toHaveTextContent('−12.7');
    expect(screen.getByTestId('pitching-skill')).toHaveTextContent('+3.7 %');
    expect(screen.getByTestId('bias-drop')).toHaveTextContent('−81.5 %');
    expect(screen.getByText('ejemplo')).toBeInTheDocument();
    expect(screen.getByTestId('flight-static')).toBeInTheDocument();
    expect(screen.queryByTestId('flight-canvas')).not.toBeInTheDocument();
    const cta = screen.getAllByRole('link', { name: /Probar el simulador/ });
    expect(cta[0]).toHaveAttribute('href', '/simulador');
    expect(screen.getByRole('heading', { name: 'El problema' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'La evidencia' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'El modelo' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Qué gana y qué pierde' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'El staff' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Prospectos' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Valor en victorias' })).toBeInTheDocument();
  });

  it('shows an error when the report cannot be read', async () => {
    renderLanding(() => Promise.reject(new Error('archivo ausente')));
    expect(await screen.findByRole('alert')).toHaveTextContent('archivo ausente');
  });

  it('treats an HTML manifest as missing and still reads the mock', async () => {
    const htmlManifest: typeof fetch = async (input) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      if (url.includes('manifest.json')) {
        return new Response('<!doctype html>', { status: 200, headers: { 'content-type': 'text/html' } });
      }
      return fetchMock(input);
    };
    renderLanding(() => loadLanding(htmlManifest));
    expect(await screen.findByTestId('league-delta')).toHaveTextContent('−12.7');
    expect(screen.getByText('ejemplo')).toBeInTheDocument();
  });

  it('shows a loading state until the report arrives', () => {
    renderLanding(() => new Promise(() => {}));
    expect(screen.getByRole('status')).toHaveTextContent('Cargando el informe');
  });
});
