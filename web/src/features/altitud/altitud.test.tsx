import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import Page, { loadAltitude, mexicoPath, parkRadius, projection } from './index';
import parks from '../../../public/data/mock/parks.json';
import shapes from '../../../public/data/mock/shapes.json';

const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
function serve(real = false) {
  return vi.fn(async (url: string | URL | Request) => {
    const path = String(url);
    if (path.endsWith('manifest.json')) return response({}, real ? 200 : 404);
    const data = structuredClone(path.endsWith('parks.json') ? parks : shapes);
    data.demo_data = !real;
    return response(data);
  });
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('projects Mexico and keeps landmark positions in the viewport', () => {
  expect(mexicoPath).toMatch(/^M/);
  expect(mexicoPath).not.toMatch(/NaN|Infinity/);
  for (const point of [[-99.13, 19.43], [-117, 32.5], [-86.85, 21.16]]) {
    const [x, y] = projection([point[0], point[1]])!;
    expect(x).toBeGreaterThanOrEqual(0); expect(x).toBeLessThanOrEqual(600);
    expect(y).toBeGreaterThanOrEqual(0); expect(y).toBeLessThanOrEqual(360);
  }
  expect(parkRadius(0.8) ** 2 / parkRadius(1) ** 2).toBeCloseTo(0.8);
});

it('loads mocks when manifest is absent and never mixes sources', async () => {
  const fetcher = serve(); vi.stubGlobal('fetch', fetcher);
  const data = await loadAltitude();
  expect(data.parks.demo_data).toBe(true);
  expect(fetcher.mock.calls.slice(1).every(([url]) => String(url).includes('/mock/'))).toBe(true);
});

it('recognizes Vite HTML fallback as an absent real manifest', async () => {
  const normal = serve();
  vi.stubGlobal('fetch', vi.fn((url: string) => url.endsWith('manifest.json')
    ? Promise.resolve(new Response('<html></html>', { headers: { 'content-type': 'text/html' } })) : normal(url)));
  expect((await loadAltitude()).parks.demo_data).toBe(true);
});

it('loads real data only after a real manifest and does not silently mock malformed real data', async () => {
  const normal = serve(true); vi.stubGlobal('fetch', normal);
  expect((await loadAltitude()).parks.demo_data).toBe(false);
  expect(normal.mock.calls.slice(1).every(([url]) => String(url).includes('/real/'))).toBe(true);
  vi.stubGlobal('fetch', vi.fn(async (url: string) => url.endsWith('shapes.json') ? response({}) : normal(url)));
  await expect(loadAltitude()).rejects.toThrow();
});

it('does not silently mock an unexpected manifest format', async () => {
  const fetcher = vi.fn(async () => new Response('unexpected', { headers: { 'content-type': 'text/plain' } }));
  vi.stubGlobal('fetch', fetcher);
  await expect(loadAltitude()).rejects.toThrow('formato inesperado');
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it.each(['density', 'duplicate', 'interval', 'provenance'])('rejects invalid %s aggregates', async kind => {
  const p = structuredClone(parks), s = structuredClone(shapes);
  if (kind === 'density') p.parks[0].rho = 0;
  if (kind === 'duplicate') p.parks[1].id = p.parks[0].id;
  if (kind === 'interval') s.shapes[0].delta_lo = s.shapes[0].delta_hi + 1;
  if (kind === 'provenance') s.model_version = 'other';
  vi.stubGlobal('fetch', vi.fn(async (url: string) => response(url.endsWith('parks.json') ? p : s, url.endsWith('manifest.json') ? 404 : 200)));
  await expect(loadAltitude()).rejects.toThrow();
});

it('renders all parks, explicit uncertainty, sources and contract CIs; toggles only scenario scores', async () => {
  vi.stubGlobal('fetch', serve());
  const { container } = render(<Page />);
  expect(screen.getByRole('status')).toHaveTextContent('Cargando');
  await screen.findByText(/Datos de ejemplo/);
  expect(screen.getByLabelText('Parques sin ubicación verificada').querySelectorAll('button')).toHaveLength(20);
  expect(screen.getByText(/círculos no representan posiciones geográficas/)).toBeVisible();
  expect(screen.getByText(/deploy\/bundle\/tables\/by_park.csv/)).toBeVisible();
  expect(screen.getByRole('link', { name: /Natural Earth/ })).toHaveAttribute('href', expect.stringContaining('naturalearthdata.com'));
  const before = [...container.querySelectorAll('.alt-ci')].map(el => el.outerHTML);
  fireEvent.click(screen.getByRole('button', { name: 'Nivel del mar' }));
  expect(screen.getByRole('button', { name: 'Nivel del mar' })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByRole('img', { name: /ΔStuff/ }).querySelectorAll('g[tabindex]')).toHaveLength(shapes.shapes.length);
  expect([...container.querySelectorAll('.alt-ci')].map(el => el.outerHTML)).toEqual(before);
  const s = shapes.shapes[0];
  expect(screen.getByLabelText(new RegExp(`${s.shape}: delta.*Stuff\\+ nivel del mar ${s.stuff_sea_level.toFixed(2)}`))).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: `Parque ${parks.parks[1].id}, densidad ${parks.parks[1].rho.toFixed(3)}` }));
  expect(screen.getByText(`ρ̂ ${parks.parks[1].rho.toFixed(3)}`)).toBeVisible();
});

it('shows a retryable error on HTTP failures', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => response({}, 500)));
  render(<Page />);
  expect(await screen.findByRole('alert')).toHaveTextContent('No se pudieron cargar');
  vi.stubGlobal('fetch', serve());
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
  await screen.findByText(/Datos de ejemplo/);
});
