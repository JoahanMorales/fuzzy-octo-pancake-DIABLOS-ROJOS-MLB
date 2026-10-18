# Altitud · HACK-046

The page reads only `parks.json` and `shapes.json` aggregates, validates their
schemas and provenance, and labels mock data explicitly. Real-data discovery
follows HACK-050 contract message #355: an available JSON `data/real/manifest.json`
selects `real/`; an absent manifest selects `mock/`. Invalid real datasets fail
visibly instead of falling back to mock figures.

The score selector changes the displayed Stuff+ scenario. The forest plot always
shows CDMX minus sea level and the published intervals, without inventing
sea-level uncertainty. The expandable table preserves all figures and physics
explanations for accessible inspection.

## Geographic criterion (decision recorded 2026-10-18)

`parks.json` has no coordinates or city names, and `reports/park_id/harp_helu.md` leaves the geographic identity of
the anonymous franchises unverified. Placing the 20 parks on the outline would invent data, so the criterion is met
this way (uak decision on HACK-046, routine and reversible, delegated by joahan): the Mexico outline is shown for
context and the 20 parks sit in a panel labelled "Identidad inferida · ubicación pendiente". Their **area**, not
their radius, is proportional to the relative air density. Park selection supports pointer and keyboard input. If a
documented `id -> longitude/latitude` mapping ever lands in the contract, the circles can move onto the projection.

## Cartography provenance

`mexico.json` contains only Mexico's geometry from Natural Earth Admin 0 countries,
1:110m, downloaded 2026-10-17 from the Natural Earth maintainer's repository:

- Dataset: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson
- Dataset page: https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/
- Public-domain terms: https://www.naturalearthdata.com/about/terms-of-use/

The UI includes the dataset and license citations. The map and data load locally;
no runtime third-party map service or raw pitch data is used.

## Verification

```sh
npm --prefix web test -- --run src/features/altitud
npm --prefix web run build
```

Tests cover projection bounds, density area encoding, manifest discovery,
invalid/provenance-mismatched aggregates, 20-park selection, scenario scores,
unchanged intervals, source labels, and error recovery. Browser verification
must use reduced motion and the worktree's `$UAK_PORT + 1` on desktop and mobile.

Verified on 2026-10-17: all web tests and the production build passed. Chrome via
Playwright (reduced motion, 1440x1000 and 390x844) confirmed the forest in the first
viewport, visible focus details, park keyboard selection, scenario switching,
and no page/forest overflow or JavaScript errors. Screenshots:
`/tmp/hack046-desktop.png` and `/tmp/hack046-mobile.png` (local QA artifacts).
The full product smoke remains blocked: `exec: python: not found`, adapter exit
127; this environment also lacks the Python test/model dependencies.
