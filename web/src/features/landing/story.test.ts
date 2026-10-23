import { describe, expect, it } from 'vitest';
import validationJson from '../../../public/data/mock/validation.json';
import { parseContractFile } from '../../contract/types';
import { biasReduction, heroNumbers, percentFromFraction, signed } from './story';
import type { ValidationFile } from './load';

const validation = parseContractFile('validation.json', validationJson) as ValidationFile;

describe('hero numbers come from validation.json', () => {
  it('uses the league delta, Pitching+ skill and park-holdout bias', () => {
    const hero = heroNumbers(validation);
    expect(hero.leagueDelta).toBe(validation.highlights.league_delta_cdmx);
    expect(hero.pitchingSplit).toBe('season_holdout');
    const skill = validation.rows.find((row) => (
      row.split === 'season_holdout' && row.model === 'Pitching+' && row.metric === 'skill_vs_baseline'
    ));
    expect(hero.pitchingSkill).toBe(skill?.value);
    const base = validation.rows.find((row) => row.split === 'park_holdout' && row.model === 'baseline' && row.metric === 'bias');
    const model = validation.rows.find((row) => row.split === 'park_holdout' && row.model === 'Pitching+' && row.metric === 'bias');
    expect(hero.biasReduction).toBeCloseTo(biasReduction(base!.value, model!.value));
    expect(signed(hero.leagueDelta)).toBe('−13.0');
    expect(percentFromFraction(hero.pitchingSkill)).toBe('+3.7 %');
    expect(percentFromFraction(-hero.biasReduction)).toBe('−81.5 %');
  });

  it('measures how much the bias shrank', () => {
    expect(biasReduction(0.01088, 0.00201)).toBeCloseTo(0.815257, 4);
    expect(biasReduction(0, 0.1)).toBe(0);
  });
});
