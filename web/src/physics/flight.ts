/**
 * RK4 pitch flight in the browser: a line-by-line port of `stuffplus/physics/flight.py` (HACK-041).
 *
 * Coordinates (Trackman, feet): x arm side, y from home plate toward the mound, z up. Forces: gravity; drag
 * −½ρA·C_D·|v|v/m; Magnus as an acceleration perpendicular to v, calibrated at sea level so the pitch shows the
 * requested IVB and HB. In air of relative density ρ, drag scales with ρ and Magnus with ρ**elasticity.
 * Breaks are measured as Trackman does: displacement at the front of the plate against the same pitch with no spin.
 *
 * The HACK-041 engine is calibrated on breaks, not on spin rate/axis, so the input is velo + sea-level IVB/HB.
 */
import physics from './physics.json';

export type Vec3 = [number, number, number];

export const G_FT_S2 = 32.174;
export const MPH_TO_FPS = 5280 / 3600;
export const PLATE_FRONT_FT = 17 / 12;
export const MOUND_FT = 60.5;
export const DT = physics.flight.dt;
export const K_SEA = physics.flight.k_sea;

export type Family = keyof typeof physics.flight.cd_sea;
export const FAMILIES = Object.keys(physics.flight.cd_sea) as Family[];

export interface PitchInput {
  velo: number; // release speed, mph
  ivb: number; // induced vertical break at sea level (ρ = 1), inches
  hb: number; // arm-side horizontal break at sea level, inches
  release?: { height: number; side: number }; // feet; side is arm side
  extension?: number; // feet
  target?: { x: number; z: number }; // where the sea-level pitch crosses the plate, feet
  rho?: number; // air density relative to sea level
  family?: Family; // picks C_D and the measured Magnus elasticity from physics.json
  cd?: number; // overrides the family C_D
  elasticity?: number; // overrides the family elasticity (1 = textbook physics)
}

export interface Flight {
  t: number[];
  pos: Vec3[]; // every 1/240 s, plus the interpolated plate crossing
  plateX: number;
  plateZ: number;
  ivb: number;
  hb: number;
  flightTime: number;
  plateMph: number;
}

const norm = (v: Vec3) => Math.hypot(v[0], v[1], v[2]);
const add = (a: Vec3, b: Vec3, s = 1): Vec3 => [a[0] + s * b[0], a[1] + s * b[1], a[2] + s * b[2]];

function integrate(v0: Vec3, r0: Vec3, mag: [number, number], rho: number, cd: number, spin = true) {
  const k = K_SEA * rho * cd;
  const [mx, mz] = spin ? mag : [0, 0];
  const acc = (v: Vec3): Vec3 => {
    const s = norm(v);
    let a: Vec3 = [-k * s * v[0], -k * s * v[1], -k * s * v[2] - G_FT_S2];
    if (spin) {
      // keep the Magnus vector perpendicular to the velocity
      const vh: Vec3 = [v[0] / s, v[1] / s, v[2] / s];
      const d = mx * vh[0] + mz * vh[2];
      a = add(a, [mx - d * vh[0], -d * vh[1], mz - d * vh[2]]);
    }
    return a;
  };

  let r: Vec3 = [...r0];
  let v: Vec3 = [...v0];
  let t = 0;
  const ts = [0];
  const ps: Vec3[] = [[...r]];
  for (let i = 0; i < 2000; i++) {
    const k1v = acc(v), k1r = v;
    const k2v = acc(add(v, k1v, 0.5 * DT)), k2r = add(v, k1v, 0.5 * DT);
    const k3v = acc(add(v, k2v, 0.5 * DT)), k3r = add(v, k2v, 0.5 * DT);
    const k4v = acc(add(v, k3v, DT)), k4r = add(v, k3v, DT);
    const rNew = [0, 1, 2].map((j) => r[j] + (DT / 6) * (k1r[j] + 2 * k2r[j] + 2 * k3r[j] + k4r[j])) as Vec3;
    const vNew = [0, 1, 2].map((j) => v[j] + (DT / 6) * (k1v[j] + 2 * k2v[j] + 2 * k3v[j] + k4v[j])) as Vec3;
    if (rNew[1] <= PLATE_FRONT_FT) {
      // interpolate the crossing
      const f = (r[1] - PLATE_FRONT_FT) / (r[1] - rNew[1]);
      const rEnd = add(r, add(rNew, r, -1), f);
      const vEnd = add(v, add(vNew, v, -1), f);
      ts.push(t + f * DT);
      ps.push(rEnd);
      return { ts, ps, vEnd };
    }
    r = rNew;
    v = vNew;
    t += DT;
    ts.push(t);
    ps.push([...r]);
  }
  throw new Error('the pitch never reached the plate');
}

function launch(velo: number, height: number, side: number, extension: number, yaw: number, pitch: number) {
  const speed = velo * MPH_TO_FPS;
  const v0: Vec3 = [
    speed * Math.sin(yaw) * Math.cos(pitch),
    -speed * Math.cos(yaw) * Math.cos(pitch),
    speed * Math.sin(pitch),
  ];
  const r0: Vec3 = [side, MOUND_FT - extension, height];
  return { v0, r0 };
}

/** Calibrate Magnus and the launch angles at sea level, then throw the same release in air `rho`. */
export function flyPitch(p: PitchInput): Flight {
  const { height, side } = p.release ?? { height: 6.0, side: 1.8 };
  const extension = p.extension ?? 6.3;
  const target = p.target ?? { x: 0, z: 2.6 };
  const rho = p.rho ?? 1;
  const cd = p.cd ?? (p.family ? physics.flight.cd_sea[p.family] : 0.29);
  const elasticity = p.elasticity ?? (p.family ? physics.flight.magnus_elasticity[p.family] : 1);

  let yaw = 0, pitch = -0.03;
  let mag: [number, number] = [0, 0];
  for (let i = 0; i < 6; i++) {
    // alternate: Magnus size from the requested breaks, launch angles from the target
    const { v0, r0 } = launch(p.velo, height, side, extension, yaw, pitch);
    const spun = integrate(v0, r0, mag, 1, cd);
    const plain = integrate(v0, r0, [0, 0], 1, cd, false);
    const T = spun.ts[spun.ts.length - 1];
    const end = spun.ps[spun.ps.length - 1];
    const endNos = plain.ps[plain.ps.length - 1];
    mag = [
      mag[0] + (2 * (p.hb / 12 - (end[0] - endNos[0]))) / T ** 2,
      mag[1] + (2 * (p.ivb / 12 - (end[2] - endNos[2]))) / T ** 2,
    ];
    const dist = r0[1] - PLATE_FRONT_FT;
    yaw += (target.x - end[0]) / dist;
    pitch += (target.z - end[2]) / dist;
  }
  const { v0, r0 } = launch(p.velo, height, side, extension, yaw, pitch);
  const scale = rho ** elasticity;
  const spun = integrate(v0, r0, [mag[0] * scale, mag[1] * scale], rho, cd);
  const plain = integrate(v0, r0, [0, 0], rho, cd, false);
  const end = spun.ps[spun.ps.length - 1];
  const endNos = plain.ps[plain.ps.length - 1];
  return {
    t: spun.ts,
    pos: spun.ps,
    plateX: end[0],
    plateZ: end[2],
    ivb: (end[2] - endNos[2]) * 12,
    hb: (end[0] - endNos[0]) * 12,
    flightTime: spun.ts[spun.ts.length - 1],
    plateMph: norm(spun.vEnd) / MPH_TO_FPS,
  };
}
