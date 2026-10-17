import { describe, expect, it } from 'vitest';
import fixture from './parity.fixture.json';
import { fly, positionAt, type Release } from './flight';

// Parity with stuffplus/physics/flight.py: the fixture is fly() run in Python on synthetic releases.
describe('flight.ts matches flight.py', () => {
  for (const c of fixture.cases) {
    it(`${c.family} rho=${c.rho} elasticity=${c.elasticity.toFixed(2)}`, () => {
      const f = fly(c.release as Release, c.rho, c.elasticity);
      expect(f.t.length).toBe(c.n);
      for (const k of ['plate_x', 'plate_z', 'flight_time'] as const) expect(Math.abs(f[k] - c[k])).toBeLessThan(1e-7);
      for (const k of ['ivb_in', 'hb_in', 'plate_mph'] as const) expect(Math.abs(f[k] - c[k])).toBeLessThan(1e-6);
      const mid = f.pos[Math.floor(c.n / 2)];
      mid.forEach((v, i) => expect(Math.abs(v - c.mid[i])).toBeLessThan(1e-7));
    });
  }

  it('positionAt clamps to release and plate', () => {
    const f = fly(fixture.cases[0].release as Release, 1, 1);
    expect(positionAt(f, -1)).toEqual(f.pos[0]);
    expect(positionAt(f, 9)).toEqual(f.pos[f.pos.length - 1]);
  });
});
