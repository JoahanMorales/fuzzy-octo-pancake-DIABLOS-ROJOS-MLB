# HACK-043
ID: HACK-043
State: REVIEW
Owner: luis-1
Branch: feat/hack-043
Worktree: /Users/FerV/Documents/HackDiablos/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB-wt/hack-043
Worklog: worklog/WL-1792206149-luis-1-HACK-043-hack.zIqwdO.md
Priority: P0
Paths: web/src/features/landing/
Depends: HACK-037
Verify: `npm --prefix web test -- --run src/features/landing`
Lease-Until: 1792280288
Updated: 1792265888
Task-Base: 7b8f70c2aed60cc65d847234fdda361ea163c1a6
Next: Wait for review of SHA 97b299a
PR: https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB/pull/54
Evidence: npm --prefix web test -- --run src/features/landing exit 0 (6); npm --prefix web run build exit 0; Lighthouse desktop performance 96 accessibility 96; hero CTA abre /simulador
Events: 9
Checkpoints: 2
Sessions: 3
Last-Checkpoint: 1792264390
Task-Tip: 97b299a63c819bb7a63e170dcb4ec7a378af0ee7
