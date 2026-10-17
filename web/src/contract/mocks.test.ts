import { parseContractFile } from './types';

const REQUIRED = [
  'parks.json',
  'shapes.json',
  'leaderboard.json',
  'staff.json',
  'validation.json',
  'physics.json',
  'models/stuff.json',
  'models/location.json',
  'models/pitching.json',
];

describe('contrato web', () => {
  const modules = import.meta.glob('../../public/data/mock/**/*.json', { eager: true }) as Record<string, { default: unknown }>;
  const parsed = Object.entries(modules).map(([path, mod]) => {
    const relativePath = path.split('/public/data/mock/')[1];
    return { relativePath, data: parseContractFile(relativePath, mod.default) };
  });

  it('parsea cada mock con su esquema', () => {
    expect(parsed.length).toBeGreaterThan(REQUIRED.length);
    for (const name of REQUIRED) {
      expect(parsed.some((file) => file.relativePath === name)).toBe(true);
    }
  });

  it('identifica el arsenal por pitch_id y separa las franquicias 5 y 11', () => {
    const staff = parsed.find((file) => file.relativePath === 'staff.json');
    expect(staff).toBeDefined();
    const franchises = (staff!.data as { franchises: { id: string; pitchers: { pitcher_anon_id: string }[] }[] }).franchises;
    const ids = franchises.map((franchise) => franchise.id).sort();
    expect(ids).toEqual(['11', '5']);
    const seen = new Set<string>();
    for (const franchise of franchises) {
      for (const pitcher of franchise.pitchers) {
        expect(seen.has(pitcher.pitcher_anon_id)).toBe(false);
        seen.add(pitcher.pitcher_anon_id);
      }
    }
    const pitcher = parsed.find((file) => file.relativePath.startsWith('pitcher/'));
    expect(pitcher).toBeDefined();
    const body = pitcher!.data as { seasons: { arsenal_pitches: { pitch_id: number }[] }[] };
    const text = JSON.stringify(body);
    expect(text.includes('AutoPitchType')).toBe(false);
    expect(body.seasons.some((season) => season.arsenal_pitches.some((pitch) => pitch.pitch_id >= 0))).toBe(true);
  });
});
