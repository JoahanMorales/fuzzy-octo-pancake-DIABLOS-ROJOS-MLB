/* RK4 pitch flight, an exact port of stuffplus/physics/flight.py (HACK-041). Parity: flight.test.ts.

   Coordinates (feet): x toward the pitcher's ARM SIDE (already normalized by hand, not catcher-right), y from home
   plate toward the mound, z up. Forces: gravity; drag -k|v|v with k = K_SEA*rho*cd; Magnus as an acceleration
   perpendicular to v, calibrated so the pitch shows the requested IVB/HB at sea level and scaled by rho**elasticity
   in other air. Breaks are measured like Trackman: displacement at the front of the plate against the same pitch
   thrown with no spin. */

export type Vec3 = [number, number, number];

const G_FT_S2 = 32.174;
const FT_TO_M = 0.3048;
const MPH_TO_FPS = 5280 / 3600;
const BALL_MASS_KG = 0.145;
const BALL_RADIUS_M = (9.125 * 0.0254) / (2 * Math.PI);
const BALL_AREA_M2 = Math.PI * BALL_RADIUS_M ** 2;
const RHO_SI_SEA_LEVEL = 1.225;

export const PLATE_FRONT_FT = 17 / 12;
export const MOUND_FT = 60.5;
export const DT = 1 / 240;
export const K_SEA = ((0.5 * RHO_SI_SEA_LEVEL * BALL_AREA_M2) / BALL_MASS_KG) * FT_TO_M;

export interface Release {
  velo_mph: number;
  ivb_in: number; // at sea level (rho = 1)
  hb_in: number; // arm side, at sea level
  rel_height_ft: number;
  rel_side_ft: number; // arm side
  extension_ft: number;
  target_z_ft: number; // where the sea-level pitch crosses the plate
  target_x_ft: number; // arm side
  cd: number;
}

export const DEFAULT_RELEASE: Release = {
  velo_mph: 94,
  ivb_in: 17,
  hb_in: 8,
  rel_height_ft: 6,
  rel_side_ft: 1.8,
  extension_ft: 6.3,
  target_z_ft: 2.6,
  target_x_ft: 0,
  cd: 0.29,
};

export interface Flight {
  t: number[];
  pos: Vec3[];
  plate_x: number;
  plate_z: number;
  ivb_in: number;
  hb_in: number;
  flight_time: number;
  plate_mph: number;
}

const add = (a: Vec3, b: Vec3): Vec3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const scale = (a: Vec3, s: number): Vec3 => [a[0] * s, a[1] * s, a[2] * s];
const norm = (a: Vec3) => Math.hypot(a[0], a[1], a[2]);

function integrate(v0: Vec3, r0: Vec3, mag: [number, number], rho: number, cd: number, spin = true) {
  const k = K_SEA * rho * cd;
  const [mx, mz] = spin ? mag : [0, 0];
  const acc = (v: Vec3): Vec3 => {
    const s = norm(v);
    let a: Vec3 = scale(v, -k * s);
    a[2] -= G_FT_S2;
    if (spin) {
      const vh = scale(v, 1 / s);
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
    const k2v = acc(add(v, scale(k1v, 0.5 * DT))), k2r = add(v, scale(k1v, 0.5 * DT));
    const k3v = acc(add(v, scale(k2v, 0.5 * DT))), k3r = add(v, scale(k2v, 0.5 * DT));
    const k4v = acc(add(v, scale(k3v, DT))), k4r = add(v, scale(k3v, DT));
    const rNew = add(r, scale(add(add(k1r, scale(k2r, 2)), add(scale(k3r, 2), k4r)), DT / 6));
    const vNew = add(v, scale(add(add(k1v, scale(k2v, 2)), add(scale(k3v, 2), k4v)), DT / 6));
    if (rNew[1] <= PLATE_FRONT_FT) {
      const f = (r[1] - PLATE_FRONT_FT) / (r[1] - rNew[1]);
      const rEnd = add(r, scale(add(rNew, scale(r, -1)), f));
      const vEnd = add(v, scale(add(vNew, scale(v, -1)), f));
      t += f * DT;
      ts.push(t);
      ps.push(rEnd);
      return { t: ts, pos: ps, vEnd };
    }
    r = rNew;
    v = vNew;
    t += DT;
    ts.push(t);
    ps.push([...r]);
  }
  throw new Error('the pitch never reached the plate');
}

function launch(rel: Release, yaw: number, pitch: number): { v0: Vec3; r0: Vec3 } {
  const speed = rel.velo_mph * MPH_TO_FPS;
  return {
    v0: [speed * Math.sin(yaw) * Math.cos(pitch), -speed * Math.cos(yaw) * Math.cos(pitch), speed * Math.sin(pitch)],
    r0: [rel.rel_side_ft, MOUND_FT - rel.extension_ft, rel.rel_height_ft],
  };
}

/** Calibrate Magnus and the launch angles at sea level, then throw the same release in air `rho`. */
export function fly(rel: Release, rho = 1, elasticity = 1): Flight {
  let yaw = 0, pitch = -0.03;
  let mag: [number, number] = [0, 0];
  for (let i = 0; i < 6; i++) {
    const { v0, r0 } = launch(rel, yaw, pitch);
    const s = integrate(v0, r0, mag, 1, rel.cd);
    const n = integrate(v0, r0, [0, 0], 1, rel.cd, false);
    const T = s.t[s.t.length - 1];
    const ps = s.pos[s.pos.length - 1], pn = n.pos[n.pos.length - 1];
    mag = [mag[0] + (2 * (rel.hb_in / 12 - (ps[0] - pn[0]))) / T ** 2, mag[1] + (2 * (rel.ivb_in / 12 - (ps[2] - pn[2]))) / T ** 2];
    const dist = r0[1] - PLATE_FRONT_FT;
    yaw += (rel.target_x_ft - ps[0]) / dist;
    pitch += (rel.target_z_ft - ps[2]) / dist;
  }
  const { v0, r0 } = launch(rel, yaw, pitch);
  const sc = rho ** elasticity;
  const s = integrate(v0, r0, [mag[0] * sc, mag[1] * sc], rho, rel.cd);
  const n = integrate(v0, r0, [0, 0], rho, rel.cd, false);
  const end = s.pos[s.pos.length - 1], endN = n.pos[n.pos.length - 1];
  return {
    t: s.t,
    pos: s.pos,
    plate_x: end[0],
    plate_z: end[2],
    ivb_in: (end[2] - endN[2]) * 12,
    hb_in: (end[0] - endN[0]) * 12,
    flight_time: s.t[s.t.length - 1],
    plate_mph: norm(s.vEnd) / MPH_TO_FPS,
  };
}

/** Position at time `t` along a flight (linear between RK4 steps; clamps to the ends). */
export function positionAt(f: Flight, t: number): Vec3 {
  const { t: ts, pos } = f;
  if (t <= 0) return pos[0];
  if (t >= ts[ts.length - 1]) return pos[pos.length - 1];
  const i = Math.min(Math.floor(t / DT), ts.length - 2);
  const u = (t - ts[i]) / (ts[i + 1] - ts[i]);
  const a = pos[i], b = pos[i + 1];
  return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u];
}
