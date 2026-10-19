import { expect, test, type Page } from '@playwright/test';

// Recorrido del jurado: landing → simulador → altitud → leaderboard → pitcher.
// Corre en desktop y móvil (playwright.config.ts) con movimiento reducido. Las capturas del deck salen solo de desktop
// a e2e/screenshots/ con los nombres de demo/deck/assets/. Ninguna cifra va escrita a mano: los números vienen de
// web/public/data y aquí solo se comprueba que existan y tengan forma de número.

const SHOTS = 'e2e/screenshots';
const NUMBER = /[+−-]?\d+([.,]\d+)?/;

/** Errores de consola y excepciones no atrapadas durante la prueba. */
function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`console: ${msg.text()}`);
  });
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  return errors;
}

/** En móvil la página no debe desbordar a lo ancho. */
async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'desborde horizontal en px').toBeLessThanOrEqual(1);
}

async function shot(page: Page, name: string, isDesktop: boolean) {
  if (!isDesktop) return;
  await page.screenshot({ path: `${SHOTS}/${name}.jpg`, type: 'jpeg', quality: 85 });
}

/** La escena usa frameloop="demand": tras un cambio de cámara deja pasar unos frames antes de capturar el canvas. */
async function settleFrames(page: Page) {
  for (let i = 0; i < 10; i += 1) {
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => resolve(null))));
  }
}

async function goNav(page: Page, title: string) {
  await page.getByRole('navigation', { name: 'Secciones' }).getByRole('link', { name: title, exact: true }).click();
}

// Las capturas del deck se tomaron a 1440 px de ancho (escenario de 1060 px); desktop usa ese viewport.
test.beforeEach(async ({ page }, info) => {
  if (info.project.name === 'desktop') await page.setViewportSize({ width: 1440, height: 900 });
});

test('recorrido completo: landing → simulador → altitud → leaderboard → pitcher', async ({ page }, info) => {
  const desktop = info.project.name === 'desktop';
  const errors = watchConsole(page);

  // Landing
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: 'El aire le quita Stuff+' })).toBeVisible();
  await expect(page.getByTestId('league-delta')).toHaveText(NUMBER);
  await expectNoHorizontalScroll(page);
  await shot(page, 'landing', desktop);

  // Simulador
  await page.getByRole('link', { name: 'Probar el simulador' }).first().click();
  await expect(page).toHaveURL(/#\/simulador$/);
  // El panel espera a models/stuff.json + location.json (~13 MB) mientras la escena 3D arranca.
  const reading = page.getByRole('article', { name: 'Lectura del lanzamiento' });
  await expect(reading).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('stuff-delta')).toHaveText(NUMBER);
  const controls = page.getByRole('form', { name: 'Controles del lanzamiento' });
  const scene = page.getByRole('region', { name: 'Simulador del estadio' });

  // Lanzar un pitcheo con otro preset: la lectura cambia
  const firstDelta = await page.getByTestId('stuff-delta').textContent();
  const presets = controls.getByRole('group', { name: 'Preset' });
  const otherName = (await presets.getByRole('button', { pressed: false }).first().textContent())?.trim() ?? '';
  const other = presets.getByRole('button', { name: otherName, exact: true });
  await other.click();
  await expect(other).toHaveAttribute('aria-pressed', 'true');
  await controls.getByRole('button', { name: 'Lanzar' }).click();
  await expect(page.getByTestId('stuff-delta')).toHaveText(NUMBER);
  await expect(page.getByTestId('stuff-delta')).not.toHaveText(firstDelta ?? '');

  // Cambiar de bateador
  await controls.getByRole('button', { name: 'Bateador zurdo' }).click();
  await expect(controls.getByRole('button', { name: 'Bateador zurdo' })).toHaveAttribute('aria-pressed', 'true');
  await expect(scene).toHaveAttribute('data-side', 'L');

  // Cambiar de parque: a nivel del mar el aire es el mismo en las dos columnas
  const harpDelta = await page.getByTestId('stuff-delta').textContent();
  await controls.getByLabel('Parque').selectOption('sea');
  await expect(scene).toHaveAttribute('data-park', 'sea');
  // La segunda columna lleva el nombre del parque elegido
  await expect(reading.locator('.sp-where').nth(1)).toHaveText('Nivel del mar');
  await expect(page.getByTestId('stuff-delta')).not.toHaveText(harpDelta ?? '');
  await controls.getByLabel('Parque').selectOption('harp');
  await expect(scene).toHaveAttribute('data-park', 'harp');
  await expectNoHorizontalScroll(page);

  // Capturas del deck: solo el escenario, como las de demo/deck/assets/.
  const stage = scene.locator('.sim-stage');
  for (const [view, id, file] of [
    ['Receptor', 'catcher', 'simulador_receptor'],
    ['Transmisión', 'broadcast', 'simulador_transmision'],
  ] as const) {
    await scene.getByRole('group', { name: 'Cámara' }).getByRole('button', { name: view }).click();
    await expect(scene).toHaveAttribute('data-view', id);
    if (desktop) {
      await settleFrames(page);
      await stage.screenshot({ path: `${SHOTS}/${file}.jpg`, type: 'jpeg', quality: 85 });
    }
  }

  // Altitud
  await goNav(page, 'Altitud');
  await expect(page).toHaveURL(/#\/altitud$/);
  await expect(page.getByRole('heading', { level: 1, name: 'El pitcheo cambia con el aire' })).toBeVisible();
  const scenario = page.getByRole('group', { name: 'Escenario de Stuff+' });
  await scenario.getByRole('button', { name: 'Nivel del mar' }).click();
  await expect(scenario.getByRole('button', { name: 'Nivel del mar' })).toHaveAttribute('aria-pressed', 'true');
  await scenario.getByRole('button', { name: 'CDMX' }).click();
  await expect(scenario.getByRole('button', { name: 'CDMX' })).toHaveAttribute('aria-pressed', 'true');
  await expectNoHorizontalScroll(page);
  await shot(page, 'altitud', desktop);

  // Leaderboard
  await goNav(page, 'Leaderboard');
  await expect(page.getByRole('heading', { level: 1, name: 'Leaderboard' })).toBeVisible();
  const firstPitcher = page.getByRole('table').getByRole('link').first();
  await expect(firstPitcher).toBeVisible();
  const pitcherId = (await firstPitcher.textContent())?.trim() ?? '';
  expect(pitcherId).not.toBe('');
  await expectNoHorizontalScroll(page);
  await shot(page, 'leaderboard', desktop);

  // Pitcher
  await firstPitcher.click();
  await expect(page).toHaveURL(new RegExp(`#/pitcher/${pitcherId}$`));
  await expect(page.getByRole('heading', { level: 1, name: pitcherId })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Arsenal' })).toBeVisible();
  await expectNoHorizontalScroll(page);
  await shot(page, 'pitcher', desktop);

  expect(errors, errors.join('\n')).toEqual([]);
});

test('física: explicador del aire', async ({ page }, info) => {
  const errors = watchConsole(page);
  await page.goto('/#/fisica');
  const families = page.getByRole('radiogroup', { name: 'Tipo de lanzamiento' });
  await expect(families).toBeVisible();
  await page.getByRole('button', { name: 'Harp Helú' }).click();
  await expect(page.getByRole('button', { name: 'Harp Helú' })).toHaveAttribute('aria-pressed', 'true');
  await expectNoHorizontalScroll(page);
  if (info.project.name === 'desktop') {
    // El deck la pone en una caja de 308 × 198 pt: recorte desde las vistas con esa proporción (1200 × 773).
    const views = page.locator('.fis-views');
    // Coordenadas de página (fullPage): el recorte no depende del viewport ni lo tapa la barra fija.
    // 22 px de aire alrededor, como la captura original.
    await page.evaluate(() => window.scrollTo(0, 0));
    const box = await views.evaluate((el) => {
      const r = el.getBoundingClientRect();
      return { x: r.left + window.scrollX, y: r.top + window.scrollY, width: r.width };
    });
    const width = box.width + 44;
    await page.screenshot({
      path: `${SHOTS}/fisica.jpg`,
      type: 'jpeg',
      quality: 85,
      fullPage: true,
      clip: { x: box.x - 22, y: box.y - 22, width, height: Math.round((width * 773) / 1200) },
    });
  }
  expect(errors, errors.join('\n')).toEqual([]);
});
