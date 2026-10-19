import { defineConfig, devices } from '@playwright/test';

// End-to-end tests live in web/e2e/ (HACK-051). They run against the static build served by `vite preview`.
const port = Number(process.env.UAK_PORT ?? 8400) + 1;

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    reducedMotion: 'reduce',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    // Same host as baseURL: plain `localhost` resolves to ::1 on macOS and the IPv4 baseURL is refused.
    command: `npm run build && npm run preview -- --host 127.0.0.1 --port ${port} --strictPort`,
    port,
    reuseExistingServer: true,
    timeout: 180_000,
  },
});
