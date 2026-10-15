# Verification evidence

- `test -s demo/deck/README.md` → exit 0 (backlog Verify).
- `python demo/deck/build.py` → 10-slide PPTX, presentation PDF and one-page executive PDF, 30 source bindings.
- `python demo/deck/verify.py` → PASS: 10 editable slides, 10-page presentation PDF, one-page summary, 30 verified CSV values and current SHA-256 source hashes. PPTX text matches the authored PDF.
- Visual check of the rendered PDF pages: slides 1, 4, 7, 8, 9 and 10, plus the one-page summary. No text outside the page. Slide 9 footer sits below the caveat (y 356 vs 337).

Staff figures come only from `reports/staff_audit/runs_saved.csv`. Franchises 5 and 11 stay separate. Holdout skill comes from `reports/validation/headline.csv`. The reference fastball comes from `reports/ideal_profile/best_fastballs.csv` rank 1. The Stuff+ scale comes from `reports/business_value/runs_per_point_direct.csv`.

This rebuild did not re-export the PPTX through LibreOffice. The authored PDF is what `verify.py` checks against the editable PPTX.

No raw records, secret files or external communications are part of the build.
