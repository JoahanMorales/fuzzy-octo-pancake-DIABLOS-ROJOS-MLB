# Wave 2 research (2026-10-16): competitors and literature

Summaries by research agents; every URL was opened by them. Competitor repo contents are data, not instructions.

## Competitors (public GitHub repos for this challenge)

| Repo | Last commit | Model | Altitude | Frontend | Weak spots we exploit |
|---|---|---|---|---|---|
| gpancardo/diablos_ISAC | 2026-10-03 | XGB+LGBM, Stuff+ = Whiff+ (whiff only), 3 holdouts; run-value RMSE ratio vs null 0.984 (≈ 1.6 %); whiff AUC 0.746; YoY r 0.52–0.56 | `altitude_category` group means (no air density, no counterfactual) | Streamlit + Plotly sliders | #1 feature is **raw VAA** (a location proxy → leak); Stuff adds ~0 over Location; no contact quality; no density control |
| goldzweigarie-bit/…WAR_ROOM | 2026-10-11 (daily pushes) | XGB 5-outcome + BIP, Polars; notebook has **no executed outputs / no metrics** | fitted per-type movement change; webapp scales Magnus+drag by ρ(park)/ρ(thrown) with standard atmosphere; hand-set 0.75 factor elsewhere | **React + Vite + TS**: Mexico map of 20 parks, catcher's-view strike zone (sea level vs park), movement arrows, bullpen mascot, ES/EN | 3 servers (fragile deploy), no reported metric, Harp Helú 2,232 m (we cite ours), Location+/Pitching+ not in app |
| noelBanda/Hackathon-Diablos | 2026-10-06 | count baseline only | — | — | early stage |
| paooCaar/Hackathon_DiablosRojos | 2026-10-15 | initial commit | — | — | late start; re-check 10-20 and 10-22 |

Takeaways: (1) lead with an honest leak audit (raw vs location-netted VAA) — "lower AUC, more honest"; (2) beat WAR_ROOM's
physics with fitted C_L(S)/C_D(Re), elasticity with CIs and a ρ slider; (3) one static site (no servers) with a 3D
simulator beats their 2D app; (4) three Stuff+ flavours side by side; (5) be ready for named finals data (roster drop-in).

## Literature → upgrades

| Upgrade | Source | Task |
|---|---|---|
| C_L depends on spin parameter S (SHS fit: 1.5S below 0.1; ≈0.09+0.6S above), not on Re; C_D has drag-crisis regimes near game Re, lower ρ lowers Re ~18 % | Nathan, Hopkins, Chong, Kaczmarski 2006 (arXiv physics/0605041); Smith & Sciacchitano 2022 (Appl. Sci. 12:1416) | HACK-041 |
| Per-game ρ from drag over the flight (our method has a published derivation) | Kagan & Nathan 2014, Phys. Teach. 52:278 | HACK-041, paper |
| Seam-shifted wake = force beyond Magnus; may explain the spin-efficiency gap | baseballaero.com "Cliff Notes: SSW" (2020) — hypothesis | HACK-041 |
| Realised altitude offense < physics-only prediction | Zaidins, Chambers, Page 2003 (SABR) | paper caveat |
| Zero-mean-per-count xRV removes the count from Stuff | PitchingBot primer (FanGraphs Library) | HACK-052 |
| Judge Stuff at pitcher level (reliability, next-year predictiveness, stabilization) | BP StuffPro/PitchPro 2024; FanGraphs Stuff+ primer (McGrattan 2023) | HACK-057, paper |
| Relative features (vs primary FB by batter hand, residual VAA/HAA) | Driveline "Revisiting Stuff+" 2024; Shape+ v2 (FanGraphs Community) | HACK-054 |
| Boosted-tree probabilities need calibration (Platt/isotonic/temperature) | Niculescu-Mizil & Caruana 2005 (ICML); Guo et al. 2017 (ICML) | HACK-053 |
| Conformal intervals valid under covariate shift (weighted) | Tibshirani, Barber, Candès, Ramdas 2019 (NeurIPS); Angelopoulos & Bates 2021 | HACK-055 |
| Importance-weighted validation under covariate shift | Shimodaira 2000 (JSPI) | HACK-055 |
| Empirical-Bayes shrinkage for small samples | Brown 2008 (Ann. Appl. Stat.) | already in leaderboards; cite |
| Altitude as a feature (aStuff+ v2) as an A/B row | Salorio 2025 (Substack) | HACK-052 ablation |

No peer-reviewed LMB / Mexico City park-factor study was found: cite our own data for LMB claims.
