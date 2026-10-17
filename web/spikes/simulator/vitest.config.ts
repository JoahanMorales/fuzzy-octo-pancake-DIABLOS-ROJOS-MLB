import { defineConfig } from 'vitest/config';

// Spike-local: web/vitest.config.ts only includes src/** (owned by HACK-037).
export default defineConfig({
  root: __dirname,
  test: { environment: 'node', include: ['*.test.ts'] },
});
