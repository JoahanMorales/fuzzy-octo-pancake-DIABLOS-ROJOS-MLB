import { describe, expect, it } from 'vitest';
import { DT, FAMILIES, flyPitch } from './flight';
import golden from './golden.json';

const IN = 1 / 12;

describe('flyPitch parity with stuffplus/physics/flight.py (50 synthetic releases)', () => {
  it.each(golden.cases.map((c, i) => [i, c] as const))('case %i', (_, c) => {
    const f = flyPitch({
      velo: c.velo,
      ivb: c.ivb,
      hb: c.hb,
      release: { height: c.height, side: c.side },
      extension: c.extension,
      target: { x: c.target_x, z: c.target_z },
      cd: c.cd,
      rho: c.rho,
      elasticity: c.elasticity,
    });
    expect(Math.abs(f.plateX - c.out.plate_x)).toBeLessThan(0.1 * IN);
    expect(Math.abs(f.plateZ - c.out.plate_z)).toBeLessThan(0.1 * IN);
    expect(Math.abs(f.ivb - c.out.ivb)).toBeLessThan(0.2);
    expect(Math.abs(f.hb - c.out.hb)).toBeLessThan(0.2);
    expect(f.flightTime).toBeCloseTo(c.out.flight_time, 4);
    expect(f.plateMph).toBeCloseTo(c.out.plate_mph, 3);
    expect(f.t.length).toBe(c.out.n);
  });
});

describe('flyPitch behaviour', () => {
  it('samples every 1/240 s and ends at the front of the plate', () => {
    const f = flyPitch({ velo: 94, ivb: 17, hb: 8, family: 'Four-Seam' });
    expect(f.t.length).toBe(f.pos.length);
    expect(f.t[1] - f.t[0]).toBeCloseTo(DT, 12);
    expect(DT).toBeCloseTo(1 / 240, 12);
    expect(f.pos[f.pos.length - 1][1]).toBeCloseTo(17 / 12, 9);
    expect(f.ivb).toBeCloseTo(17, 1);
    expect(f.hb).toBeCloseTo(8, 1);
  });

  it('reproduces the HACK-041 four-seam ΔIVB (No → Extreme bucket ρ̂, measured elasticity) within 0.3 in', () => {
    const c = golden.flight_check;
    const throwAt = (rho: number) =>
      flyPitch({ velo: c.velo, ivb: c.ivb, hb: c.hb, cd: c.cd, elasticity: c.elasticity, rho });
    const delta = throwAt(c.rho_ext).ivb - throwAt(c.rho_no).ivb;
    expect(Math.abs(delta - c.reported_delta_ivb)).toBeLessThan(0.3);
    expect(Math.abs(delta - c.observed_delta_ivb)).toBeLessThan(0.3);
  });

  it('thin air (ρ 1.0 → 0.819) loses ride and arrives faster for every family', () => {
    for (const family of FAMILIES) {
      const sea = flyPitch({ velo: 90, ivb: 14, hb: 8, family, rho: 1 });
      const hh = flyPitch({ velo: 90, ivb: 14, hb: 8, family, rho: 0.819 });
      expect(hh.ivb).toBeLessThan(sea.ivb);
      expect(hh.plateMph).toBeGreaterThan(sea.plateMph);
    }
  });
});
