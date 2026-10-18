/* Data and physics for /fisica (HACK-072). The Magnus elasticity and its interval come from the contract physics.json
   (data/real or data/mock); the typical sea-level shape of each family from shapes.json (make_data.py, copied from
   reports/physics_v2); the flights from the browser RK4 engine (web/src/physics/flight.ts, HACK-041). */
import { flyPitch, type Family, type Flight } from '../../physics/flight';
import engine from '../../physics/physics.json';
import { loadDoc, type Source } from '../staff/data';
import shapesDoc from './shapes.json';

export interface PhysicsFamily {
  pitch_family: string;
  cd_sea: number;
  elasticity: number;
  elasticity_lo: number;
  elasticity_hi: number;
}
export interface PhysicsDoc {
  demo_data: boolean;
  sources: string[];
  families: PhysicsFamily[];
}
export interface Shape {
  pitch_family: string;
  pitches: number;
  velo: number;
  ivb: number;
  hb: number;
}

export const SHAPES: Shape[] = shapesDoc.shapes;
export const SHAPES_SOURCE = shapesDoc.sources[0];
/** Relative air density of the Harp Helú, the one the flight engine uses (HACK-041). */
export const RHO_HARP: number = engine.rho.harp_helu;

export const FAMILY_LABEL: Record<string, string> = {
  'Four-Seam': 'Recta de 4 costuras', Sinker: 'Sinker', Cutter: 'Cutter', Slider: 'Slider', Curveball: 'Curva',
  Changeup: 'Cambio', Splitter: 'Splitter',
};
/** Spanish noun with its article, and whether "típico" agrees in feminine. */
export const NOUN: Record<string, [string, boolean]> = {
  'Four-Seam': ['la recta de 4 costuras', true], Sinker: ['el sinker', false], Cutter: ['el cutter', false],
  Slider: ['el slider', false], Curveball: ['la curva', true], Changeup: ['el cambio', false], Splitter: ['el splitter', false],
};
/** Display order: fastballs first, then breaking balls, then offspeed. */
export const ORDER = ['Four-Seam', 'Sinker', 'Cutter', 'Slider', 'Curveball', 'Changeup', 'Splitter'];

export const loadPhysics = () => loadDoc<PhysicsDoc>('physics.json');
export type { Source };

export interface Comparison {
  family: string;
  rho: number;
  elasticity: number;
  sea: Flight;
  measured: Flight;
  textbook: Flight;
  /** Fraction of the sea-level force left in air `rho`. */
  drag: number;
  magnusMeasured: number;
  magnusTextbook: number;
  /** Inches of movement lost at the plate along the pitch's own break (positive = less than at sea level). */
  moveLost: number;
  moveLostTextbook: number;
  /** Inches the pitch crosses lower than at sea level. */
  drop: number;
}

/** The same release thrown at sea level, in air `rho` with the measured elasticity, and in air `rho` with textbook
 *  physics (elasticity 1). */
export function compare(shape: Shape, fam: PhysicsFamily, rho: number): Comparison {
  const base = { velo: shape.velo, ivb: shape.ivb, hb: shape.hb, family: shape.pitch_family as Family };
  const sea = flyPitch({ ...base, rho: 1, elasticity: fam.elasticity });
  const measured = flyPitch({ ...base, rho, elasticity: fam.elasticity });
  const textbook = flyPitch({ ...base, rho, elasticity: 1 });
  const mag = Math.hypot(sea.ivb, sea.hb);
  // movement lost along the pitch's own break direction, so curveballs and sliders read as positive too
  const along = (f: Flight) => (mag === 0 ? 0 : (sea.ivb * (sea.ivb - f.ivb) + sea.hb * (sea.hb - f.hb)) / mag);
  return {
    family: shape.pitch_family,
    rho,
    elasticity: fam.elasticity,
    sea,
    measured,
    textbook,
    drag: rho,
    magnusMeasured: rho ** fam.elasticity,
    magnusTextbook: rho,
    moveLost: along(measured),
    moveLostTextbook: along(textbook),
    drop: (sea.plateZ - measured.plateZ) * 12,
  };
}

const MINUS = '−';
export function fmt(v: number, digits = 1): string {
  const s = Math.abs(v).toFixed(digits);
  return v < 0 && Number(s) !== 0 ? MINUS + s : s;
}
export const pct = (v: number) => `${Math.round(v * 100)} %`;
