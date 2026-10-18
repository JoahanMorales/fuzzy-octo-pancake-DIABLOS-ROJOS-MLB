/**
 * Shape releases next to each shape's centroid in `reports/shapes/shapes.csv` (within 3 mph, 2 in of IVB, 4 in of HB
 * and 200 rpm) whose ΔStuff+, scored by the production Stuff+ v2 trees (HACK-066) and `physics_translator`, lands
 * within ±1.5 of `reports/altitude_delta/delta_by_shape.csv` at `physics.json` → `rho.harp_helu`. The primary
 * fastball is the 4S centroid. Representative releases, not league means: the model is non-linear, so the centroid
 * itself does not reproduce the shape's mean ΔStuff+.
 */
import type { Family } from '../../../physics/flight';
import physics from '../../../physics/physics.json';

export const HARP_RHO = physics.rho.harp_helu;
export const RHO_REF = physics.translator.rho_ref;

export interface Release {
  id: string;
  label: string;
  shape: string | null;
  family: Family;
  velo: number;
  spin: number;
  axis: number;
  ivb: number;
  hb: number;
  height: number;
  side: number;
  extension: number;
  throws: 'R' | 'L';
  fastball: boolean;
  fbVelo: number;
  fbIvb: number;
  fbHb: number;
  /** Where the release came from, shown next to the number. */
  source: string;
}

const FB = { fbVelo: 90.8, fbIvb: 12.8, fbHb: 9.1 }; // 4S centroid, reports/shapes/shapes.csv
const BODY = { height: 5.9, side: 1.7, extension: 6.3, throws: 'R' as const };

interface Seed {
  shape: string;
  label: string;
  family: Family;
  velo: number;
  spin: number;
  axis: number;
  ivb: number;
  hb: number;
  fastball?: boolean;
}

const SEEDS: Seed[] = [
  { shape: 'riding 4S', label: 'Recta de ride', family: 'Four-Seam', velo: 91.7, spin: 2434, axis: 185, ivb: 20.5, hb: 9.7, fastball: true },
  { shape: '4S', label: 'Recta de cuatro', family: 'Four-Seam', velo: 89.3, spin: 2386, axis: 200, ivb: 12.8, hb: 7.1, fastball: true },
  { shape: 'sweeper', label: 'Sweeper', family: 'Slider', velo: 82.2, spin: 2606, axis: 280, ivb: -2.7, hb: -11.3 },
  { shape: 'slider', label: 'Slider', family: 'Slider', velo: 83.1, spin: 2475, axis: 250, ivb: 2, hb: -8.7 },
  { shape: 'gyro slider', label: 'Gyro', family: 'Slider', velo: 84.8, spin: 2246, axis: 220, ivb: 5.4, hb: 1.9 },
  { shape: 'splitter', label: 'Splitter', family: 'Splitter', velo: 81.6, spin: 1518, axis: 190, ivb: -0.3, hb: 1.9 },
  { shape: '12-6 CB', label: 'Curva 12-6', family: 'Curveball', velo: 80.1, spin: 2426, axis: 20, ivb: -4.5, hb: -2.2 },
  { shape: '11-5 CB', label: 'Curva 11-5', family: 'Curveball', velo: 78.1, spin: 2514, axis: 50, ivb: -6.9, hb: -10.9 },
  { shape: 'cutter', label: 'Cutter', family: 'Cutter', velo: 86.8, spin: 2365, axis: 160, ivb: 10.3, hb: 0.9 },
  { shape: 'running 2S', label: 'Dos costuras', family: 'Sinker', velo: 91.5, spin: 2182, axis: 230, ivb: 15.3, hb: 12.3, fastball: true },
  { shape: 'sinking 2S', label: 'Sinker', family: 'Sinker', velo: 88.9, spin: 2130, axis: 240, ivb: 6.4, hb: 16.4, fastball: true },
  { shape: 'changeup', label: 'Cambio', family: 'Changeup', velo: 81.4, spin: 2060, axis: 220, ivb: 4, hb: 8.7 },
  { shape: 'power CH', label: 'Cambio de poder', family: 'Changeup', velo: 89.7, spin: 2004, axis: 210, ivb: 12, hb: 12.1 },
];

export const SHAPE_PRESETS: Release[] = SEEDS.map((seed) => ({
  id: seed.shape,
  label: seed.label,
  shape: seed.shape,
  family: seed.family,
  velo: seed.velo,
  spin: seed.spin,
  axis: seed.axis,
  ivb: seed.ivb,
  hb: seed.hb,
  ...BODY,
  fastball: Boolean(seed.fastball),
  ...FB,
  source: 'reports/altitude_delta/delta_by_shape.csv',
}));

export const RIDE = SHAPE_PRESETS[0];

interface ArsenalPitch {
  pitch_id: number;
  pitch_family: string;
  shape: string;
  pitches: number;
  velo: number;
  ivb: number;
  hb: number;
  spin: number;
}

interface PitcherFile {
  id: string;
  demo_data?: boolean;
  seasons: { throws: string; arsenal_pitches: ArsenalPitch[] }[];
}

function mostUsed(rows: ArsenalPitch[]): ArsenalPitch {
  return rows.reduce((best, row) => (row.pitches > best.pitches ? row : best));
}

/** Most-used pitch of pitcher_00019 (mock), with his primary fastball as the arsenal reference. */
const STAFF_SNAPSHOT: PitcherFile = {
  id: 'pitcher_00019',
  demo_data: true,
  seasons: [{
    throws: 'Right',
    arsenal_pitches: [
      { pitch_id: 1, pitch_family: 'Sinker', shape: 'running 2S', pitches: 188, velo: 93.944, ivb: 9.758, hb: 11.144, spin: 2340.046 },
      { pitch_id: 4, pitch_family: 'Slider', shape: 'gyro slider', pitches: 232, velo: 85.021, ivb: -0.469, hb: -5.687, spin: 2561.946 },
    ],
  }],
};

export function staffRelease(file: PitcherFile = STAFF_SNAPSHOT): Release {
  const season = file.seasons[file.seasons.length - 1];
  const pitch = mostUsed(season.arsenal_pitches);
  const fastballs = season.arsenal_pitches.filter((row) => row.pitch_family === 'Four-Seam' || row.pitch_family === 'Sinker');
  const fb = fastballs.length ? mostUsed(fastballs) : pitch;
  const fastball = pitch.pitch_family === 'Four-Seam' || pitch.pitch_family === 'Sinker';
  const axis = (Math.atan2(pitch.hb, pitch.ivb) * 180) / Math.PI;
  return {
    id: 'staff',
    label: 'Lanzador del staff',
    shape: null,
    family: pitch.pitch_family as Family,
    velo: pitch.velo,
    spin: pitch.spin,
    axis: (axis + 360) % 360,
    ivb: pitch.ivb,
    hb: pitch.hb,
    ...BODY,
    throws: season.throws === 'Left' ? 'L' : 'R',
    fastball,
    fbVelo: fb.velo,
    fbIvb: fb.ivb,
    fbHb: fb.hb,
    source: file.demo_data === false
      ? `${file.id} · pitch_id ${pitch.pitch_id}`
      : `${file.id} · pitch_id ${pitch.pitch_id} · agregado de ejemplo`,
  };
}

export const STAFF = staffRelease();

export const SHORTCUTS: { id: string; label: string; release: Release }[] = [
  { id: 'ride', label: 'Recta de ride', release: RIDE },
  { id: 'sweeper', label: 'Sweeper', release: SHAPE_PRESETS.find((row) => row.shape === 'sweeper')! },
  { id: 'splitter', label: 'Splitter', release: SHAPE_PRESETS.find((row) => row.shape === 'splitter')! },
  { id: 'staff', label: 'Lanzador del staff', release: STAFF },
];

export function byShape(shape: string): Release | undefined {
  return SHAPE_PRESETS.find((row) => row.shape === shape);
}
