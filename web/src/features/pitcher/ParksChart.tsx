/* Stuff+ of one pitcher-season at each of the 20 parks, ordered by air density. Reference lines: sea level
   (grey, dashed) and Harp Helú air (red). Values are linear in ρ between the two scored flavours. */
import { fmt } from '../leaderboard/data';
import { parkCurve, RHO_HH, type Park, type Season } from './logic';

const W = 520;
const ROW = 18;
const LEFT = 92;
const RIGHT = 56;

export function ParksChart({ season, parks }: { season: Season; parks: Park[] }) {
  const curve = parkCurve(season, parks);
  const vals = [...curve.map((c) => c.stuff), season.stuff_plus, season.stuff_plus_harp_helu];
  const lo = Math.floor(Math.min(...vals) - 2);
  const hi = Math.ceil(Math.max(...vals) + 2);
  const H = curve.length * ROW + 34;
  const sx = (v: number) => LEFT + ((v - lo) / (hi - lo)) * (W - LEFT - RIGHT);
  return (
    <figure className="parks">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Stuff+ en los ${curve.length} parques, de ${fmt(curve[0]?.stuff ?? 0)} a ${fmt(curve[curve.length - 1]?.stuff ?? 0)}`}>
        <line x1={sx(season.stuff_plus)} x2={sx(season.stuff_plus)} y1={8} y2={H - 22} className="pk-sea" />
        <line x1={sx(season.stuff_plus_harp_helu)} x2={sx(season.stuff_plus_harp_helu)} y1={8} y2={H - 22} className="pk-hh" />
        <text x={sx(season.stuff_plus)} y={H - 6} textAnchor="middle" className="pk-ref">nivel del mar</text>
        <text x={sx(season.stuff_plus_harp_helu)} y={H - 6} textAnchor="middle" className="pk-ref pk-ref-hh">Harp Helú</text>
        {curve.map((c, i) => {
          const y = 14 + i * ROW;
          return (
            <g key={c.park.id}>
              <title>{`Parque ${c.park.id} · ρ ${c.park.rho.toFixed(3)} · Stuff+ ${fmt(c.stuff)}`}</title>
              <text x={8} y={y + 4} className="pk-name">P{c.park.id}</text>
              <text x={LEFT - 8} y={y + 4} className="pk-rho" textAnchor="end">ρ {c.park.rho.toFixed(3)}</text>
              <line x1={LEFT} x2={W - RIGHT} y1={y} y2={y} className="pk-row" />
              <circle cx={sx(c.stuff)} cy={y} r={5} className={`pk-dot ${c.park.rho <= RHO_HH + 0.02 ? 'is-thin' : ''}`} />
              <text x={W - 8} y={y + 4} textAnchor="end" className="pk-val">{fmt(c.stuff)}</text>
            </g>
          );
        })}
      </svg>
      <figcaption>
        Parques identificados por densidad (ρ relativa al nivel del mar), no por nombre. Entre el Stuff+ neutral y el
        de CDMX, cada parque se interpola en línea recta según su ρ.
      </figcaption>
    </figure>
  );
}
