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

describe('modelos exportados (HACK-066)', () => {
  const models = import.meta.glob('../../public/data/models/*.json', { eager: true }) as Record<string, { default: unknown }>;
  const fixtures = import.meta.glob('../model/fixtures/stuff*_synthetic*.json', { eager: true }) as Record<string, { default: unknown }>;

  it('los modelos reales (packed, escala Plus completa, temperatura, bloque de conteo) pasan el contrato', () => {
    const names = Object.keys(models).map((p) => p.split('/').pop());
    expect(names).toEqual(expect.arrayContaining(['stuff.json', 'location.json']));
    for (const [path, mod] of Object.entries(models)) {
      const rel = `models/${path.split('/').pop()}`;
      const doc = parseContractFile(rel, mod.default) as { plus: { stats?: object }; outcome: { trees: { packed?: object }[] } };
      expect(doc.plus.stats).toBeDefined();
      expect(doc.outcome.trees[0].packed).toBeDefined();
    }
  });

  it('acepta árboles anidados y empaquetados, v1 y v2, y rechaza un árbol con ambos', () => {
    for (const mod of Object.values(fixtures)) {
      if (!(mod.default as { outcome?: unknown }).outcome) continue; // goldens are not models
      expect(() => parseContractFile('models/stuff.json', { ...(mod.default as object), model: 'pitch_family Stuff+ composite', translation: 'physics_translator', name: 'stuff' })).not.toThrow();
    }
    const one = Object.values(models)[0].default as { outcome: { trees: { tree_index: number; packed?: unknown }[] } };
    const bad = { ...(one as object), outcome: { ...one.outcome, trees: [{ ...one.outcome.trees[0], tree_structure: { leaf_value: 0 } }] } };
    expect(() => parseContractFile('models/stuff.json', bad)).toThrow();
  });
});
