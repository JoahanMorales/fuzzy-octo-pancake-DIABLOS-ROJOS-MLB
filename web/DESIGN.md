# DESIGN · Stuff+ 2240 web (HACK-039)

**Status: Frozen 2026-10-16.** Direction "Transmisión nocturna" (3D stylized low-poly), picked by joahan. Changes go
through `uak msg HACK-039 --kind request` with a reason; tokens live only in `src/styles/tokens.css`.
Screens: `design/desktop.png`, `design/mobile.png` (from `design/mock.html`). Every UI task loads the
`design-taste-frontend` skill first.

## Design read
Product landing + analysis app for a hackathon jury (pitching coach, GM, data scientists, a physicist), in the
language of a **night-game sports broadcast**: dark field, one hot accent, condensed display numbers, lower-third
readouts. Dials: `DESIGN_VARIANCE 7` (asymmetric hero, mixed section families), `MOTION_INTENSITY 6` (the ball
flight and camera moves carry the story; UI motion is restrained), `VISUAL_DENSITY 5` on analysis pages, 4 on
the landing.

## Theme and color (locked)
- **Dark only.** A night game under lights is the brand moment; no section flips to light. Off-black and off-white
  only (`--bg #0c0c0e`, `--fg #f1f1f3`), never pure black or white.
- **One accent: Diablos red `--red #c8102e`.** It also means **"Harp Helú / CDMX air"** in every chart, trail, dot
  and number. **Sea level is always the neutral `--sea #c9ccd3`** (ghost ball, reference lines). Never invert this.
- No purple, no neon glows, no gradient text. Gradients only as stadium light on the field (radial, green to black).
- State colors (`--ok`, `--warn`) only for real status, inline, never decorative dots.

## Type
- Display: **Barlow Condensed** 600/700, uppercase for hero and section titles, big stats. Body: **Geist** 400/500.
  Numbers in tables and units: **Geist Mono**. No Inter, no serif.
- Self-hosted in production (`@fontsource/barlow-condensed`, `@fontsource-variable/geist`, `@fontsource-variable/geist-mono`), never a Google Fonts `<link>`.
- Hero headline max 2 lines; subtext max 20 words. Section headline max 8 words.

## Shape and space
- Panels and controls: radius `--radius` 6px. Chips and toggles: full pill. Data marks (bars, zone cells): square.
- Prefer hairlines (`--line`) and spacing over cards. Cards only for the simulator panel and the pitcher card.
- 4px spacing scale (`--s-*`), content max width 1320px; mobile gutters 16px; every multi-column layout declares its
  `< 900px` single-column fallback.

## Motion
- Motion (`motion/react`) for UI; three.js / react-three-fiber for the scene. Never both in the same component tree.
- Allowed motion, each with a reason: hero ball flight (story), camera transitions (state change), pitch throw and
  trails (feedback), number count-up on the readout (state change), scroll reveal of landing sections (hierarchy).
- `prefers-reduced-motion`: no camera moves, no count-ups, flights jump to the final frame with both trails drawn.
- No scroll listeners, no marquees, no infinite decorative loops, no custom cursors.

## 3D scene (simulator, landing hero)
- **Stylized low-poly, flat shading.** Field from the tokens (`--grass`, `--dirt`, `--chalk`), stadium lights as two
  soft point lights, no photoreal textures. The ball is `--ball`; the sea-level ghost is `--sea` at 50 % opacity.
- Batter: simple low-poly figure that mirrors sides with a short animation; never a photo or a real player likeness.
- Cameras: Catcher (default), Pitcher, Lateral, Transmisión. HUD chips top-left; controls in the right rail;
  readout strip at the bottom (lower-third style, 4 values max).
- Budget: 60 fps on a mid laptop, < 150k triangles, lazy-load three.js off the landing's first paint; WebGL missing →
  2D catcher view (same data, SVG/canvas).

## Charts (dataviz skill; reference implementation `design/charts.js`)
- Two-series comparisons are **highlight vs reference**: Harp Helú air = `--red`, solid 2.5px; sea level = `--sea`,
  **dashed** 2px (secondary encoding, never color alone). Validated on `--bg`/`--surface`: deutan ΔE 31.5,
  normal ΔE 37.9, both ≥ 3:1 contrast (the grey is a neutral reference, not a categorical hue).
- Pitch graphics look like broadcast tracking, not schematics: real proportions (zone 17 in, ball 2.9 in), axes with
  units, recessive grid (`--line`), flight tubes that widen toward the catcher, an arrow or bracket that states the
  movement lost, direct labels in a right-hand column. Text always in text tokens; the swatch carries identity.
- A legend for every chart with ≥ 2 series, plus direct labels; no dual axes; markers ≥ 8px with a 2px surface ring;
  every chart has hover/focus tooltips in the product and a short text conclusion beside it.

## Copy (Spanish)
- Plain, concrete sentences. Zero em-dashes. Hyphen for ranges; the minus sign for negative numbers.
- Every number comes from a contract JSON (`public/data/`), never typed in a component. Mocks say "ejemplo".
- Labels used everywhere the same way: "nivel del mar", "aire del Harp Helú", "Stuff+ neutral", "Stuff+ en CDMX",
  "identificación inferida" for anything about the Diablos staff.
- One label per intent: primary CTA "Probar el simulador", secondary "Ver la metodología".

## Accessibility
- Text contrast WCAG AA (body ≥ 4.5:1 on `--bg`, `--fg-muted` passes on `--bg` and `--surface`).
- Every control reachable by keyboard with a visible focus ring (`--fg` 2px outline); the 3D view has a text
  summary of the last pitch for screen readers.
- Charts carry a short text conclusion next to them.

## Banned here (from the taste skill, the ones most likely to sneak in)
Three equal feature cards, eyebrows above every section (max 1 per 3 sections), fake screenshots made of divs,
version labels or "BETA" in the hero, scroll cues, decorative status dots, pills over images, gradient text,
light sections inside the dark page.
