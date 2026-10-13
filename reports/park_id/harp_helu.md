# Harp Helú candidate (HACK-003)

- Extreme franchises (6): lowest rho_hat = 11 (0.813) and 5 (0.821).
- P(franchise 11 lower than 5) = 0.832 (pooled game-level bootstrap, 2000 draws).
- Decisive (P >= 0.95): NO. Reporting the two lowest-density parks and pooling them: franchises [11, 5].
- Pooled rho_hat of [11, 5]: 0.819 (95% CI 0.814-0.824, 148 games). Provisional proxy; HACK-004 replaces it.
- Theoretical gap Harp Helú (2,240 m) vs Puebla (2,135 m): ~1.2 % pressure; observed gap 0.7 % of rho.
- Franchise identity (CDMX vs Puebla) is NOT verified from the data: ids are anonymous. Confirm with Diablos staff.
- Coverage caveat: the lowest-rho franchise has few home games in the dataset {2024: 3, 2025: 14, 2026: 16} (home games per season).

## Candidate staff (pitchers per season; ids via `candidate_staff(load_maps(), franchises)`)

```
franchise  5   11
season           
2024       30  20
2025       31  18
2026       29  22
```
