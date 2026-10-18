import { ZONE, insideBand, pointAt, skylineProfile, type Hand, type ParkSide, type Vec3 } from './sceneModel';

const W = 360;
const H = 300;
const X0 = -2.5;
const X1 = 2.5;
const Y0 = 0.15;
const Y1 = 7.2;
const px = (x: number) => ((x - X0) / (X1 - X0)) * W;
const py = (y: number) => H - ((y - Y0) / (Y1 - Y0)) * H;

function poly(path: Vec3[]): string {
  return path.map((p) => `${px(p[0]).toFixed(1)},${py(p[1]).toFixed(1)}`).join(' ');
}

export default function Fallback2D({
  hand,
  park,
  harpPath,
  seaPath,
  label,
}: {
  hand: Hand;
  park: ParkSide;
  harpPath: Vec3[];
  seaPath: Vec3[];
  label: string;
}) {
  const band = insideBand(hand);
  const sky = skylineProfile(park);
  const endH = pointAt(harpPath, 1);
  const endS = pointAt(seaPath, 1);
  const zoneW = px(ZONE.half) - px(-ZONE.half);
  const zoneH = py(ZONE.bottom) - py(ZONE.top);
  const bandX = px(band.x - band.width / 2);
  const bandW = px(band.x + band.width / 2) - bandX;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} data-sky={park} data-side={hand}>
      {sky.ridges ? (
        <polygon points="0,86 28,48 78,70 132,22 196,58 248,30 310,62 360,44 360,96 0,96" className="fb-ridge" />
      ) : (
        <line x1={0} y1={78} x2={W} y2={78} className="fb-flat" />
      )}
      <rect className="fb-zone" x={px(-ZONE.half)} y={py(ZONE.top)} width={zoneW} height={zoneH} />
      <rect className="fb-in" x={bandX} y={py(band.y + band.height / 2)} width={bandW} height={py(band.y - band.height / 2) - py(band.y + band.height / 2)} />
      <polygon className="fb-plate" points={`${px(0)},${py(0.2)} ${px(-0.35)},${py(0.55)} ${px(0)},${py(0.9)} ${px(0.35)},${py(0.55)}`} />
      <circle className="fb-batter" cx={px(hand === 'R' ? -1.7 : 1.7)} cy={py(1)} r={8} />
      <polyline className="fb-sea" points={poly(seaPath)} />
      <polyline className="fb-harp" points={poly(harpPath)} />
      <circle className="fb-ghost" cx={px(endS[0])} cy={py(endS[1])} r={6} />
      <circle className="fb-ball" cx={px(endH[0])} cy={py(endH[1])} r={6} />
    </svg>
  );
}
