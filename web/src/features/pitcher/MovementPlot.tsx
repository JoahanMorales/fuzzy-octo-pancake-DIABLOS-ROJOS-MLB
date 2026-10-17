/* Catcher's-view movement chart: each pitch at sea level (grey ring, dashed) and in Harp Helú air (red dot),
   with an arrow for the movement lost. Axes in inches, arm side to the right. */
import { useState } from 'react';
import { fmt } from '../leaderboard/data';
import { familyLabel, type Movement } from './logic';

const SIZE = 360;

/* Explicit colors from tokens.css so the PNG export (html-to-image) keeps them: CSS variables inside SVG are
   not resolved there. */
function token(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}
function palette() {
  return { red: token('--red', '#c8102e'), sea: token('--sea', '#c9ccd3'), bg: token('--bg', '#0c0c0e'),
    line: token('--line', '#2a2a31'), strong: token('--line-strong', '#3a3a43') };
}
const PAD = 36;
const LIM = 25; // inches shown on each side

export function MovementPlot({ moves, compact = false }: { moves: Movement[]; compact?: boolean }) {
  const [hover, setHover] = useState<number | null>(null);
  const span = SIZE - 2 * PAD;
  const sx = (v: number) => PAD + ((Math.max(-LIM, Math.min(LIM, v)) + LIM) / (2 * LIM)) * span;
  const sy = (v: number) => PAD + ((LIM - Math.max(-LIM, Math.min(LIM, v))) / (2 * LIM)) * span;
  const ticks = [-20, -10, 0, 10, 20];
  const h = hover === null ? null : moves[hover];
  const c = palette();
  return (
    <figure className="mv">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role={compact ? undefined : 'img'} aria-hidden={compact || undefined}
        aria-label={compact ? undefined : `Movimiento de ${moves.length} lanzamientos a nivel del mar y en el aire del Harp Helú`}>
        <defs>
          <marker id={compact ? 'mv-arrow-c' : 'mv-arrow'} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="mv-arrowhead" fill={c.red} />
          </marker>
        </defs>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={sx(t)} x2={sx(t)} y1={PAD} y2={SIZE - PAD} className={t === 0 ? 'mv-axis' : 'mv-grid'} stroke={t === 0 ? c.strong : c.line} />
            <line y1={sy(t)} y2={sy(t)} x1={PAD} x2={SIZE - PAD} className={t === 0 ? 'mv-axis' : 'mv-grid'} stroke={t === 0 ? c.strong : c.line} />
            {!compact && <text x={sx(t)} y={SIZE - PAD + 16} className="mv-tick" textAnchor="middle">{t}</text>}
            {!compact && <text x={PAD - 8} y={sy(t) + 4} className="mv-tick" textAnchor="end">{t}</text>}
          </g>
        ))}
        {!compact && (
          <>
            <text x={SIZE - PAD} y={SIZE - 6} className="mv-unit" textAnchor="end">quiebre horizontal, lado del brazo (in)</text>
            <text x={10} y={PAD - 12} className="mv-unit">quiebre vertical inducido (in)</text>
          </>
        )}
        {moves.map((m, i) => (
          <g key={m.pitch.pitch_id} tabIndex={compact ? -1 : 0} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(i)} onBlur={() => setHover(null)} className="mv-pitch"
            aria-label={`${familyLabel(m.pitch.pitch_family)}: ${fmt(m.sea.ivb)} a ${fmt(m.cdmx.ivb)} pulgadas verticales`}>
            <line x1={sx(m.sea.hb)} y1={sy(m.sea.ivb)} x2={sx(m.cdmx.hb)} y2={sy(m.cdmx.ivb)} className="mv-arrow" stroke={c.red} strokeWidth={2}
              markerEnd={`url(#${compact ? 'mv-arrow-c' : 'mv-arrow'})`} />
            <circle cx={sx(m.sea.hb)} cy={sy(m.sea.ivb)} r={compact ? 9 : 6} className="mv-sea" fill={c.bg} stroke={c.sea}
              strokeWidth={2} strokeDasharray="3 2" />
            <circle cx={sx(m.cdmx.hb)} cy={sy(m.cdmx.ivb)} r={compact ? 9 : 6} className="mv-cdmx" fill={c.red} stroke={c.bg}
              strokeWidth={2} />
            {!compact && (
              <text x={sx(m.cdmx.hb) + 10} y={sy(m.cdmx.ivb) + 4} className="mv-label">{familyLabel(m.pitch.pitch_family)}</text>
            )}
            <circle cx={sx(m.cdmx.hb)} cy={sy(m.cdmx.ivb)} r={16} className="mv-hit" fill="transparent" />
          </g>
        ))}
      </svg>
      {!compact && h && (
        <div className="mv-tip" role="status">
          <b>{familyLabel(h.pitch.pitch_family)}</b> · {h.pitch.shape}
          <span>Vertical {fmt(h.sea.ivb)} → {fmt(h.cdmx.ivb)} in ({fmt(h.cdmx.ivb - h.sea.ivb, 1, true)})</span>
          <span>Horizontal {fmt(h.sea.hb)} → {fmt(h.cdmx.hb)} in ({fmt(h.cdmx.hb - h.sea.hb, 1, true)})</span>
        </div>
      )}
      {!compact && (
        <figcaption>
          <span className="lg"><svg width="22" height="10" aria-hidden><circle cx="11" cy="5" r="4" className="mv-sea" /></svg>nivel del mar</span>
          <span className="lg"><svg width="22" height="10" aria-hidden><circle cx="11" cy="5" r="4" className="mv-cdmx" /></svg>aire del Harp Helú</span>
          <span className="lg-note">Movimiento medio traducido con la física de HACK-041 desde la densidad media de la liga.</span>
        </figcaption>
      )}
    </figure>
  );
}
