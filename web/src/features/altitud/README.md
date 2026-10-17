# Altitud · HACK-046 (partial)

The page reads only `parks.json` and `shapes.json` aggregates, validates their
schemas and provenance, and labels mock data explicitly. Real-data discovery
follows HACK-050 contract message #355: an available JSON `data/real/manifest.json`
selects `real/`; an absent manifest selects `mock/`. Invalid real datasets fail
visibly instead of falling back to mock figures.

The score selector changes the displayed Stuff+ scenario. The forest plot always
shows CDMX minus sea level and the published intervals, without inventing
sea-level uncertainty. The expandable table preserves all figures and physics
explanations for accessible inspection.

## Open geographic acceptance criterion

`parks.json` has no coordinates or city names. `reports/park_id/harp_helu.md`
explicitly leaves the geographic identity of anonymous franchises unverified.
The 20 circles therefore appear in a panel labelled as unlocated, not as points
on the Mexico outline. Their **area**, rather than radius, is proportional to
the relative air density. Park selection supports pointer and keyboard input.

**Do not call HACK-046 complete or merge this draft as a completed task** until a
documented `id -> longitude/latitude` mapping is available, or the responsible
human revises the geographic criterion. UAK request #358 asks HACK-038 for it.

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
