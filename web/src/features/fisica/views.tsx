/* The three graphics of /fisica: side view and catcher view of the same release in two airs, and the measured
   Magnus elasticity per family against textbook physics. Plain SVG; CDMX air is red and solid, sea level grey and
   dashed, textbook physics red and dotted (DESIGN.md, charts). */
import type { Flight } from '../../physics/flight';
import { FAMILY_LABEL, fmt, ORDER, type Comparison, type PhysicsFamily } from './data';

const PLATE_HALF = 17 / 24; // feet
const ZONE = { bottom: 1.5, top: 3.5 }; // feet, the generic zone the simulator draws
const BALL_R = 2.9 / 24; // feet

function Legend() {
  return (
    <ul className="fis-legend" aria-label="Leyenda">
      <li><svg width="28" height="10" aria-hidden="true"><line x1="0" y1="5" x2="28" y2="5" className="fis-l-hh" /></svg>Aire elegido, elasticidad medida</li>
      <li><svg width="28" height="10" aria-hidden="true"><line x1="0" y1="5" x2="28" y2="5" className="fis-l-book" /></svg>Aire elegido, física de libro</li>
      <li><svg width="28" height="10" aria-hidden="true"><line x1="0" y1="5" x2="28" y2="5" className="fis-l-sea" /></svg>Nivel del mar</li>
    </ul>
  );
}

/** Side view: distance to home plate on x (mound left, plate right), height on y. */
export function SideView({ cmp, anim, motion }: { cmp: Comparison; anim: number; motion: boolean }) {
  const W = 640, H = 300, L = 44, R = 150, T = 16, B = 34;
  const flights = [cmp.sea, cmp.textbook, cmp.measured];
  const zs = flights.flatMap((f) => f.pos.map((p) => p[2]));
  const zMin = Math.floor(Math.min(...zs) - 0.3), zMax = Math.ceil(Math.max(...zs) + 0.3);
  const yMax = Math.ceil(cmp.sea.pos[0][1]);
  const sx = (y: number) => L + ((yMax - y) / yMax) * (W - L - R);
  const sy = (z: number) => T + ((zMax - z) / (zMax - zMin)) * (H - T - B);
  const d = (f: Flight) => f.pos.map((p, i) => `${i ? 'L' : 'M'}${sx(p[1]).toFixed(1)},${sy(p[2]).toFixed(1)}`).join('');
  const end = (f: Flight) => f.pos[f.pos.length - 1];
  const ticksX = Array.from({ length: Math.floor(yMax / 10) + 1 }, (_, i) => i * 10);
  const ticksZ = Array.from({ length: zMax - zMin + 1 }, (_, i) => zMin + i);
  const eSea = end(cmp.sea), eHH = end(cmp.measured);
  const bx = sx(eHH[1]) + 14;
  return (
    <figure className="fis-fig">
      <figcaption>Vista lateral · altura en pies contra distancia al plato</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Vista lateral: a nivel del mar la bola cruza a ${fmt(eSea[2] * 12)} pulgadas del suelo; en el aire elegido a ${fmt(eHH[2] * 12)}.`}>
        {ticksZ.map((z) => (
          <g key={z}>
            <line x1={L} x2={W - R} y1={sy(z)} y2={sy(z)} className="fis-grid" />
            <text x={L - 8} y={sy(z) + 4} className="fis-tick" textAnchor="end">{z}</text>
          </g>
        ))}
        {ticksX.map((y) => (
          <text key={y} x={sx(y)} y={H - 12} className="fis-tick" textAnchor="middle">{y}</text>
        ))}
        <line x1={sx(17 / 12)} x2={sx(17 / 12)} y1={sy(ZONE.top)} y2={sy(ZONE.bottom)} className="fis-zone-edge" />
        <path d={d(cmp.sea)} className="fis-sea" />
        <path d={d(cmp.textbook)} className="fis-book" />
        <path key={`hh-${anim}`} d={d(cmp.measured)} className={`fis-hh${motion ? ' fis-draw' : ''}`} pathLength={1} />
        <circle cx={sx(eSea[1])} cy={sy(eSea[2])} r={5} className="fis-dot-sea" />
        <circle cx={sx(eHH[1])} cy={sy(eHH[2])} r={5} className="fis-dot-hh" />
        {/* bracket that states the gap at the plate */}
        <path d={`M${bx},${sy(eSea[2])}h6V${sy(eHH[2])}h-6`} className="fis-bracket" />
        <text x={bx + 12} y={(sy(eSea[2]) + sy(eHH[2])) / 2 + 4} className="fis-gap">
          {fmt(Math.abs(cmp.drop))} in {cmp.drop >= 0 ? 'abajo' : 'arriba'}
        </text>
      </svg>
      <Legend />
    </figure>
  );
}

/** Catcher view: where the three versions cross the front of the plate. */
export function CatcherView({ cmp, anim, motion }: { cmp: Comparison; anim: number; motion: boolean }) {
  const W = 320, H = 300;
  const pts = [cmp.sea, cmp.textbook, cmp.measured];
  const cx = pts.reduce((a, f) => a + f.plateX, 0) / 3;
  const cz = pts.reduce((a, f) => a + f.plateZ, 0) / 3;
  const span = Math.max(2.4, ...pts.map((f) => 2 * Math.max(Math.abs(f.plateX - cx), Math.abs(f.plateZ - cz)) + 1));
  const s = (H - 40) / span;
  // the catcher faces the mound: a right-hander's arm side is the catcher's left
  const px = (x: number) => W / 2 - (x - cx) * s;
  const pz = (z: number) => H / 2 - 10 - (z - cz) * s;
  const r = Math.max(5, BALL_R * s);
  const a = { x: px(cmp.sea.plateX), y: pz(cmp.sea.plateZ) }, b = { x: px(cmp.measured.plateX), y: pz(cmp.measured.plateZ) };
  const lost = Math.hypot(cmp.sea.plateX - cmp.measured.plateX, cmp.sea.plateZ - cmp.measured.plateZ) * 12;
  return (
    <figure className="fis-fig">
      <figcaption>Vista del receptor · cruce por el frente del plato</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Vista del receptor: en el aire elegido la bola cruza a ${fmt(lost)} pulgadas de donde cruza a nivel del mar.`}>
        <rect x={px(PLATE_HALF)} y={pz(ZONE.top)} width={2 * PLATE_HALF * s} height={(ZONE.top - ZONE.bottom) * s} className="fis-zone" />
        <circle cx={a.x} cy={a.y} r={r} className="fis-ball-sea" />
        <circle cx={px(cmp.textbook.plateX)} cy={pz(cmp.textbook.plateZ)} r={r} className="fis-ball-book" />
        <circle key={`b-${anim}`} cx={b.x} cy={b.y} r={r} className={`fis-ball-hh${motion ? ' fis-pop' : ''}`} />
        {lost > 0.2 ? <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="fis-arrow" markerEnd="url(#fis-head)" /> : null}
        <defs>
          <marker id="fis-head" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0,0L8,4L0,8z" className="fis-head-mark" />
          </marker>
        </defs>
        <text x={W / 2} y={H - 8} className="fis-tick" textAnchor="middle">lado del brazo de un diestro a la izquierda</text>
      </svg>
      <p className="fis-fig-note"><strong>{fmt(lost)} in</strong> entre el cruce a nivel del mar y el cruce en el aire elegido.</p>
    </figure>
  );
}

/** Measured elasticity with its 95 % interval per family, against textbook physics (1). */
export function ElasticityChart({ families, selected, onSelect }: {
  families: PhysicsFamily[]; selected: string; onSelect: (family: string) => void;
}) {
  const rows = ORDER.map((f) => families.find((x) => x.pitch_family === f)).filter((x): x is PhysicsFamily => !!x);
  const W = 640, row = 34, T = 14, B = 52, L = 210, R = 64;
  const H = T + rows.length * row + B;
  const hi = Math.max(2, Math.ceil(Math.max(...rows.map((x) => x.elasticity_hi)) * 2) / 2);
  const lo = 0.5;
  const sx = (e: number) => L + ((e - lo) / (hi - lo)) * (W - L - R);
  const ticks = Array.from({ length: Math.round((hi - lo) / 0.5) + 1 }, (_, i) => lo + i * 0.5);
  return (
    <figure className="fis-fig">
      <figcaption>Elasticidad del Magnus contra la densidad, por tipo de lanzamiento (IC 95 %)</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="group" aria-label="Elasticidad medida por tipo de lanzamiento">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={sx(t)} x2={sx(t)} y1={T} y2={H - B} className="fis-grid" />
            <text x={sx(t)} y={H - B + 18} className="fis-tick" textAnchor="middle">{t.toFixed(1)}</text>
          </g>
        ))}
        <line x1={sx(1)} x2={sx(1)} y1={T - 6} y2={H - B} className="fis-ref" />
        <text x={sx(1)} y={H - 4} className="fis-ref-label" textAnchor="middle">1 = física de libro</text>
        {rows.map((f, i) => {
          const y = T + i * row + row / 2;
          const on = f.pitch_family === selected;
          return (
            <g key={f.pitch_family} className={`fis-row${on ? ' is-on' : ''}`} role="button" tabIndex={0}
              aria-pressed={on} aria-label={`${FAMILY_LABEL[f.pitch_family] ?? f.pitch_family}: elasticidad ${fmt(f.elasticity, 2)}, intervalo ${fmt(f.elasticity_lo, 2)} a ${fmt(f.elasticity_hi, 2)}`}
              onClick={() => onSelect(f.pitch_family)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(f.pitch_family); } }}>
              <rect x={0} y={y - row / 2} width={W} height={row} className="fis-row-hit" />
              <text x={L - 14} y={y + 4} textAnchor="end" className="fis-row-label">{FAMILY_LABEL[f.pitch_family] ?? f.pitch_family}</text>
              <line x1={sx(f.elasticity_lo)} x2={sx(f.elasticity_hi)} y1={y} y2={y} className="fis-ci" />
              <circle cx={sx(f.elasticity)} cy={y} r={on ? 6 : 5} className="fis-est" />
              <text x={sx(f.elasticity_hi) + 8} y={y + 4} className="fis-row-value">{fmt(f.elasticity, 2)}</text>
              <title>{`${FAMILY_LABEL[f.pitch_family] ?? f.pitch_family}: ${fmt(f.elasticity, 2)} [${fmt(f.elasticity_lo, 2)}, ${fmt(f.elasticity_hi, 2)}]`}</title>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
