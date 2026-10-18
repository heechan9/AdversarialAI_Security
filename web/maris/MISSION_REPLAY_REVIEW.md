# MARIS recorded-evidence mission candidate

Date: 2026-10-18 KST. Unpublished candidate, based on main
`06b5fa7a56d99c3554cd0c18216e349af24990f4` (merged PR #84).
The existing public site remains v14.

## User-visible changes

The opening section now has a playable recorded-evidence loop:

1. Select one of the four existing aircraft-carrier cases. The mission selector
   does not reveal the attack outcome in advance.
2. Choose the clean control or that case's recorded FGSM epsilon (0.03).
3. Predict whether the model's class will stay the same or change. The reveal
   action is disabled until a prediction is selected.
4. Reveal the actual stored prediction and original input/attack panels. Feedback
   says whether the player's prediction matched the stored record. Replay/reset
   and the detailed evidence comparison are available immediately.

The scene has a state-dependent reticle, an illustrative scan when an attack
condition is armed, a real selected-image thumbnail, and a changed outcome card.
These overlays do not require WebGL. The procedural vessel and its CAD/camera
controls are unchanged. Reduced-motion mode removes scan/reveal animation.

Case changes clear mission state without remounting the ship renderer. Back,
reset, and repeated reveal actions do not generate or change evidence. Keyboard
focus moves to the mission controls when a step changes. KO/EN selection does not
reset a mission. The layout includes narrow-screen rules and touch-sized primary
controls; actual browser/mobile interaction remains unverified in this candidate.

## Scientific boundaries

- The four published image cases support only their clean input and recorded
  epsilon 0.03 prediction. Aggregate epsilon 0.01 and 0.05 rows are not reused as
  individual predictions. Unsupported individual epsilon values are rejected.
- A player's matched prediction is UI feedback, not an AI robustness score.
- The optional post-reveal filter panel is explicitly a separate 781-image
  aggregate evaluation. It includes the model, epsilon, filter and correct-count
  denominator for each displayed accuracy. It never presents a defended outcome
  for the selected image.
- The defense-aware attack is identified as a separately generated attack that
  knows about the filter. Clean accuracy cost is also shown.
- No new inference, source image, synthetic defense image, navigation/collision
  simulation, attack footprint or real-world safety result is produced.
- Original evidence JSON, provenance, images, scientific tables, charts, research
  appendices, status qualifiers and source URLs are preserved.

## Verification performed on candidate source

- `npm run lint`: 0 errors; 1 existing original-PNG warning in image-comparison.tsx.
- `npm run test:ui`: 364 translation literals and placeholder parity; KO/EN server
  rendering; preserved research values/links and section order; original synthetic
  camera/touch/viewport controls; new 16-path case × condition × guess suite.
- New mission suite: reveal gating, repeated reveal, back/reset, unsupported
  epsilon rejection, actual recorded case predictions and separate aggregate
  defense values, with KO/EN server rendering; error/retry and epsilon-zero control
  copy; both Gaussian and mean aggregate branches.
- `npm run test:evidence`: snapshot and all four PNG hashes, six rejected
  mutations, complete defense exports/counts/ASR denominators pass.
- `npx tsc --noEmit`: pass.
- `npm run build`: pass. Existing large-chunk and unknown route-classification
  notices remain.
- Byte comparison against the main-derived baseline: all 11 evidence files,
  entire research body below the opening mission, Ocean renderer, and camera
  controls are unchanged.

These are code/state/SSR/build checks, not browser clicks, physical touch input,
hardware WebGL testing, model inference or independent experimental reproduction.

## Runtime and preview limits

The cloud browser could inspect public v14 but could not open the workspace's
local preview. A normal installed-Chromium test launch failed with a sandbox
socket permission error before a page opened. No denied route was bypassed, no
sandbox escalation was attempted, and the public site was not republished to get
a preview. Consequently no candidate runtime screenshots or successful browser
interaction result are claimed.

The two delivered PNGs are explicitly labeled static layout previews. Their UI
layout is a design rendering, not a screenshot; the vessel is a static SVG export
of the unchanged procedural model and their image panels use the original
recorded PNGs. They communicate the intended first-screen and reveal states.
They cannot establish actual responsive sizing, focus behavior, animation timing,
SVG/WebGL rendering behavior or browser interactions.

Before release, validate all four cases, both clean/attack conditions, both guesses,
repeated/back/reset flows, case changes from the lower evidence selector, KO/EN
changes mid-mission, filter selection, CAD/camera controls, reduced motion,
network failure/retry, keyboard navigation, and narrow layouts in a supported
browser. Verify the exact source commit and CI before publication.

## Contribution provenance

Requirements and direction: 최희찬 (heechan9).
Implementation, source/state tests, and static design preview: Codex.
A second Codex source-only review identified and verified fixes for loading/error
  presentation, epsilon-zero defense wording, offscreen focus on external case
  changes, and the control-to-attack image handoff. Narrow case-label wrapping was
  added. No remaining source blocker was identified in that limited review. This
  is separate from runtime QA and experimental validation.
No new Claude/Jules review, hardware testing, independent model rerun, human code
implementation, commit, merge or deployment is claimed by this candidate.
