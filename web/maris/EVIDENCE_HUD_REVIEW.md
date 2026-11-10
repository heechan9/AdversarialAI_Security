# PaulGuard saved-evidence HUD review

## Scope

Based on public research main `3ffc32b46002075f78cf7fb57a9b0d8b05b1d99d` (includes PR #115).
The request is a contextual cinematic HUD, not a new AI capability or a film asset reproduction.

- Integrates a saved-record HUD with the existing four-step mission state.
- Shows the selected saved PNG crop, model, available epsilon, baseline/output classes and pinned evidence source.
- Conceals the selected-condition output until explicit reveal. An attack output score stays absent; a clean score is not reused as attack confidence or safety.
- Replaces the animated scan/target overlay on the illustrative vessel. Retains 3D as an optional keyboard-operable disclosure.
- Adds a low-motion responsive layout, preserves existing native controls, and fixes narrow mobile model-name wrapping.
- Public evidence, model/attack code, paper metrics, 4/4 cross-score matrix, 10/10 matching-label-pair meaning and external FAIL/UNRESOLVED remain unchanged.

## Automated validation

Passed on this candidate:

- `pnpm run test:ui`: literal and rendered KO/EN, synthetic controls, 16 full mission paths, 352 paired-defense render cases, plus 64 new HUD render cases.
- `pnpm run test:evidence`: original data/PNG hashes; defense exports; matched follow-up; diagnostics; FGSM run audit; selected fixed-array summary.
- `pnpm exec tsc --noEmit`.
- `pnpm run lint`: no errors; one pre-existing Next image warning in `image-comparison.tsx`.
- `python verification/maris_source_check.py`: PASS, 8 FGSM conditions, 16 defense conditions and 4 saved sample cards. No inference.
- Production build through the existing shell environment wrapper.
- `git diff --check`.

The managed `pnpm run build` entry initially hits a pre-existing non-executable
`scripts/sites-env.sh` (Git mode 100644). Running the same environment/build
scripts explicitly with Bash succeeds: `bash scripts/sites-env.sh -- bash scripts/build-verified.sh`.
No script permissions or dependency versions were changed. Portable CI uses its
normal `pnpm run build` path and must be checked independently for the posted head.

## Browser checks

Actual running local preview, cloud Chromium (not Opera):

- Desktop KO and EN: all four attack cases reveal the saved classes. Missing attack scores remain absent. Reveal is disabled until a guess is chosen.
- Keyboard Enter/Space, clean input, Back, reset and repeated case selection checked. Returning from the prediction step conceals the output. The clean result shows its original score with a non-probability disclaimer.
- 3D disclosure opens/closes without navigating away; the evidence remains separate.
- 390px iframe viewport (375px content after scrollbar): Korean mobile mission/reveal and HUD checked with no horizontal overflow; real mobile device/touch hardware was not used.
- Saved desktop and mobile screenshots are separate review artifacts, not new research evidence.
- Browser logs included extension metadata errors; these were not application inference or UI failures.

KO/EN has automated full render coverage. English mobile visual QA and OS-level
reduced-motion emulation were not completed; reduced-motion CSS is present and
the new HUD has no animation. This is not a complete accessibility certification.

## Publication boundary

This review covers the candidate source and local preview. It does not claim
Git main merge or production publication. Existing production v22/PR #115 is
handled separately; synchronize with that release before applying this candidate.
No private arrays, models, PC paths, logs or unpublished experiment results are included.

Implementation and verification assistance: Codex. Direction: the project owner.
