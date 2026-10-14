# Verification evidence

- `test -s demo/deck/README.md` → exit 0 (backlog Verify).
- `python demo/deck/build.py` → built 10-slide PPTX, presentation PDF and one-page executive PDF, with 21 source bindings.
- `python demo/deck/verify.py` → PASS: 10 editable slides, 10-page presentation PDF, one-page summary, 21 verified CSV values and current SHA-256 source hashes.
- LibreOffice 26.8.1 headless exported the actual PPTX to PDF: 10 pages.
- `python demo/deck/verify.py --rendered <LibreOffice-export.pdf>` → PASS, all text matches between the actual PPTX export and the authored PDF. Geometry checks found no content outside the page or slide.
- Visual inspection: all ten slides in the final LibreOffice export montage, the presentation PDF, and the executive summary rendered at 150% were legible and had no unintended overlaps. Rectangle theme shadows were removed after the first export.

The deck deliberately distinguishes measured physical contrasts, modeled changes,
transductive model metrics and scenarios. Named-park identity, actual staff audit,
real prospect evaluation and a verified live dashboard are not claimed.
The canonical presentation and one-pager use tracked aggregate CSVs. No raw records,
secret files, accounts, publishing or external communications are part of the build.

Dependencies were isolated in a temporary artifact environment. LibreOffice ran
from a temporary read-only disk image; no system installation was required.
The PPTX remains editable and carries a Spanish presenter script in its notes.

`bash .uak/bin/smoke` → exit 0 in 154 s, `PRODUCT_PASS: current adapter exited 0.`
The artifact environment package versions are pinned in `requirements.txt`.
