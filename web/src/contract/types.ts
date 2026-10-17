import { z } from 'zod';

/** Contrato web (HACK-038). Cada archivo de public/data lleva este sobre. */
export const envelopeSchema = z.object({
  model_version: z.string().min(1),
  model: z.literal('pitch_family Stuff+ composite'),
  translation: z.literal('physics_translator'),
  demo_data: z.boolean(),
  sources: z.array(z.string().min(1)).min(1),
});

export const parkSchema = z.object({
  id: z.string().min(1),
  rho: z.number(),
  bucket: z.string().min(1),
  air_effect: z.number(),
  altitude: z.string().min(1),
}).strict();

export const parksSchema = envelopeSchema.extend({
  parks: z.array(parkSchema).length(20),
}).strict();

export const shapeSchema = z.object({
  shape: z.string().min(1),
  pitches: z.number().int().nonnegative(),
  pitchers: z.number().int().nonnegative(),
  stuff_sea_level: z.number(),
  stuff_harp_helu: z.number(),
  delta_stuff: z.number(),
  delta_lo: z.number(),
  delta_hi: z.number(),
  delta_ivb_in: z.number(),
  delta_hb_arm_in: z.number(),
  delta_whiff_pct: z.number(),
  delta_called_strike_pct: z.number(),
  delta_in_play_pct: z.number(),
  delta_contact_runs: z.number(),
  delta_hard_contact_pct: z.number(),
  delta_hr_per_fb_pct: z.number(),
  relative_to_league: z.number(),
  verdict: z.string(),
  physics: z.string(),
}).strict();

export const shapesSchema = envelopeSchema.extend({
  shapes: z.array(shapeSchema).min(1),
}).strict();

export const leaderboardRowSchema = z.object({
  pitcher_anon_id: z.string().min(1),
  year: z.number().int(),
  pitches: z.number().int().nonnegative(),
  throws: z.string().min(1),
  stuff_plus: z.number(),
  stuff_plus_harp_helu: z.number(),
  stuff_plus_own_air: z.number(),
  location_plus: z.number(),
  pitching_plus: z.number(),
  delta_cdmx: z.number(),
  arsenal: z.string(),
  stuff_plus_percentile: z.number(),
}).strict();

export const leaderboardSchema = envelopeSchema.extend({
  rows: z.array(leaderboardRowSchema).min(1),
}).strict();

const nullableNumber = z.number().nullable();

export const staffPitcherSchema = z.object({
  pitcher_anon_id: z.string().min(1),
  throws: z.string().min(1),
  role: z.string().min(1),
  pitches: z.number().int().nonnegative(),
  home_pitches: z.number().int().nonnegative(),
  stuff_plus: nullableNumber,
  stuff_plus_harp_helu: nullableNumber,
  pitching_plus: nullableNumber,
  location_plus: nullableNumber,
  delta_cdmx: nullableNumber,
  altitude_resilience: nullableNumber,
  own_air_home: nullableNumber,
  own_air_road: nullableNumber,
}).strict();

export const staffSchema = envelopeSchema.extend({
  pooled: z.literal(false),
  note: z.string().min(1),
  franchises: z.array(z.object({
    id: z.string().min(1),
    pitchers: z.array(staffPitcherSchema).min(1),
  }).strict()).min(2),
}).strict();

export const altitudeModelSchema = z.object({
  model: z.string().min(1),
  league_delta: z.number(),
  best_shape: z.string().min(1),
  best_delta: z.number(),
  worst_shape: z.string().min(1),
  worst_delta: z.number(),
}).passthrough();

export const adoptionSchema = z.object({
  rule: z.string().min(1),
  check: z.string().min(1),
  value: z.string(),
  passed: z.boolean(),
}).strict();

export const validationRowSchema = z.object({
  split: z.string().min(1),
  model: z.string().min(1),
  metric: z.string().min(1),
  value: z.number(),
  demo_data: z.boolean(),
  evidence: z.string(),
}).strict();

export const validationSchema = envelopeSchema.extend({
  highlights: z.object({
    league_delta_cdmx: z.number(),
    best_shape: z.string().min(1),
    best_delta: z.number(),
    worst_shape: z.string().min(1),
    worst_delta: z.number(),
    source_model: z.string().min(1),
  }).strict(),
  altitude_models: z.array(altitudeModelSchema).min(1),
  adoption: z.array(adoptionSchema).min(1),
  rows: z.array(validationRowSchema).min(1),
}).strict();

export const physicsFamilySchema = z.object({
  pitch_family: z.string().min(1),
  cd_sea: z.number(),
  cl_sea: z.number(),
  cl_lo: z.number(),
  cl_hi: z.number(),
  cd_extreme: z.number(),
  cl_extreme: z.number(),
  elasticity: z.number(),
  elasticity_lo: z.number(),
  elasticity_hi: z.number(),
}).strict();

export const physicsSchema = envelopeSchema.extend({
  families: z.array(physicsFamilySchema).min(1),
}).strict();

export type TreeNode = {
  split_feature?: number;
  threshold?: number | string;
  decision_type?: string;
  default_left?: boolean;
  missing_type?: string;
  left_child?: TreeNode;
  right_child?: TreeNode;
  leaf_index?: number;
  leaf_value?: number;
};

export const treeNodeSchema: z.ZodType<TreeNode> = z.lazy(() => z.object({
  split_feature: z.number().int().nonnegative().optional(),
  threshold: z.union([z.number(), z.string()]).optional(),
  decision_type: z.string().optional(),
  default_left: z.boolean().optional(),
  missing_type: z.string().optional(),
  left_child: treeNodeSchema.optional(),
  right_child: treeNodeSchema.optional(),
  leaf_index: z.number().int().optional(),
  leaf_value: z.number().optional(),
}));

export const boosterTreeSchema = z.object({
  tree_index: z.number().int().nonnegative(),
  tree_structure: treeNodeSchema,
}).strict();

export const modelSchema = envelopeSchema.extend({
  name: z.enum(['stuff', 'location', 'pitching']),
  features: z.array(z.string().min(1)).min(1),
  categories: z.record(z.array(z.string())),
  class_values: z.array(z.object({
    outcome: z.string().min(1),
    rv: z.number(),
  }).strict()).min(1),
  plus: z.object({
    center: z.number(),
    spread: z.number(),
    reference: z.literal('park-neutral'),
  }).strict(),
  outcome: z.object({
    num_class: z.number().int().positive(),
    trees: z.array(boosterTreeSchema).min(1),
  }).strict(),
  contact: z.object({
    trees: z.array(boosterTreeSchema).min(1),
  }).strict(),
}).strict();

export const arsenalPitchSchema = z.object({
  pitch_id: z.number().int().nonnegative(),
  pitch_family: z.string().min(1),
  shape: z.string(),
  pitches: z.number().int().nonnegative(),
  usage: z.number(),
  velo: z.number(),
  ivb: z.number(),
  hb: z.number(),
  spin: z.number(),
  stuff_plus: z.number(),
  stuff_plus_harp_helu: z.number(),
  stuff_plus_own_air: z.number(),
  location_plus: z.number(),
  pitching_plus: z.number(),
  delta_cdmx: z.number(),
}).strict();

export const pitcherSchema = envelopeSchema.extend({
  id: z.string().min(1),
  seasons: z.array(z.object({
    year: z.number().int(),
    pitches: z.number().int().nonnegative(),
    throws: z.string().min(1),
    stuff_plus: z.number(),
    stuff_plus_harp_helu: z.number(),
    stuff_plus_own_air: z.number(),
    location_plus: z.number(),
    pitching_plus: z.number(),
    delta_cdmx: z.number(),
    arsenal: z.string(),
    stuff_plus_percentile: z.number(),
    arsenal_pitches: z.array(arsenalPitchSchema),
  }).strict()).min(1),
}).strict();

const ROOT_SCHEMAS: Record<string, z.ZodTypeAny> = {
  'parks.json': parksSchema,
  'shapes.json': shapesSchema,
  'leaderboard.json': leaderboardSchema,
  'staff.json': staffSchema,
  'validation.json': validationSchema,
  'physics.json': physicsSchema,
  'models/stuff.json': modelSchema,
  'models/location.json': modelSchema,
  'models/pitching.json': modelSchema,
};

export function parseContractFile(relativePath: string, data: unknown) {
  const schema = ROOT_SCHEMAS[relativePath]
    ?? (relativePath.startsWith('pitcher/') && relativePath.endsWith('.json') ? pitcherSchema : undefined);
  if (!schema) {
    throw new Error(`sin esquema: ${relativePath}`);
  }
  return schema.parse(data);
}
