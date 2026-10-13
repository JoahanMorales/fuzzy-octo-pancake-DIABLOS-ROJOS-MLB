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
