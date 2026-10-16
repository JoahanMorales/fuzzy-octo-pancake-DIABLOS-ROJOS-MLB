# Stuff+ 2240 · web (React + Vite + three.js)

Static product site: landing, 3D simulator and analysis pages. Everything runs in the browser from aggregated JSON
(`public/data/`, HACK-038/050) and tree models exported from Python (HACK-040). No server, no pitch-level data.

```sh
npm --prefix web ci          # install (lockfile)
npm --prefix web run dev     # http://localhost:5173
npm --prefix web test -- --run
npm --prefix web run build   # web/dist/ (relative base + hash routes: any static host)
```

## Adding a page (feature tasks)

Create `web/src/features/<feature>/index.tsx` with a default-exported component. `src/routes.tsx` discovers it
with `import.meta.glob`; until it exists the route shows a placeholder. Feature tasks never edit the shell
(`App.tsx`, `routes.tsx`, `shell/`): ask HACK-037's owner with `uak msg` if a route must change.

| Route | Feature folder | Task |
|---|---|---|
| `/` | `landing` | HACK-043 |
| `/simulador` | `simulador` | HACK-044/045 |
| `/altitud` | `altitud` | HACK-046 |
| `/leaderboard`, `/pitcher/:id` | `leaderboard`, `pitcher` | HACK-047 |
| `/staff`, `/prospecto`, `/laboratorio` | `staff`, `prospecto`, `laboratorio` | HACK-048 |
| `/metodologia` | `metodologia` | HACK-049 |

Design tokens: `src/styles/tokens.css` (HACK-039) is loaded when present; `base.css` has fallbacks.
Tests: vitest + Testing Library (`src/**/*.test.tsx`); end-to-end: Playwright in `e2e/` (HACK-051).
