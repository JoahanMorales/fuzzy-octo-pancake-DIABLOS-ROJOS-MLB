/**
 * In-browser prospect profiler (HACK-048): a CSV arsenal → Stuff+ neutral and Stuff+ en CDMX, scored with the
 * exported pitch_family composite (HACK-040). The file is parsed and scored here; nothing is sent anywhere.
 *
 * Ports `stuffplus/prospect.py` (column names, Trackman aggregation, primary fastball by usage), the arm-side
 * frame of `models.common.add_arm_side_features`, and `altitude.physics_translator` with the paper's k
 * (physics.json, HACK-041). Two deliberate fixes over prospect.py: friendly release columns (rel_height,
 * rel_side, extension) are read, and the default release side is on the arm side for lefties too.
 */
import physics from '../../physics/physics.json';
import { predict, toPlus, type CompositeModel, type FeatureRow } from '../../model/predict';

export const PITCH_TYPES = ['Four-Seam', 'Sinker', 'Cutter', 'Slider', 'Curveball', 'Changeup', 'Splitter'] as const;
const FASTBALL_TYPES = ['Four-Seam', 'Sinker', 'Cutter'];
const TYPE_MAP: Record<string, string> = { Sweeper: 'Slider' };
const MIN_PITCHES = 2;
const MAX_PITCHES = 5;
const DEFAULTS = { rel_height: 5.8, rel_side_arm: 1.8, extension: 6.1, rho_measured: 1.0 };
const RANGES: [keyof PitchSpec, number, number][] = [
  ['velo', 55, 106], ['spin_rate', 300, 3800], ['spin_axis', 0, 360], ['ivb', -35, 35], ['hb', -35, 35], ['extension', 3.5, 8.5],
];
// Trackman column → profiler name (stuffplus/prospect.py _TRACKMAN)
const TRACKMAN: Record<string, keyof PitchSpec> = {
  AutoPitchType: 'pitch_type', PitcherThrows: 'throws', RelSpeed: 'velo', SpinRate: 'spin_rate', SpinAxis: 'spin_axis',
  InducedVertBreak: 'ivb', HorzBreak: 'hb', RelHeight: 'rel_height', RelSide: 'rel_side', Extension: 'extension',
};

export interface PitchSpec {
  pitch_type: string;
  throws: 'Right' | 'Left';
  velo: number;
  spin_rate: number;
  spin_axis: number;
  ivb: number;
  hb: number; // Trackman sign (catcher's view)
  rel_height: number;
  rel_side: number; // Trackman sign
  extension: number;
  rho_measured: number;
}

export interface ScoredPitch {
  pitch: PitchSpec;
  usage: number;
  features: FeatureRow;
  stuffNeutral: number;
  stuffCdmx: number;
}

export interface Profile {
  pitches: ScoredPitch[];
  arsenalNeutral: number;
  arsenalCdmx: number;
  rhoHarpHelu: number;
}

export class ProfileError extends Error {}

/** Minimal RFC 4180 CSV reader (quotes, escaped quotes, CRLF). */
export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [], cell = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') quoted = false;
      else cell += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); cell = '';
      if (row.some((v) => v.trim() !== '')) rows.push(row);
      row = [];
    } else cell += c;
  }
  row.push(cell);
  if (row.some((v) => v.trim() !== '')) rows.push(row);
  if (rows.length < 2) throw new ProfileError('el CSV no trae lanzamientos');
  const header = rows[0].map((h) => h.trim());
  return rows.slice(1).map((r) => Object.fromEntries(header.map((h, j) => [h, (r[j] ?? '').trim()])));
}

const num = (v: string | undefined) => (v === undefined || v === '' ? NaN : Number(v));
const mean = (xs: number[]) => {
  const ok = xs.filter((x) => Number.isFinite(x));
  return ok.length ? ok.reduce((a, b) => a + b, 0) / ok.length : NaN;
};
const mod360 = (x: number) => ((x % 360) + 360) % 360;

function throwsOf(v: string | undefined): 'Right' | 'Left' {
  const s = (v ?? '').trim().toLowerCase();
  if (['right', 'r', 'derecho', 'd'].includes(s)) return 'Right';
  if (['left', 'l', 'zurdo', 'z', 'i'].includes(s)) return 'Left';
  throw new ProfileError(`mano de lanzar no reconocida: "${v ?? ''}" (usa Right o Left)`);
}

function typeOf(v: string | undefined): string {
  const t = TYPE_MAP[(v ?? '').trim()] ?? (v ?? '').trim();
  if (!(PITCH_TYPES as readonly string[]).includes(t)) {
    throw new ProfileError(`tipo de lanzamiento no reconocido: "${v ?? ''}" (usa ${PITCH_TYPES.join(', ')})`);
  }
  return t;
}

function validate(p: PitchSpec): PitchSpec {
  for (const [k, lo, hi] of RANGES) {
    const v = p[k] as number;
    if (!Number.isFinite(v) || v < lo || v > hi) throw new ProfileError(`${k}=${v} fuera de ${lo} a ${hi} (${p.pitch_type})`);
  }
  return p;
}

function fromRow(row: Record<string, string>): { pitch: PitchSpec; usage: number | null } {
  const get = (name: keyof PitchSpec) => {
    const tm = Object.keys(TRACKMAN).find((k) => TRACKMAN[k] === name);
    const v = tm !== undefined && row[tm] !== undefined && row[tm] !== '' ? row[tm] : row[name];
    return v === undefined || v === '' ? undefined : v;
  };
  const missing = (['pitch_type', 'throws', 'velo', 'spin_rate', 'spin_axis', 'ivb', 'hb'] as const).filter((k) => get(k) === undefined);
  if (missing.length) throw new ProfileError(`faltan columnas para armar el lanzamiento: ${missing.join(', ')}`);
  const throws = throwsOf(get('throws'));
  const sign = throws === 'Right' ? 1 : -1;
  const relSide = get('rel_side');
  const pitch = validate({
    pitch_type: typeOf(get('pitch_type')),
    throws,
    velo: num(get('velo')),
    spin_rate: num(get('spin_rate')),
    spin_axis: mod360(num(get('spin_axis'))),
    ivb: num(get('ivb')),
    hb: num(get('hb')),
    rel_height: num(get('rel_height') ?? String(DEFAULTS.rel_height)),
    rel_side: relSide === undefined ? DEFAULTS.rel_side_arm * sign : num(relSide),
    extension: num(get('extension') ?? String(DEFAULTS.extension)),
    rho_measured: num(row.rho_measured || String(DEFAULTS.rho_measured)),
  });
  const u = row.usage;
  return { pitch, usage: u === undefined || u === '' ? null : Number(u) };
}

function circularMean(deg: number[]): number {
  const a = deg.filter(Number.isFinite).map((d) => (d * Math.PI) / 180);
  if (!a.length) throw new ProfileError('SpinAxis vacío');
  const s = a.reduce((t, x) => t + Math.sin(x), 0) / a.length;
  const c = a.reduce((t, x) => t + Math.cos(x), 0) / a.length;
  return mod360((Math.atan2(s, c) * 180) / Math.PI);
}

/** Trackman pitch-level rows → one pitch per type (mean shape, circular-mean axis), usage = pitch count. */
function aggregate(rows: Record<string, string>[]): { pitch: PitchSpec; usage: number }[] {
  if (!('AutoPitchType' in rows[0])) throw new ProfileError('el CSV Trackman necesita la columna AutoPitchType');
  if (!('PitcherThrows' in rows[0])) throw new ProfileError('el CSV Trackman necesita la columna PitcherThrows');
  const groups = new Map<string, Record<string, string>[]>();
  for (const r of rows) {
    const t = TYPE_MAP[r.AutoPitchType] ?? r.AutoPitchType;
    if (!(PITCH_TYPES as readonly string[]).includes(t)) continue;
    groups.set(t, [...(groups.get(t) ?? []), r]);
  }
  const out = [...groups.entries()]
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([type, sub]) => {
      const col = (c: string) => sub.map((r) => num(r[c]));
      const hands = sub.map((r) => r.PitcherThrows).filter(Boolean);
      const counts = new Map<string, number>();
      hands.forEach((h) => counts.set(h, (counts.get(h) ?? 0) + 1));
      const top = Math.max(...counts.values());
      const throws = throwsOf([...counts.keys()].filter((h) => counts.get(h) === top).sort()[0]);
      const opt = (c: string, d: number) => (c in sub[0] && col(c).some(Number.isFinite) ? mean(col(c)) : d);
      return {
        pitch: validate({
          pitch_type: type, throws, velo: mean(col('RelSpeed')), spin_rate: mean(col('SpinRate')),
          spin_axis: circularMean(col('SpinAxis')), ivb: mean(col('InducedVertBreak')), hb: mean(col('HorzBreak')),
          rel_height: opt('RelHeight', DEFAULTS.rel_height),
          rel_side: opt('RelSide', DEFAULTS.rel_side_arm * (throws === 'Right' ? 1 : -1)),
          extension: opt('Extension', DEFAULTS.extension), rho_measured: DEFAULTS.rho_measured,
        }),
        usage: sub.length,
      };
    })
    .sort((a, b) => b.usage - a.usage)
    .slice(0, MAX_PITCHES);
  if (out.length < MIN_PITCHES) throw new ProfileError(`el CSV quedó con ${out.length} tipos de lanzamiento; hacen falta al menos ${MIN_PITCHES}`);
  return out;
}

function usages(raw: (number | null)[]): number[] {
  if (raw.some((u) => u !== null && u < 0)) throw new ProfileError('el uso no puede ser negativo');
  if (raw.every((u) => u === null)) return raw.map(() => 1 / raw.length);
  const filled = raw.map((u) => u ?? 0);
  const total = filled.reduce((a, b) => a + b, 0);
  return total <= 0 ? raw.map(() => 1 / raw.length) : filled.map((u) => u / total);
}

/** CSV text → 2–5 pitches with normalized usage (stuffplus.prospect._parse). */
export function parseArsenal(text: string): { pitch: PitchSpec; usage: number }[] {
  const rows = parseCsv(text);
  const header = Object.keys(rows[0]);
  const trackman = header.includes('AutoPitchType') || header.includes('RelSpeed');
  const types = new Set(rows.map((r) => r.AutoPitchType).filter(Boolean));
  let parsed: { pitch: PitchSpec; usage: number | null }[];
  if (trackman && (rows.length > MAX_PITCHES || types.size < rows.length)) parsed = aggregate(rows);
  else parsed = rows.map(fromRow);
  if (parsed.length < MIN_PITCHES || parsed.length > MAX_PITCHES) {
    throw new ProfileError(`el arsenal debe tener entre ${MIN_PITCHES} y ${MAX_PITCHES} lanzamientos (llegaron ${parsed.length})`);
  }
  const u = usages(parsed.map((p) => p.usage));
  return parsed.map((p, i) => ({ pitch: p.pitch, usage: u[i] }));
}

/** Model features in the pitch's own air (arm-side frame, diffs against the primary fastball). */
export function features(arsenal: { pitch: PitchSpec; usage: number }[]): FeatureRow[] {
  const fbs = arsenal.filter((a) => FASTBALL_TYPES.includes(a.pitch.pitch_type));
  const primary = fbs.length
    ? fbs.reduce((best, a) => (a.usage > best.usage || (a.usage === best.usage && a.pitch.velo > best.pitch.velo) ? a : best)).pitch
    : null;
  return arsenal.map(({ pitch: p }) => {
    const sign = p.throws === 'Right' ? 1 : -1;
    const hbArm = p.hb * sign;
    const relSideArm = p.rel_side * sign;
    return {
      RelSpeed: p.velo,
      SpinRate: p.spin_rate,
      spin_axis_arm: p.throws === 'Right' ? mod360(p.spin_axis) : mod360(360 - mod360(p.spin_axis)),
      InducedVertBreak: p.ivb,
      hb_arm: hbArm,
      RelHeight: p.rel_height,
      rel_side_arm: relSideArm,
      Extension: p.extension,
      arm_angle: (Math.atan2(p.rel_height - 5, Math.abs(relSideArm)) * 180) / Math.PI,
      is_rhp: p.throws === 'Right' ? 1 : 0,
      pitch_family: p.pitch_type,
      rho: p.rho_measured,
      velo_diff_fb: primary ? p.velo - primary.velo : NaN,
      ivb_diff_fb: primary ? p.ivb - primary.ivb : NaN,
      hb_diff_fb: primary ? hbArm - primary.hb * sign : NaN,
    };
  });
}

type K = { ivb: number; hb: number };
const TRANSLATOR = physics.translator as { rho_ref: number; k: Record<string, K> };
const shift = (y: number, k: number, rf: number, rt: number) => y * (1 + (k * (rt - rf)) / (1 + k * (rf - TRANSLATOR.rho_ref)));

/** stuffplus.altitude.physics_translator: per-family proportional shift; fastball diffs move with the four-seam k. */
export function translate(f: FeatureRow, rhoTo: number): FeatureRow {
  const fam = String(f.pitch_family);
  const k = TRANSLATOR.k[fam] ?? TRANSLATOR.k['Four-Seam'];
  const fb = TRANSLATOR.k['Four-Seam'];
  const rf = f.rho as number;
  const ivb = f.InducedVertBreak as number, hb = f.hb_arm as number;
  const newIvb = shift(ivb, k.ivb, rf, rhoTo), newHb = shift(hb, k.hb, rf, rhoTo);
  return {
    ...f,
    InducedVertBreak: newIvb,
    hb_arm: newHb,
    ivb_diff_fb: newIvb - shift(ivb - (f.ivb_diff_fb as number), fb.ivb, rf, rhoTo),
    hb_diff_fb: newHb - shift(hb - (f.hb_diff_fb as number), fb.hb, rf, rhoTo),
    rho: rhoTo,
  };
}

export const RHO_HARP_HELU = physics.rho.harp_helu;

/** Parse, build features, move each pitch to sea level and to Harp Helú air, score with the TS model. */
export function profileArsenal(text: string, model: CompositeModel): Profile {
  const arsenal = parseArsenal(text);
  const feats = features(arsenal);
  const pitches = arsenal.map(({ pitch, usage }, i) => ({
    pitch,
    usage,
    features: feats[i],
    stuffNeutral: toPlus(model, predict(model, translate(feats[i], 1.0)).xrv),
    stuffCdmx: toPlus(model, predict(model, translate(feats[i], RHO_HARP_HELU)).xrv),
  }));
  const weighted = (key: 'stuffNeutral' | 'stuffCdmx') => pitches.reduce((t, p) => t + p[key] * p.usage, 0);
  return { pitches, arsenalNeutral: weighted('stuffNeutral'), arsenalCdmx: weighted('stuffCdmx'), rhoHarpHelu: RHO_HARP_HELU };
}
