import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

// Spike-local: web/vitest.config.ts only includes src/** (owned by HACK-037).
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  test: { environment: 'node', include: ['*.test.ts'] },
});
