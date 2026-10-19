import { fireEvent, render, screen } from '@testing-library/react';
import csv from '../../../../reports/altitude_delta/delta_by_shape.csv?raw';
import type { CompositeModel, PitchingModel } from '../../model/predict';
import locationJson from '../../../public/data/models/location.json';
import stuffJson from '../../../public/data/models/stuff.json';
import pitchingJson from '../../../public/data/models/pitching.json';
import pitcher from '../../../public/data/mock/pitcher/pitcher_00019.json';
import { PLATE_FRONT_FT } from '../../physics/flight';
import { HARP_RHO, SHAPE_PRESETS, STAFF, staffRelease } from './flight/presets';
import { plateGap, scenePath, throwPair } from './flight/throw';
import { loadModels, scoreRelease, stuffDelta, type Models } from './panel/score';
import { countValue } from './panel/Controls';
import { Simulador } from './index';

const models: Models = {
  stuff: stuffJson as CompositeModel,
  location: locationJson as CompositeModel,
  demo: stuffJson.demo_data !== false || locationJson.demo_data !== false,
};

function publishedDeltas(csv: string): Map<string, number> {
  const [head, ...lines] = csv.trim().split(/\r?\n/);
  const cols = head.split(',');
  const shapeAt = cols.indexOf('shape');
  const deltaAt = cols.indexOf('delta_stuff');
  const out = new Map<string, number>();
  for (const line of lines) {
    const cells = line.split(',');
    out.set(cells[shapeAt], Number(cells[deltaAt]));
  }
  return out;
}

beforeAll(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
});

afterAll(() => {
  vi.restoreAllMocks();
});

describe('presets contra delta_by_shape', () => {
  const published = publishedDeltas(csv);

  it('cada forma en Harp Helú reproduce su ΔStuff+ a ±1.5', () => {
    expect(SHAPE_PRESETS.length).toBe(published.size);
    for (const release of SHAPE_PRESETS) {
      const target = published.get(release.shape ?? '');
      expect(target, release.shape ?? '').toBeTypeOf('number');
      const delta = stuffDelta(release, HARP_RHO, models);
      expect(Math.abs(delta - (target as number)), `${release.shape} got ${delta}`).toBeLessThanOrEqual(1.5);
    }
  });

  it('el personal sale del agregado de pitcher_00019', () => {
    const live = staffRelease(pitcher as Parameters<typeof staffRelease>[0]);
    expect(STAFF.family).toBe(live.family);
    expect(STAFF.velo).toBeCloseTo(live.velo, 3);
    expect(STAFF.ivb).toBeCloseTo(live.ivb, 3);
    expect(STAFF.hb).toBeCloseTo(live.hb, 3);
    expect(STAFF.label).toBe('Lanzador del staff');
    expect(STAFF.source).toMatch(/pitcher_00019/);
    expect(STAFF.source).toMatch(/ejemplo/);
  });
});

describe('vuelo', () => {
  it('dibuja el mismo lanzamiento en el mar y en el parque, y deja el plato en pulgadas', () => {
    const ride = SHAPE_PRESETS[0];
    const { sea, park } = throwPair(ride, HARP_RHO);
    const seaPath = scenePath(sea);
    const parkPath = scenePath(park);
    expect(seaPath.length).toBeGreaterThan(8);
    expect(parkPath.length).toBeGreaterThan(8);
    expect(seaPath[seaPath.length - 1][2]).toBeCloseTo(-PLATE_FRONT_FT, 5);
    expect(parkPath[parkPath.length - 1][2]).toBeCloseTo(-PLATE_FRONT_FT, 5);
    const gap = plateGap(sea, park);
    expect(Math.abs(gap.ivb)).toBeGreaterThan(0.5);
    expect(Math.hypot(gap.xIn, gap.zIn)).toBeGreaterThan(0.5);
  });

  it('pone la salida de un derecho a la izquierda del receptor y la de un zurdo a la derecha', () => {
    const ride = SHAPE_PRESETS[0];
    const { sea } = throwPair(ride, HARP_RHO);
    expect(scenePath(sea, 'R')[0][0]).toBeLessThan(0);
    expect(scenePath(sea, 'L')[0][0]).toBeGreaterThan(0);
  });
});

describe('panel', () => {
  it('muestra el modelo real, el delta y los puntos en el plato', () => {
    render(<Simulador models={models} />);
    expect(screen.getByTestId('model-badge')).toHaveTextContent('modelo real');
    expect(screen.getByTestId('stuff-delta').textContent).toMatch(/−1[0-9]\.[0-9]/);
    expect(screen.getByRole('button', { name: 'Recta de ride' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Sweeper' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Splitter' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Lanzador del staff' })).toBeInTheDocument();
    expect(screen.getAllByText(/En el plato/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/¿Por qué\?/)).toBeInTheDocument();
    expect(document.querySelector('.fb-ball')).toBeTruthy();
    expect(document.querySelector('.fb-ghost')).toBeTruthy();
    expect(document.querySelector('.sim')).toHaveAttribute('data-controlled', 'on');

    fireEvent.click(screen.getByRole('button', { name: 'Lanzador del staff' }));
    expect(screen.getByRole('button', { name: 'Lanzador del staff' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText(/agregado de ejemplo/)).toBeInTheDocument();
  });
});

describe('revisión', () => {
  it('no muestra Stuff+ en la celda de Pitching+ mientras no hay modelo de Pitching+', () => {
    render(<Simulador models={models} />);
    const cells = screen.getAllByTestId('pitching-cell');
    expect(cells).toHaveLength(2);
    for (const cell of cells) expect(cell).toHaveTextContent('sin modelo');
  });

  it('el conteo solo acepta enteros de 0 a 3 bolas y de 0 a 2 strikes', () => {
    expect(countValue('99', 3)).toBe(3);
    expect(countValue('-1', 3)).toBe(0);
    expect(countValue('1.5', 3)).toBe(1);
    expect(countValue('', 2)).toBe(0);
    expect(countValue('2', 2)).toBe(2);
  });
});

describe('Pitching+ (HACK-079)', () => {
  const withPitching: Models = { ...models, pitching: pitchingJson as unknown as PitchingModel };

  it('con models/pitching.json la celda muestra Pitching+ real en ambos aires', () => {
    render(<Simulador models={withPitching} />);
    const cells = screen.getAllByTestId('pitching-cell');
    expect(cells).toHaveLength(2);
    for (const cell of cells) {
      expect(cell).not.toHaveTextContent('sin modelo');
      expect(Number(cell.textContent?.replace('−', '-'))).toBeGreaterThan(40);
    }
    expect(screen.getByText(/bateador promedio de la LMB/)).toBeInTheDocument();
  });

  it('cada forma da un Pitching+ finito y propio (no repite Stuff+) a nivel del mar y en Harp Helú', () => {
    for (const release of SHAPE_PRESETS) {
      const pair = scoreRelease(release, HARP_RHO, withPitching);
      for (const side of [pair.sea, pair.park]) {
        expect(side.pitchingSource).toBe('model');
        expect(Number.isFinite(side.pitching)).toBe(true);
        expect(side.pitching).toBeGreaterThan(40);
        expect(side.pitching).toBeLessThan(160);
      }
    }
  });

  it('sin pitching.json la carga sigue y cae a "sin modelo"', async () => {
    const fake = (async (url: string) =>
      url.endsWith('pitching.json')
        ? new Response('', { status: 404 })
        : new Response(JSON.stringify(url.endsWith('stuff.json') ? stuffJson : locationJson))) as unknown as typeof fetch;
    const loaded = await loadModels(fake);
    expect(loaded.pitching).toBeNull();
    expect(scoreRelease(SHAPE_PRESETS[0], HARP_RHO, loaded).sea.pitchingSource).toBe('stuff-fallback');
  });
});
