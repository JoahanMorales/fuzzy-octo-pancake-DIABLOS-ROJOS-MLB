import { readFileSync } from 'node:fs';
import { expect, test, type Page } from '@playwright/test';

// HACK-070: un solo script recorre TODAS las rutas del producto (desktop y móvil, movimiento reducido).
// La lista sale de src/routes.tsx (PAGES), así una ruta nueva entra sola al recorrido. En cada ruta comprueba:
// sin errores de consola ni excepciones, sin respuestas 4xx/5xx del mismo origen, un h1 visible, que no sea el
// placeholder "En construcción", sin "undefined"/"NaN"/"[object" en el texto, y sin desborde horizontal.

interface Route {
  path: string;
  title: string;
}

/** Rutas de PAGES leídas del código fuente (routes.tsx importa Vite/React, no se puede cargar desde Playwright). */
function readRoutes(): Route[] {
  const src = readFileSync(new URL('../../src/routes.tsx', import.meta.url), 'utf8');
  const rows = [...src.matchAll(/\{\s*path:\s*'([^']+)',\s*feature:\s*'[^']+',\s*title:\s*'([^']+)'/g)];
  return rows.map(([, path, title]) => ({ path, title }));
}

const ROUTES = readRoutes();
const BAD_TEXT = /\bundefined\b|\bNaN\b|\[object /;

/** Errores de consola, excepciones y respuestas 4xx/5xx del mismo origen mientras dura la prueba. */
function watch(page: Page, origin: string): string[] {
  const problems: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') problems.push(`console: ${msg.text()}`);
  });
  page.on('pageerror', (err) => problems.push(`pageerror: ${err.message}`));
  page.on('response', (res) => {
    if (res.url().startsWith(origin) && res.status() >= 400) problems.push(`http ${res.status()}: ${res.url()}`);
  });
  return problems;
}

/** La app usa HashRouter: la ruta `/x` vive en `/#/x`. Un `goto('/x')` caería en la landing sin avisar. */
const hashUrl = (path: string) => `/#${path}`;

/** El pitcher de prueba para `/pitcher/:id`: el primer enlace de la tabla del leaderboard, nunca un id escrito a mano. */
async function firstPitcherPath(page: Page): Promise<string> {
  await page.goto(hashUrl('/leaderboard'));
  const link = page.getByRole('table').getByRole('link').first();
  await expect(link, 'el leaderboard debe enlazar a algún pitcher').toBeVisible({ timeout: 15_000 });
  const href = await link.getAttribute('href');
  expect(href, 'enlace al pitcher').toMatch(/^#\/pitcher\/.+/);
  return (href as string).slice(1);
}

/** Recorre con Tab hasta 40 controles y devuelve los que, enfocados con teclado, no dibujan contorno ni sombra de ≥ 2 px. */
async function tabStopsWithoutRing(page: Page): Promise<string[]> {
  await page.locator('body').click({ position: { x: 1, y: 1 } });
  const missing: string[] = [];
  const seen = new Set<string>();
  for (let i = 0; i < 40; i += 1) {
    await page.keyboard.press('Tab');
    const info = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return null;
      const cs = getComputedStyle(el);
      const outline = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2;
      const shadow = cs.boxShadow !== 'none' && cs.boxShadow !== '';
      const name = `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''}${el.className && typeof el.className === 'string' ? `.${el.className.split(/\s+/)[0]}` : ''} "${(el.getAttribute('aria-label') ?? el.textContent ?? '').trim().slice(0, 30)}"`;
      return { name, ring: outline || shadow };
    });
    if (!info) break;
    if (seen.has(info.name)) break; // dio la vuelta
    seen.add(info.name);
    if (!info.ring) missing.push(info.name);
  }
  return missing;
}

test('hay rutas que recorrer', () => {
  expect(ROUTES.length, 'no se pudo leer PAGES de src/routes.tsx').toBeGreaterThanOrEqual(10);
  expect(new Set(ROUTES.map((r) => r.path)).size).toBe(ROUTES.length);
});

for (const route of ROUTES) {
  test(`ruta ${route.path} (${route.title})`, async ({ page, baseURL }) => {
    const problems = watch(page, new URL(baseURL as string).origin);
    const path = route.path.includes(':') ? await firstPitcherPath(page) : route.path;

    await page.goto(hashUrl(path));
    await expect(page, 'la URL debe conservar la ruta pedida').toHaveURL(new RegExp(`#${path}$`));
    const main = page.locator('main#main');
    await expect(main).toBeVisible();
    await expect(page.getByText('Cargando…')).toHaveCount(0, { timeout: 20_000 });

    await expect(main.getByRole('heading', { level: 1 }).first(), 'cada página tiene un h1').toBeVisible();
    await expect(page.getByText(/En construcción/), 'la ruta sigue siendo placeholder').toHaveCount(0);
    await expect(page.getByText('Esta página no existe')).toHaveCount(0);

    const text = (await main.innerText()) ?? '';
    expect(text, 'texto vacío o con valores rotos').not.toMatch(BAD_TEXT);
    expect(text.trim().length).toBeGreaterThan(40);
    // DESIGN.md §Copy: cero rayas largas (em-dash) en el texto ni en las etiquetas accesibles.
    const labels = await page.locator('[aria-label],[title],[alt]').evaluateAll((els) =>
      els.flatMap((el) => ['aria-label', 'title', 'alt'].map((a) => el.getAttribute(a) ?? '')));
    expect(`${text}\n${labels.join('\n')}`, 'em-dash (—) en el copy').not.toContain('—');

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, 'desborde horizontal en px').toBeLessThanOrEqual(1);

    // DESIGN.md §Accesibilidad: todo control alcanzable con Tab muestra un foco visible (contorno o sombra de ≥ 2 px).
    const unfocusable = await tabStopsWithoutRing(page);
    expect(unfocusable, `controles sin anillo de foco en ${path}`).toEqual([]);

    // Deja pasar un momento por si algo falla al hidratar (datos, escena 3D) antes de leer los errores.
    await page.waitForTimeout(500);
    expect(problems, `problemas en ${path}`).toEqual([]);
  });
}

test('la navegación principal lleva a cada sección y una ruta inexistente muestra el 404', async ({ page }, info) => {
  const nav = page.getByRole('navigation', { name: 'Secciones' });
  await page.goto('/');
  // En móvil la navegación puede ir plegada: solo comprobamos que exista en el DOM.
  const links = nav.getByRole('link');
  expect(await links.count()).toBeGreaterThanOrEqual(5);
  if (info.project.name === 'desktop') {
    for (const route of ROUTES.filter((r) => !r.path.includes(':') && r.path !== '/')) {
      const link = nav.locator(`a[href="#${route.path}"]`);
      // Las rutas fuera del menú (nav: false) pueden no estar; las demás deben llevar a su página.
      if (await link.count()) {
        await link.first().click();
        await expect(page).toHaveURL(new RegExp(`#${route.path}$`));
        await expect(page.locator('main#main').getByRole('heading', { level: 1 }).first()).toBeVisible();
      }
    }
  }
  await page.goto(hashUrl('/ruta-que-no-existe'));
  await expect(page.getByRole('heading', { level: 1, name: 'Esta página no existe' })).toBeVisible();
});
