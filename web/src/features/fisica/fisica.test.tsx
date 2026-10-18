import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import mock from '../../../public/data/mock/physics.json';
import { resetSourceCache } from '../staff/data';
import { compare, RHO_HARP, SHAPES, type PhysicsDoc } from './data';
import FisicaPage, { Explainer } from './index';

const doc = mock as PhysicsDoc;
const fam = (f: string) => doc.families.find((x) => x.pitch_family === f)!;
const shape = (f: string) => SHAPES.find((s) => s.pitch_family === f)!;

afterEach(() => {
  vi.unstubAllGlobals();
  resetSourceCache();
});

describe('física: el mismo lanzamiento en dos aires', () => {
  it('at sea level the three flights coincide; in Harp Helú air the measured elasticity loses more than textbook', () => {
    const sea = compare(shape('Four-Seam'), fam('Four-Seam'), 1);
    expect(Math.abs(sea.moveLost)).toBeLessThan(1e-6);
    expect(sea.measured.plateZ).toBeCloseTo(sea.sea.plateZ, 6);

    const hh = compare(shape('Four-Seam'), fam('Four-Seam'), RHO_HARP);
    expect(hh.drag).toBeCloseTo(RHO_HARP, 6);
    expect(hh.magnusTextbook).toBeCloseTo(RHO_HARP, 6);
    expect(hh.magnusMeasured).toBeCloseTo(RHO_HARP ** fam('Four-Seam').elasticity, 6);
    expect(hh.magnusMeasured).toBeLessThan(hh.magnusTextbook);
    expect(hh.moveLost).toBeGreaterThan(hh.moveLostTextbook);
    expect(hh.moveLostTextbook).toBeGreaterThan(0);
    // less ride: the fastball crosses lower, and with less drag it arrives faster
    expect(hh.drop).toBeGreaterThan(0);
    expect(hh.measured.plateMph).toBeGreaterThan(hh.sea.plateMph);
  });

  it('every family loses movement along its own break, curveballs and sliders included', () => {
    for (const s of SHAPES) {
      const c = compare(s, fam(s.pitch_family), RHO_HARP);
      expect(c.moveLost, s.pitch_family).toBeGreaterThan(0);
    }
  });

  it('shows the measured elasticity next to textbook physics and updates with the density', () => {
    render(<Explainer doc={doc} />);
    expect(screen.getByText('1 = física de libro')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /elasticidad/ })).toHaveLength(7);
    const fourSeam = fam('Four-Seam').elasticity.toFixed(2);
    expect(screen.getByText(`ρ elevada a ${fourSeam}`)).toBeInTheDocument();
    expect(screen.getByText(/pierde .* in de movimiento/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Nivel del mar' }));
    expect(screen.getByText(/las tres versiones coinciden/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('radio', { name: 'Curva' }));
    expect(screen.getByText(/la curva típica/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Curva: elasticidad/ })).toHaveAttribute('aria-pressed', 'true');
  });

  it('draws a side view and a catcher view with a legend and text alternatives', () => {
    render(<Explainer doc={doc} />);
    const views = screen.getAllByRole('img');
    expect(views.map((v) => v.getAttribute('aria-label'))).toEqual([
      expect.stringMatching(/^Vista lateral/), expect.stringMatching(/^Vista del receptor/),
    ]);
    const legend = screen.getByRole('list', { name: 'Leyenda' });
    expect(within(legend).getByText('Nivel del mar')).toBeInTheDocument();
    expect(within(legend).getByText('Aire elegido, física de libro')).toBeInTheDocument();
  });

  it('reduced motion shows the final frame (no draw animation)', () => {
    const media = (matches: boolean) => vi.fn(() => ({ matches, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
    vi.stubGlobal('matchMedia', media(false));
    const { container, unmount } = render(<Explainer doc={doc} />);
    expect(container.querySelector('.fis-draw')).not.toBeNull();
    unmount();
    vi.stubGlobal('matchMedia', media(true));
    const reduced = render(<Explainer doc={doc} />);
    expect(reduced.container.querySelector('.fis-draw')).toBeNull();
    expect(reduced.container.querySelector('.fis-pop')).toBeNull();
    expect(reduced.container.querySelector('.fis-hh')?.getAttribute('d')).toMatch(/^M/);
  });

  it('loads physics.json from the contract and labels the mock as an example', async () => {
    const files: Record<string, unknown> = { 'data/mock/physics.json': mock };
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      const key = Object.keys(files).find((k) => url.endsWith(k));
      return { ok: !!key, status: key ? 200 : 404, json: async () => (key ? files[key] : {}) };
    }));
    render(<FisicaPage />);
    await waitFor(() => expect(screen.getByText('Ejemplo')).toBeInTheDocument());
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Por qué la recta pierde subida en la CDMX');
  });
});
