/* Pure scene data. Density comes from the HACK-038 parks contract, never from a fixed altitude. */
import localParks from './parks.mock.json';

export type Hand = 'R' | 'L';
export type ViewId = 'catcher' | 'pitcher' | 'lateral' | 'broadcast';
export type ParkSide = 'harp' | 'sea';
export type Vec3 = [number, number, number];

export const VIEW_LABEL: Record<ViewId, string> = {
  catcher: 'Receptor',
  pitcher: 'Lanzador',
  lateral: 'Lateral',
  broadcast: 'Transmisión',
};

export const VIEWS: Record<ViewId, { pos: Vec3; target: Vec3; fov: number }> = {
  catcher: { pos: [0, 4.2, 16], target: [0, 2.6, -2], fov: 28 },
  pitcher: { pos: [0.6, 7.2, -66], target: [0, 3.2, -2], fov: 18 },
  lateral: { pos: [46, 10, -16], target: [0, 2.6, -(17 / 12)], fov: 28 },
  broadcast: { pos: [9, 15, 20], target: [0, 3.2, -62], fov: 46 },
};

export const ZONE = { half: 17 / 24, bottom: 1.5, top: 3.5, z: -(17 / 12) };
export const MOUND_Z = -60.5;
export const MOUND_H = 10 / 12;
export const BALL_R = 2.9 / 2 / 12;
export const PATH_SAMPLES = 32;
const RELEASE_Y = MOUND_H + 5.4;
const PLATE_Y = 2.45;

export interface Park {
  id: string;
  rho: number;
  bucket: string;
  airEffect: number | null;
  altitude: string;
  name: string;
}

export interface ParkBook {
  demoData: boolean;
  parks: Park[];
}

export interface LoadedParks {
  book: ParkBook;
  origin: 'file' | 'local';
}

export function parseParkBook(raw: unknown): ParkBook | null {
  if (!raw || typeof raw !== 'object') return null;
  const body = raw as Record<string, unknown>;
  if (!Array.isArray(body.parks)) return null;
  const parks: Park[] = [];
  for (const row of body.parks) {
    if (!row || typeof row !== 'object') continue;
    const item = row as Record<string, unknown>;
    const rho = typeof item.rho === 'number' ? item.rho : Number(item.rho);
    if (!Number.isFinite(rho)) continue;
    parks.push({
      id: String(item.id ?? parks.length),
      rho,
      bucket: typeof item.bucket === 'string' ? item.bucket : '',
      airEffect: typeof item.air_effect === 'number' ? item.air_effect : null,
      altitude: typeof item.altitude === 'string' ? item.altitude : '',
      name: typeof item.name === 'string' ? item.name : '',
    });
  }
  if (parks.length === 0) return null;
  return { demoData: body.demo_data !== false, parks };
}

const parsedLocal = parseParkBook(localParks);
if (!parsedLocal) throw new Error('mock de parques inválido');
export const LOCAL_BOOK: ParkBook = parsedLocal;

export function pickEnds(book: ParkBook): { harp: Park; sea: Park } {
  let harp = book.parks[0];
  let sea = book.parks[0];
  for (const park of book.parks) {
    if (park.rho < harp.rho) harp = park;
    if (Math.abs(park.rho - 1) < Math.abs(sea.rho - 1)) sea = park;
  }
  return { harp, sea };
}

export async function loadParkBook(fetchImpl: typeof fetch = fetch): Promise<LoadedParks> {
  try {
    const url = `${import.meta.env.BASE_URL}data/mock/parks.json`;
    const res = await fetchImpl(url, { signal: AbortSignal.timeout(2500) });
    if (!res.ok) return { book: LOCAL_BOOK, origin: 'local' };
    const book = parseParkBook(await res.json());
    if (!book) return { book: LOCAL_BOOK, origin: 'local' };
    return { book, origin: 'file' };
  } catch {
    return { book: LOCAL_BOOK, origin: 'local' };
  }
}

export function identifiesHarp(park: Park): boolean {
  const blob = `${park.id} ${park.name} ${park.altitude} ${park.bucket}`.toLowerCase();
  return /harp|helu|helú|cdmx/.test(blob);
}

export function endLabel(park: Park, side: ParkSide): string {
  if (side === 'harp' && identifiesHarp(park)) return 'Harp Helú';
  if (side === 'sea') return 'Nivel del mar';
  return 'Aire delgado';
}

/** The arc from placeholderPath is not flyPitch. The tag stays even when the park file is real. */
export function pathNote(): string {
  return 'Trayectoria de ejemplo.';
}

export function sourceLine(origin: LoadedParks['origin'], demo: boolean): string {
  const path = pathNote();
  if (origin === 'local') return `Ejemplo. parks.json no está en esta base. ${path}`;
  return demo ? `Ejemplo. Fuente: parks.json. ${path}` : `Fuente: parks.json. ${path}`;
}

export function cameraMoves(reduced: boolean): boolean {
  return !reduced;
}

export function cameraSmoothTime(reduced: boolean): number {
  return reduced ? 0 : 0.55;
}

export function showDevStats(dev: boolean): boolean {
  return dev;
}

export function readReduced(): boolean {
  if (typeof matchMedia !== 'function') return false;
  return matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function hasWebGL2(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2'));
  } catch {
    return false;
  }
}

export interface Palette {
  bg: string;
  surface: string;
  surface2: string;
  fg: string;
  red: string;
  sea: string;
  grass: string;
  grassDark: string;
  dirt: string;
  chalk: string;
  ball: string;
}

function token(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export function palette(): Palette {
  return {
    bg: token('--bg', '#0c0c0e'),
    surface: token('--surface', '#141417'),
    surface2: token('--surface-2', '#1c1c21'),
    fg: token('--fg', '#f1f1f3'),
    red: token('--red', '#c8102e'),
    sea: token('--sea', '#c9ccd3'),
    grass: token('--grass', '#2f4a35'),
    grassDark: token('--grass-dark', '#263d2c'),
    dirt: token('--dirt', '#6b4f3a'),
    chalk: token('--chalk', '#e8e6e1'),
    ball: token('--ball', '#efece6'),
  };
}

export function insideBand(side: Hand): { x: number; y: number; z: number; width: number; height: number } {
  const width = (ZONE.half * 2) / 3;
  const sign = side === 'R' ? -1 : 1;
  return {
    x: sign * (ZONE.half - width / 2),
    y: (ZONE.bottom + ZONE.top) / 2,
    z: ZONE.z,
    width,
    height: ZONE.top - ZONE.bottom,
  };
}

export function skylineProfile(kind: ParkSide): { ridges: boolean; stand: number[] } {
  if (kind === 'sea') return { ridges: false, stand: [4, 5, 4, 6, 4, 5, 4] };
  return { ridges: true, stand: [8, 14, 11, 18, 12, 16, 9] };
}

/** Visual arc only. HACK-045 replaces it with flyPitch. The gap scales with rho from the park file. */
export function placeholderPath(rho: number, seaRho: number, samples = PATH_SAMPLES): Vec3[] {
  const thin = Math.max(0, seaRho - rho);
  const pts: Vec3[] = [];
  for (let i = 0; i < samples; i += 1) {
    const u = samples === 1 ? 1 : i / (samples - 1);
    const z = MOUND_Z + (ZONE.z - MOUND_Z) * u;
    const y = RELEASE_Y * (1 - u) + PLATE_Y * u + thin * 7 * Math.sin(Math.PI * u);
    const x = thin * 1.4 * u * u;
    pts.push([x, y, z]);
  }
  return pts;
}

export function pointAt(path: Vec3[], u: number): Vec3 {
  if (path.length === 0) return [0, 0, 0];
  const t = Math.min(1, Math.max(0, u));
  const f = t * (path.length - 1);
  const i = Math.floor(f);
  const j = Math.min(path.length - 1, i + 1);
  const k = f - i;
  const a = path[i];
  const b = path[j];
  return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
}

const BATTER_X = 2.9;
const BATTER_Z = -1.1;

export function batterFrame(from: Hand, to: Hand, t: number): { x: number; y: number; z: number; mirror: number } {
  const u = Math.min(1, Math.max(0, t));
  const eased = u < 0.5 ? 2 * u * u : 1 - ((-2 * u + 2) ** 2) / 2;
  const xOf = (hand: Hand) => (hand === 'R' ? -1 : 1) * BATTER_X;
  const x0 = xOf(from);
  const x1 = xOf(to);
  const arc = Math.sin(Math.PI * eased);
  const m0 = from === 'R' ? 1 : -1;
  const m1 = to === 'R' ? 1 : -1;
  const m = m0 + (m1 - m0) * eased;
  return {
    x: x0 + (x1 - x0) * eased,
    y: 0.55 * arc,
    z: BATTER_Z + 3.1 * arc,
    mirror: Math.abs(m) < 0.02 ? 0.02 * m1 : m,
  };
}

export function sceneSummary(input: {
  hand: Hand;
  park: ParkSide;
  parkName: string;
  rho: number;
  view: ViewId;
  demo: boolean;
}): string {
  const batter = input.hand === 'R' ? 'diestro' : 'zurdo';
  const edge = input.hand === 'R' ? 'izquierda' : 'derecha';
  const data = input.demo ? ' Datos de ejemplo.' : '';
  return `Bateador ${batter}. Adentro hacia la ${edge} del receptor. ${input.parkName}, densidad relativa ${input.rho.toFixed(3)}. Cámara ${VIEW_LABEL[input.view]}. ${pathNote()}${data}`;
}
