# Spike HACK-060: simulador 3D

El mismo release lanzado dos veces: a nivel del mar (fantasma gris, estela punteada) y en el aire del Harp Helú
(estela roja). Campo low-poly con sombreado plano, bateador que cambia de lado y cuatro cámaras (Catcher, Pitcher,
Lateral, Transmisión).

- `flight.ts`: port exacto de `stuffplus/physics/flight.py` (HACK-041). `flight.test.ts` compara contra
  `parity.fixture.json`, generado con el `fly()` de Python sobre releases sintéticos (tolerancia 1e-7 ft).
- `physics.json`: subconjunto de `reports/physics_v2/physics.json` (ρ del Harp Helú, C_D y elasticidad del Magnus
  por familia). `presets.json`: lanzamientos de ejemplo, no de un pitcher real.
- `model.ts` (datos y ejes), `Scene.tsx` (r3f, sin Motion), `App.tsx` (HUD), `Fallback2D.tsx` (sin WebGL).
- Movimiento reducido: la cámara no se mueve, el vuelo salta al cuadro final con las dos estelas.
- Capturas en `screenshots/` (Edge, 1440×900 y 390×844); 60 fps en todas las cámaras.

Comandos (desde `web/`):

```bash
npx vite --port 8701
```

Abre `http://127.0.0.1:8701/spikes/simulator/`.

```bash
npx tsc --noEmit -p spikes/simulator && npx vitest run --config spikes/simulator/vitest.config.ts
```

```bash
npx vite build --config spikes/simulator/vite.config.ts
```

Para HACK-044/045: `flight.ts` y `model.ts` pasan tal cual a `src/`; `Scene.tsx` se parte en campo, figuras y
lanzamiento; los colores ya se leen de `tokens.css` en tiempo de ejecución. `@fontsource-variable` registra
`'Geist Variable'`, no `'Geist'`: `tokens.css` debe nombrarla así o la fuente cae al respaldo.
