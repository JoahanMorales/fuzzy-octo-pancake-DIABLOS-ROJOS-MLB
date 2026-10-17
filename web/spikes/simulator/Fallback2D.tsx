/* No WebGL: the catcher's view in SVG with the same flights (web/DESIGN.md). */
import { fmt, toWorld, type Hand, type Throw } from './model';

const W = 280, H = 340;
const X0 = -1.7, X1 = 1.7, Z0 = 0.6, Z1 = 4.4;
const sx = (x: number) => ((x - X0) / (X1 - X0)) * W;
const sz = (z: number) => H - ((z - Z0) / (Z1 - Z0)) * H;
const HALF = 17 / 24;

export default function Fallback2D({ thrown, hand }: { thrown: Throw; hand: Hand }) {
  const end = (p: { plate_x: number; plate_z: number }) => toWorld([p.plate_x, 0, p.plate_z], hand);
  const [sxw, szw] = end(thrown.sea);
  const [hxw, hzw] = end(thrown.hh);
  const r = (2.9 / 24 / (X1 - X0)) * W;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img"
      aria-label={`Vista del catcher: el lanzamiento cruza ${fmt(thrown.plateGapIn)} pulgadas lejos de donde cruzaría a nivel del mar`}>
      <rect x={sx(-HALF)} y={sz(3.5)} width={sx(HALF) - sx(-HALF)} height={sz(1.5) - sz(3.5)} className="fb-zone" />
      <line x1={sx(sxw)} y1={sz(szw)} x2={sx(hxw)} y2={sz(hzw)} className="fb-gap" />
      <circle cx={sx(sxw)} cy={sz(szw)} r={r} className="fb-sea" />
      <circle cx={sx(hxw)} cy={sz(hzw)} r={r} className="fb-hh" />
      <text x={sx(Math.max(sxw, hxw)) + r + 6} y={(sz(szw) + sz(hzw)) / 2 + 4} className="fb-label">
        {fmt(thrown.plateGapIn)} in
      </text>
    </svg>
  );
}
