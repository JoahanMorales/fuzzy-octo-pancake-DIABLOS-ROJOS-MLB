import { describe, expect, it } from 'vitest';
import { countKey, encode, fillPitchingRow, locationValue, outsideZone, pitchingXrv, predict, stuffValue, toPlus, type CompositeModel, type FeatureRow, type PitchingModel } from './predict';
import synthetic from './fixtures/stuff_synthetic.json';
import syntheticPacked from './fixtures/stuff_synthetic_packed.json';
import syntheticGolden from './fixtures/stuff_synthetic_golden.json';
import v2Synthetic from './fixtures/stuff_v2_synthetic.json';
import v2Golden from './fixtures/stuff_v2_synthetic_golden.json';
import realGolden from './fixtures/stuff_real_golden.json';
import stuff from '../../public/data/models/stuff.json';
import location from '../../public/data/models/location.json';
import locationGolden from './fixtures/location_real_golden.json';
import pitchingSynthetic from './fixtures/pitching_synthetic.json';
import pitchingGolden from './fixtures/pitching_synthetic_golden.json';

interface Golden {
  rows: FeatureRow[];
  probs: number[][];
  contact: number[];
  xrv: number[];
  xrv_at_count?: number[];
}

function expectParity(model: CompositeModel, g: Golden) {
  g.rows.forEach((row, i) => {
    const p = predict(model, row);
    p.probs.forEach((v, c) => expect(Math.abs(v - g.probs[i][c])).toBeLessThan(1e-6));
    expect(Math.abs(p.contact - g.contact[i])).toBeLessThan(1e-6);
    expect(Math.abs(p.xrv - g.xrv[i])).toBeLessThan(1e-6);
    if (g.xrv_at_count) expect(Math.abs(p.xrvAtCount - g.xrv_at_count[i])).toBeLessThan(1e-6);
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

describe('production Stuff+ v2 (HACK-066): temperature and count-neutral value', () => {
  const model = v2Synthetic as unknown as CompositeModel;

  it('matches CountNeutral (probabilities and contact at the row count, xRV at count, count-neutral xRV)', () => {
    expect(model.calibration?.method).toBe('temperature');
    expect(model.count?.value).toBe('count_neutral');
    expect(model.count?.counts).toHaveLength(12);
    expectParity(model, v2Golden as Golden);
  });

  it('the pitch count changes the components but never the count-neutral value', () => {
    const row = { ...(v2Golden as Golden).rows[0], Balls: 0, Strikes: 2 };
    const a = predict(model, row);
    const b = predict(model, { ...row, Balls: 3, Strikes: 0 });
    expect(a.xrvAtCount).not.toBeCloseTo(b.xrvAtCount, 6);
    expect(a.xrv).toBeCloseTo(b.xrv, 12);
    expect(stuffValue(model, { ...row, Balls: null, Strikes: null })).toBeCloseTo(a.xrv, 12);
  });

  it('clips the count only for the table key and falls back to league weights for an unseen family', () => {
    expect(countKey(5, 4)).toBe('3-2');
    expect(countKey(null, 1)).toBeNull();
    const row = { ...(v2Golden as Golden).rows[0], pitch_family: 'Knuckle-Curve' };
    expect(Number.isFinite(stuffValue(model, row))).toBe(true);
  });
});

describe('Pitching+ (HACK-079): components, target boosters and combination', () => {
  const model = pitchingSynthetic as unknown as PitchingModel;

  it('matches PitchingExport.predict_xrv on conftest rows + random vectors', () => {
    expect(pitchingGolden.rows.length).toBeGreaterThanOrEqual(100);
    pitchingGolden.rows.forEach((row, i) => {
      expect(Math.abs(pitchingXrv(model, row as FeatureRow) - pitchingGolden.xrv[i])).toBeLessThan(1e-6);
    });
  });

  it('fills the batter with the league average and the context the panel lacks with family medians', () => {
    const fam = Object.keys(model.neutral.by_family)[0];
    const row = fillPitchingRow(model, { pitch_family: fam, Balls: 1, batter_rv: 0.5, Outs: 2 });
    expect(row.batter_rv).toBe(model.neutral.batter.batter_rv);
    expect(row.Outs).toBe(2);
    expect(row.arsenal_size).toBe(model.neutral.by_family[fam].arsenal_size ?? model.neutral.league.arsenal_size);
    expect(fillPitchingRow(model, { pitch_family: 'Knuckle-Curve' }).tunnel_ratio).toBe(model.neutral.league.tunnel_ratio);
  });

  it('the zone box decides chase: middle in, far outside out, no location = 0', () => {
    const mid = (model.zone.z_low + model.zone.z_high) / 2;
    expect(outsideZone(model, { plate_x_arm: 0, PlateLocHeight: mid })).toBe(0);
    expect(outsideZone(model, { plate_x_arm: -(model.zone.x + 0.1), PlateLocHeight: mid })).toBe(1);
    expect(outsideZone(model, { plate_x_arm: null, PlateLocHeight: mid })).toBe(0);
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
