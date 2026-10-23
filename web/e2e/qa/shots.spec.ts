import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

// HACK-070: capturas de cada ruta a 1440 px (escritorio) y 390 px (móvil), con movimiento reducido (playwright.config.ts).
// Alimentan la revisión design-critic contra web/DESIGN.md (ver INFORME.md). Solo se escriben con QA_SHOTS=1 para que
// las corridas normales de e2e no reescriban imágenes:
//   QA_SHOTS=1 npm --prefix web run e2e -- --project=desktop e2e/qa/shots.spec.ts

const VIEWPORTS = [
  { tag: '1440', width: 1440, height: 900 },
  { tag: '390', width: 390, height: 844 },
];

function readPaths(): string[] {
  const src = readFileSync(new URL('../../src/routes.tsx', import.meta.url), 'utf8');
  return [...src.matchAll(/\{\s*path:\s*'([^']+)',\s*feature:/g)].map(([, p]) => p).filter((p) => !p.includes(':'));
}

const slug = (path: string) => (path === '/' ? 'inicio' : path.slice(1).replace('/:id', ''));

test.skip(!process.env.QA_SHOTS, 'solo con QA_SHOTS=1');

// `/pitcher/:id`: el pitcher sale del primer enlace de la tabla del leaderboard, nunca un id escrito a mano.
const PITCHER = '/pitcher/:id';

for (const path of [...readPaths(), PITCHER]) {
  for (const vp of VIEWPORTS) {
    test(`captura ${path} a ${vp.tag}px`, async ({ page }, info) => {
      test.skip(info.project.name !== 'desktop', 'los dos anchos se fijan aquí; basta con un proyecto');
      await page.setViewportSize({ width: vp.width, height: vp.height });
      if (path === PITCHER) {
        await page.goto('/#/leaderboard');
        const link = page.getByRole('table').getByRole('link').first();
        await expect(link).toBeVisible({ timeout: 15_000 });
        await link.click();
      } else {
        await page.goto(`/#${path}`);
      }
      await expect(page.locator('main#main')).toBeVisible();
      await expect(page.getByText('Cargando…')).toHaveCount(0, { timeout: 20_000 });
      for (let i = 0; i < 10; i += 1) {
        await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => resolve(null))));
      }
      await page.waitForTimeout(400);
      await page.screenshot({ path: `e2e/qa/shots/${slug(path)}-${vp.tag}.jpg`, type: 'jpeg', quality: 70, fullPage: false });
    });
  }
}
