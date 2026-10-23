import { flyPitch, type Family, type Flight, type Vec3 as Track } from '../../../physics/flight';
import type { Vec3 } from '../scene/sceneModel';
import type { Release } from './presets';

export interface Gap {
  xIn: number;
  zIn: number;
  ivb: number;
  hb: number;
}

/** Flight feet (x arm side, y toward the mound, z up) → scene feet (x = catcher's right, y up, z toward the
 *  catcher). A right-hander's arm side is the catcher's left, so his x flips; a lefty's does not. */
export function toScene(point: Track, throws: 'R' | 'L' = 'R'): Vec3 {
  return [throws === 'R' ? -point[0] : point[0], point[2], -point[1]];
}

export function scenePath(flight: Flight, throws: 'R' | 'L' = 'R', step = 4): Vec3[] {
  const points: Vec3[] = [];
  for (let i = 0; i < flight.pos.length; i += step) points.push(toScene(flight.pos[i], throws));
  const last = toScene(flight.pos[flight.pos.length - 1], throws);
  const prev = points[points.length - 1];
  if (!prev || prev[0] !== last[0] || prev[1] !== last[1] || prev[2] !== last[2]) points.push(last);
  return points;
}

export function throwPair(release: Release, rho: number): { sea: Flight; park: Flight } {
  const common = {
    velo: release.velo,
    ivb: release.ivb,
    hb: release.hb,
    release: { height: release.height, side: release.side },
    extension: release.extension,
    family: release.family as Family,
  };
  return {
    sea: flyPitch({ ...common, rho: 1 }),
    park: flyPitch({ ...common, rho }),
  };
}

export function plateGap(sea: Flight, park: Flight): Gap {
  return {
    xIn: (park.plateX - sea.plateX) * 12,
    zIn: (park.plateZ - sea.plateZ) * 12,
    ivb: park.ivb - sea.ivb,
    hb: park.hb - sea.hb,
  };
}

function signed(n: number): string {
  const body = Math.abs(n).toFixed(1);
  return n >= 0 ? `+${body}` : `−${body}`;
}

/** Plate arrival and break lost, in inches, park minus sea level. */
export function lostLabel(gap: Gap): string {
  const side = gap.xIn >= 0 ? 'hacia el brazo' : 'hacia el guante';
  const vert = gap.zIn >= 0 ? 'más alto' : 'más bajo';
  return `En el plato, ${Math.abs(gap.xIn).toFixed(1)} in ${side} y ${Math.abs(gap.zIn).toFixed(1)} in ${vert}. IVB ${signed(gap.ivb)} in, HB ${signed(gap.hb)} in.`;
}
