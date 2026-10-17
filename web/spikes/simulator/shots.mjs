// Screenshots of the spike for the PR (node web/spikes/simulator/shots.mjs <url> <outdir>). Uses the local Edge.
import { chromium } from '@playwright/test';

const [url = 'http://127.0.0.1:8701/spikes/simulator/', out = '.'] = process.argv.slice(2);
const browser = await chromium.launch({ channel: 'msedge', args: ['--use-angle=d3d11', '--enable-gpu'] });
const errors = [];

async function shoot(name, { width, height, reduced = false, view, batter = false, wait = 4500 }) {
  const page = await browser.newPage({ viewport: { width, height }, reducedMotion: reduced ? 'reduce' : 'no-preference' });
  page.on('console', (m) => m.type() === 'error' && errors.push(`${name}: ${m.text()}`));
  page.on('pageerror', (e) => errors.push(`${name}: ${e.message}`));
  await page.goto(url);
  await page.waitForSelector('canvas', { timeout: 20000 });
  if (view) await page.getByRole('button', { name: view, exact: true }).click();
  if (batter) await page.getByRole('button', { name: /cambiar/ }).click();
  if (view || batter) await page.getByRole('button', { name: /Lanzar/ }).click();
  await page.waitForTimeout(wait);
  await page.screenshot({ path: `${out}/${name}.png` });
  const fps = await page.evaluate(
    () => new Promise((res) => { let n = 0; const t0 = performance.now(); const f = () => { n++; if (performance.now() - t0 < 1000) requestAnimationFrame(f); else res(n); }; requestAnimationFrame(f); }),
  );
  console.log(name, 'fps≈', fps);
  await page.close();
}

await shoot('catcher', { width: 1440, height: 900 });
await shoot('broadcast', { width: 1440, height: 900, view: 'Transmisión' });
await shoot('lateral', { width: 1440, height: 900, view: 'Lateral' });
await shoot('pitcher', { width: 1440, height: 900, view: 'Pitcher' });
await shoot('zurdo', { width: 1440, height: 900, batter: true });
await shoot('mobile', { width: 390, height: 844, reduced: true, wait: 2500 });
await browser.close();
console.log(errors.length ? errors.join('\n') : 'no console errors');
