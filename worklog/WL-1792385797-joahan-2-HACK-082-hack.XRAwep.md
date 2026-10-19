# worklog/WL-1792385797-joahan-2-HACK-082-hack.XRAwep.md · HACK-082

## Live summary
- Done: 1f9b220: staff audit re-run (v2 scores from hack-057 artifacts, v2 sensitivity and business conversion: 4.5/6.5 runs), paper/deck/one-pager on the v2 business scale (8.68e-4, 1.51 wins), check_numbers OK, deck verify PASS, PDF rebuilt; web real export unchanged by these
- Decision: Recruiting thresholds and memo wait for HACK-083 (ideal_profile v2) to merge; demo/qa.md Q11 lives on feat/hack-025 (not on main)
- Why: memo reads reports/ideal_profile; 083 owns those files
- Failing: none
- Commands: python docs/technical/check_numbers.py && python demo/deck/verify.py
- Next: After 083 merges: merge main, run reports/recommendations/build_memo.py, update paper §7 thresholds (IVB 21.1/5.8, extension -11.0/-15.3, VAA -12.4/-14.1, ride vs sweeper runs), rebuild PDF + deck, done

## History
- 1792385797 | CLAIMED | joahan-2 | claim; next: wait for 076–078, then run the three generators in that order.
- 1792386152 | CLAIMED | joahan-2 | checkpoint; next: After 083 merges: merge main, run reports/recommendations/build_memo.py, update paper §7 thresholds (IVB 21.1/5.8, extension -11.0/-15.3, VAA -12.4/-14.1, ride vs sweeper runs), rebuild PDF + deck, done
