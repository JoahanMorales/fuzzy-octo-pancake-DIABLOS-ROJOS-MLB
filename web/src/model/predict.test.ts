import { describe, expect, it } from 'vitest';
import { encode, locationValue, predict, toPlus, type CompositeModel, type FeatureRow } from './predict';
import synthetic from './fixtures/stuff_synthetic.json';
import syntheticPacked from './fixtures/stuff_synthetic_packed.json';
import syntheticGolden from './fixtures/stuff_synthetic_golden.json';
import realGolden from './fixtures/stuff_real_golden.json';
import stuff from '../../public/data/models/stuff.json';
import location from '../../public/data/models/location.json';
import locationGolden from './fixtures/location_real_golden.json';

interface Golden {
  rows: FeatureRow[];
  probs: number[][];
  contact: number[];
  xrv: number[];
}

function expectParity(model: CompositeModel, g: Golden) {
  g.rows.forEach((row, i) => {
    const p = predict(model, row);
    p.probs.forEach((v, c) => expect(Math.abs(v - g.probs[i][c])).toBeLessThan(1e-6));
    expect(Math.abs(p.contact - g.contact[i])).toBeLessThan(1e-6);
    expect(Math.abs(p.xrv - g.xrv[i])).toBeLessThan(1e-6);
  });
}

describe('predict.ts parity with LightGBM', () => {
  it('synthetic fixture model: conftest rows + random vectors (NaNs, every category, an unseen one)', () => {
    expect(syntheticGolden.rows.length).toBeGreaterThanOrEqual(100);
    expectParity(synthetic as CompositeModel, syntheticGolden as Golden);
  });

  it('packed layout of the same synthetic model gives the same predictions', () => {
    expect((syntheticPacked as CompositeModel).outcome.trees[0].packed).toBeDefined();
    expectParity(syntheticPacked as CompositeModel, syntheticGolden as Golden);
  });

  it('exported paper Stuff+ composite on random vectors in observed ranges', () => {
    const g = realGolden as Golden;
    expect(g.rows.some((r) => Object.values(r).some((v) => v === null))).toBe(true);
    expectParity(stuff as CompositeModel, g);
  });

  it('exported Location+ composite and its count × family reference', () => {
    const g = locationGolden as Golden & { loc_value: (number | null)[] };
    const model = location as CompositeModel;
    expectParity(model, g);
    g.rows.forEach((row, i) => {
      if (row.Balls === null || row.Strikes === null || g.loc_value[i] === null) return;
      expect(Math.abs(locationValue(model, row) - (g.loc_value[i] as number))).toBeLessThan(1e-6);
    });
  });
});

describe('encoding and Plus scale', () => {
  const model = stuff as CompositeModel;

  it('maps categories by the booster code order and sends unseen ones to NaN', () => {
    const fam = model.features.indexOf('pitch_family');
    const levels = model.categories.pitch_family;
    expect(levels[0]).toBe('Four-Seam');
    expect(encode(model, { pitch_family: levels[2] })[fam]).toBe(2);
    expect(encode(model, { pitch_family: 'Knuckle-Curve' })[fam]).toBeNaN();
  });

  it('Plus = 100 + 10·z with lower xRV = better (park-neutral reference)', () => {
    const g = model.plus.stats!.__all__;
    expect(toPlus(model, g.mean)).toBeCloseTo(100, 9);
    expect(toPlus(model, g.mean - g.sd)).toBeCloseTo(110, 9);
    expect(model.plus.reference).toBe('park-neutral');
    const loc = location as CompositeModel;
    expect(toPlus(loc, loc.plus.stats!.__all__.mean)).toBeCloseTo(100, 9); // Location+ scales locationValue
  });
});
