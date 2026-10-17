import { describe, expect, it } from 'vitest';
import type { CompositeModel } from '../../model/predict';
import stuff from '../../../public/data/models/stuff.json';
import golden from './golden.json';
import { features, parseArsenal, parseCsv, profileArsenal, ProfileError, RHO_HARP_HELU } from './profile';

const model = stuff as CompositeModel;

describe('prospect profiler parity with the Python pipeline', () => {
  it('uses the paper model and the Harp Helú density from physics.json', () => {
    expect(golden.model_version).toBe((stuff as { model_version: string }).model_version);
    expect(RHO_HARP_HELU).toBe(golden.rho_hh);
  });

  it.each(golden.cases.map((c) => [c.name, c] as const))('%s: features and Stuff+ within 1e-6', (_, c) => {
    const p = profileArsenal(c.csv, model);
    expect(p.pitches.map((x) => x.pitch.pitch_type)).toEqual(c.pitches.map((x) => x.pitch_type));
    p.pitches.forEach((x, i) => {
      const g = c.pitches[i];
      expect(Math.abs(x.usage - g.usage)).toBeLessThan(1e-12);
      for (const [k, v] of Object.entries(g.features)) {
        const mine = x.features[k] as number;
        if (v === null) expect(mine).toBeNaN();
        else expect(Math.abs(mine - (v as number))).toBeLessThan(1e-9);
      }
      expect(Math.abs(x.stuffNeutral - g.stuff_neutral)).toBeLessThan(1e-6);
      expect(Math.abs(x.stuffCdmx - g.stuff_cdmx)).toBeLessThan(1e-6);
    });
    expect(Math.abs(p.arsenalNeutral - c.arsenal_neutral)).toBeLessThan(1e-6);
    expect(Math.abs(p.arsenalCdmx - c.arsenal_cdmx)).toBeLessThan(1e-6);
  });
});

describe('parsing', () => {
  it('reads friendly release columns and puts the default release on the arm side for lefties', () => {
    const csv = 'pitch_type,throws,velo,spin_rate,spin_axis,ivb,hb,rel_height\nFour-Seam,Left,92,2300,150,16,-8,6.3\nSlider,Left,84,2500,250,1,5,6.3\n';
    const f = features(parseArsenal(csv));
    expect(f[0].RelHeight).toBe(6.3);
    expect(f[0].rel_side_arm).toBe(1.8);
    expect(f[0].hb_arm).toBe(8);
    expect(f[1].hb_diff_fb).toBe(-5 - 8);
  });

  it('rejects bad input with a Spanish message', () => {
    expect(() => parseArsenal('pitch_type,throws\n')).toThrow(ProfileError);
    expect(() => parseArsenal('pitch_type,throws,velo,spin_rate,spin_axis,ivb,hb\nFour-Seam,Right,94,2300,210,17,9\n')).toThrow(/entre 2 y 5/);
    expect(() => parseArsenal('pitch_type,throws,velo,spin_rate,spin_axis,ivb,hb\nGyro,Right,94,2300,210,17,9\nSlider,Right,85,2500,95,1,-6\n')).toThrow(/no reconocido/);
    expect(() => parseArsenal('pitch_type,throws,velo,spin_rate,spin_axis,ivb,hb\nFour-Seam,Right,140,2300,210,17,9\nSlider,Right,85,2500,95,1,-6\n')).toThrow(/fuera de/);
  });

  it('handles quoted cells and CRLF', () => {
    expect(parseCsv('a,"b, c"\r\n1,"say ""hi"""\r\n')).toEqual([{ a: '1', 'b, c': 'say "hi"' }]);
  });
});
