# Verification evidence (v2, HACK-059)

- `python demo/deck/build.py` → 10-slide PPTX, presentation PDF and one-page PDF, 29 source bindings and 2 derived values (league ΔStuff+ and the bias cut), all from Stuff+ v2 reports.
- `python demo/deck/verify.py` → PASS: 10 editable slides, 10-page PDF, one-page summary, 29 verified CSV values, 2 recomputed derived values, current SHA-256 source hashes; PPTX text matches the authored PDF on every slide.
- Backlog Verify: `test -s demo/deck/deck.pdf && test -s demo/one-pager/one-pager.pdf` → exit 0.
- Built on Windows 11 with the bundled DejaVu Sans (`fonts/`); no system font paths.
- Visual check of every rendered page and the one-pager: no text outside the page, no overlaps after fixing slides 4, 8 and 9 and the one-pager title.

The four headline numbers in v2: league ΔStuff+ in Harp Helú air −13.0 (was −10.3), Stuff+ v2 50-pitch r 0.269 against 0.048 for the pitcher's own results (was 0.230 against 0.051), altitude bias cut 84 % by Stuff+ v2 (was −82 % for Pitching+), and +10 Stuff+ = 1.26 wins in Harp Helú (unchanged; the runs-per-point scale was measured on Stuff+ v1).

Product screenshots in `assets/` come from the HACK-045 and HACK-072 builds; HACK-051 (Playwright) is not done yet, so replace them with its captures under the same names when it lands.

No raw records, secret files or external communications are part of the build.
