# DECISIONS

Coordination decisions on the claims branch.
Why: a reversible option after 15 min keeps work moving.
- 1791869129 | HACK-001 | smoke-project via init-smoke resolves the shared venv python | Why: python3 is the Store stub on Windows
- 1791869565 | HACK-002 | drop rows w/o pitcher id (2,956) | Why: cannot attribute or group them
- 1791870012 | HACK-030 | RE by outs x count with observed future runs (no base state in data) | Why: RE24 impossible without runners
- 1791870453 | HACK-013 | EB k from within/between variance | Why: small samples (relievers) must not look elite
- 1791871406 | HACK-005 | skill = % RMSE/logloss reduction, pitcher-cluster bootstrap | Why: pitches of one pitcher are not independent
- 1791873055 | HACK-031 | ship as plumbing; move Stuff+ target to rv_x | Why: rv noise: best iters 25-66, skill +0.02%
- 1791873324 | HACK-004 | empirical rho relative to No-Altitude games; RHO_HARP_HELU barometric until HACK-003 | Why: no HACK-003 yet
- 1791873359 | HACK-029 | rule-based shapes on sea-level-translated movement | Why: interpretable thresholds from real quantiles
- 1791873630 | deadline lease/HACK-003/1791873191 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791873839 | HACK-003 | Draft PR, no uak done: task incomplete. Row-level maps never committed, rebuilt by load_maps() | Why: Avoid review/merge of a partial task and the raw-data rule
- 1791874055 | HACK-006 | trajectory axes X=toward plate; tunnel_ratio=plate_sep/decision_sep | Why: verified vs y0/PlateLoc
- 1791898637 | deadline lease/HACK-003/1791877608 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-004/1791887724 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-005/1791885806 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-006/1791888455 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-013/1791884853 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-029/1791887759 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-030/1791887764 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791898637 | deadline lease/HACK-031/1791887455 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791899057 | HACK-007 | implement brief direction only; lock left to human | Why: needs luis pick
- 1791900367 | HACK-003 | ship via uak done after HACK-030 landed on main | Why: last pending criterion was unblocked
- 1791902448 | HACK-004 | k proportional for ivb/hb/speed_drop, additive plate_velo | Why: joahan-1 reject 16abfbb
- 1791902998 | HACK-010 | component xRV (5 outcomes x LMB values + contact) instead of direct rv regression | Why: direct regression on rv ~ noise; components stabilize 0.80
- 1791907732 | HACK-009 | bootstrap por pitcher sobre tabla agregada; verdict fijado antes de datos | Why: advisor plan lock
- 1791919410 | deadline lease/HACK-007/1791913457 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791919410 | deadline lease/HACK-010/1791918944 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1791920233 | HACK-026 | Keep reports exploratory/transductive; fixed diagnostic blend only | Why: Shared preparation uses global target and feature statistics; official parquet absent
