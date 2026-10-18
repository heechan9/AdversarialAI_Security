# MARIS Sites reconciliation — 2026-10-18

Candidate base: GitHub merged main `020ab55c5a119854e6e5453b78789c7fe9c18c85`, tree identical to tested PR83 head `38d8861b8e4ede256016152b1e0ce5dcce634c76`.

Sites source baseline: `c62cdf8ceacc3017fb3999804918149dad1ca6f1` (public v13). The source contains an Oct 12 research-progress table not present in GitHub main. Replacing the whole page would remove live research content.

Applied the 19 web paths changed by PR83 and its lint correction. Added the already-audited verification-status JSON required by the new panel. Preserved Sites-only VALIDATION.md and hosting configuration. No original image, data.json, defense evidence or provenance bytes changed.

Preserved the existing Oct 12 CNN/PGD/Square appendix with unchanged numeric cells, attack budgets, evidence links, incomplete GPU/PR78 status and VLM/LLM limitations. Added English translations and a prominent historical-status qualifier; no new experimental results or current completion claims. Kept the new dataset-duplication warning and September rerun panel from main.

Deployment source is therefore main plus this preservation patch, not byte-identical main. Extra source files versus main: app/page.tsx, lib/page-locale-en.ts, scripts/test-localization.cjs and this reconciliation record; pre-existing Sites-only VALIDATION.md is preserved. Sync this preservation patch back to GitHub in a subsequent scoped commit/PR to eliminate undocumented drift.

Regression coverage checks all eight original numeric cells and the three evidence URLs in both languages, with dictionary completeness, no English Hangul leakage and unchanged section order. Publishing follows only after full lint, typecheck, localization, evidence and build gates pass and an independent preservation/translation review.
