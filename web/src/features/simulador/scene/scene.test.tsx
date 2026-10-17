import { fireEvent, render, screen } from '@testing-library/react';
import { afterAll, beforeAll } from 'vitest';
import { SimulatorScene } from './SimulatorScene';
import {
  LOCAL_BOOK,
  VIEWS,
  ZONE,
  batterFrame,
  cameraMoves,
  cameraSmoothTime,
  insideBand,
  loadParkBook,
  parseParkBook,
  pickEnds,
  placeholderPath,
  readReduced,
  showDevStats,
  skylineProfile,
} from './sceneModel';

beforeAll(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
});

afterAll(() => {
  vi.restoreAllMocks();
});

describe('parques y trayectoria', () => {
  it('elige el aire delgado y el nivel del mar por rho, no por una altitud escrita', () => {
    const book = parseParkBook({
      demo_data: true,
      parks: [
        { id: '9', rho: 0.999, bucket: 'No Altitude', air_effect: 0.922, altitude: 'No Altitude' },
        { id: '11', rho: 0.812, bucket: 'Extreme Altitude', air_effect: -10.742, altitude: 'Extreme Altitude' },
        { id: '5', rho: 0.822, bucket: 'Extreme Altitude', air_effect: -10.296, altitude: '2240 m' },
      ],
    });
    expect(book).not.toBeNull();
    const ends = pickEnds(book!);
    expect(ends.harp.id).toBe('11');
    expect(ends.harp.rho).toBeCloseTo(0.812);
    expect(ends.sea.id).toBe('9');
  });

  it('usa el mock local si parks.json no está', async () => {
    expect(LOCAL_BOOK.demoData).toBe(true);
    expect(JSON.stringify(LOCAL_BOOK)).not.toMatch(/2240/);
    const missing = await loadParkBook(async () => new Response('no', { status: 404 }));
    expect(missing.origin).toBe('local');
    const file = await loadParkBook(async () => new Response(JSON.stringify({
      demo_data: false,
      parks: [
        { id: 'a', rho: 1.01, bucket: 'No Altitude', air_effect: 0, altitude: 'No Altitude' },
        { id: 'b', rho: 0.8, bucket: 'Extreme Altitude', air_effect: 0, altitude: 'Extreme Altitude' },
      ],
    }), { status: 200 }));
    expect(file.origin).toBe('file');
    expect(file.book.demoData).toBe(false);
    expect(pickEnds(file.book).harp.id).toBe('b');
  });

  it('separa la trayectoria de ejemplo cuando la densidad baja', () => {
    const sea = placeholderPath(1, 1);
    const thin = placeholderPath(0.82, 1);
    expect(sea).toHaveLength(32);
    expect(thin[16][1]).toBeGreaterThan(sea[16][1]);
    expect(sea[sea.length - 1][2]).toBeCloseTo(ZONE.z);
  });
});

describe('cámaras, zona y bateador', () => {
  it('tiene las cuatro cámaras y corta la transición si hay menos movimiento', () => {
    expect(Object.keys(VIEWS)).toEqual(['catcher', 'pitcher', 'lateral', 'broadcast']);
    expect(cameraMoves(true)).toBe(false);
    expect(cameraMoves(false)).toBe(true);
    expect(cameraSmoothTime(true)).toBe(0);
    expect(showDevStats(false)).toBe(false);
    expect(showDevStats(true)).toBe(true);
  });

  it('manda la zona adentro hacia el bateador y camina de lado', () => {
    expect(insideBand('R').x).toBeLessThan(0);
    expect(insideBand('L').x).toBeGreaterThan(0);
    expect(batterFrame('R', 'R', 1).x).toBeLessThan(0);
    expect(batterFrame('L', 'L', 1).x).toBeGreaterThan(0);
    expect(batterFrame('R', 'L', 0).x).toBeCloseTo(batterFrame('R', 'R', 1).x);
    expect(batterFrame('R', 'L', 1).mirror).toBeLessThan(0);
    expect(skylineProfile('harp').ridges).toBe(true);
    expect(skylineProfile('sea').ridges).toBe(false);
    expect(Math.max(...skylineProfile('harp').stand)).toBeGreaterThan(Math.max(...skylineProfile('sea').stand));
  });
});

describe('vista sin WebGL2', () => {
  it('muestra el mensaje, la vista 2D y actualiza lado, parque y cámara', () => {
    render(<SimulatorScene />);
    expect(screen.getByText(/no tiene WebGL2/)).toBeInTheDocument();
    expect(screen.getByText(/parks.json no está en esta base/)).toBeInTheDocument();
    expect(screen.queryByTestId('sim-fps')).not.toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Bateador diestro/ })).toHaveAttribute('data-side', 'R');
    expect(screen.getByRole('img')).toHaveAttribute('data-sky', 'harp');
    expect(document.querySelector('.sim')).toHaveAttribute('data-motion', readReduced() ? 'cut' : 'smooth');

    fireEvent.click(screen.getByRole('button', { name: 'Zurdo' }));
    expect(screen.getByRole('img', { name: /Bateador zurdo/ })).toHaveAttribute('data-side', 'L');
    expect(screen.getByRole('img', { name: /derecha del receptor/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Nivel del mar' }));
    expect(screen.getByRole('img', { name: /Nivel del mar, densidad relativa 1\.000/ })).toHaveAttribute('data-sky', 'sea');

    fireEvent.click(screen.getByRole('button', { name: 'Lanzador' }));
    expect(screen.getByRole('button', { name: 'Lanzador' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('status')).toHaveTextContent('Cámara Lanzador');
  });

  it('marca el corte de cámara cuando el sistema pide menos movimiento', () => {
    const previous = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: query.includes('reduce'),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as typeof window.matchMedia;
    render(<SimulatorScene />);
    expect(document.querySelector('.sim')).toHaveAttribute('data-motion', 'cut');
    window.matchMedia = previous;
  });
});
