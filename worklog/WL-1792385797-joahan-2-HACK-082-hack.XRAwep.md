# worklog/WL-1792385797-joahan-2-HACK-082-hack.XRAwep.md · HACK-082

## Live summary
- Done: 26864e5c: verify.py PASS; sources.json hashes == sha256 of git show HEAD:<path> for all 11 sources (0 mismatches), so it passes on macOS checkouts too; check_numbers unchanged
- Decision: Recruiting thresholds and memo wait for HACK-083 (ideal_profile v2) to merge; demo/qa.md Q11 lives on feat/hack-025 (not on main)
- Why: memo reads reports/ideal_profile; 083 owns those files
- Failing: none
- Commands: python docs/technical/check_numbers.py && python demo/deck/verify.py
- Next: Integrated in main: 1f99f873f59d362982b34a4b6a89bfa33684e917 (recorded by joahan-2)

## History
- 1792385797 | CLAIMED | joahan-2 | claim; next: wait for 076–078, then run the three generators in that order.
- 1792386152 | CLAIMED | joahan-2 | checkpoint; next: After 083 merges: merge main, run reports/recommendations/build_memo.py, update paper §7 thresholds (IVB 21.1/5.8, extension -11.0/-15.3, VAA -12.4/-14.1, ride vs sweeper runs), rebuild PDF + deck, done
- 1792387507 | REVIEW | joahan-2 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-082?expand=1; evidence: 9c9b5ff: python docs/technical/check_numbers.py NUMBERS_OK (34 blocks) && python demo/deck/verify.py PASS (29 values, 2 derived) && stuffplus2240.pdf 9 pages. Changed old->new: runs per point 7.24e-4->8.68e-4; +10 Stuff+ HH wins 1.26->1.51 (18.1->21.7 runs); 1 SD 0.69->0.77 wins (5.45->5.08 pts); staff runs 3.8/5.5->4.5/6.5 (wins 0.26/0.38->0.32/0.46; mix 2.0/4.3->2.3/5.2; starts 1.82/1.15->2.18/1.38); sensitivity corr 0.57/0.68->0.53/0.69; IVB swing 20.9/7.6->21.1/5.8; extension -9.7/-12.8->-11.0/-15.3; VAA -9.1/-13.1->-12.4/-14.1; ride vs sweeper 6.0->7.2 runs per 1,000. Memo built with HACK-083 CSVs (in review); web real export unchanged by these reports; demo/qa.md Q11 lives on feat/hack-025; reviewer: -
- 1792462164 | REVIEW | luis-1 | review; reject; SHA 996646dbd048b314c90ab5980c6d4957ece94fba; reviewer luis-1
- 1792462462 | REVIEW | joahan-2 | done; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-082?expand=1; evidence: 26864e5c: verify.py PASS; sources.json hashes == sha256 of git show HEAD:<path> for all 11 sources (0 mismatches), so it passes on macOS checkouts too; check_numbers unchanged; reviewer: -
- 1792503750 | REVIEW | sebastian-2 | review; approve; SHA 26864e5c529219614c40fef93f9206a17ffde5a5; reviewer sebastian-2
- 1792533504 | INTEGRATED | joahan-2 | integrate; recorded by joahan-2; PR https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/compare/main...feat/hack-082?expand=1; merged 1f99f873f59d362982b34a4b6a89bfa33684e917; proof ancestry
