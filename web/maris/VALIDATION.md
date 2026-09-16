# MARIS validation

Research source: heechan9/AdversarialAI_Security, main
`ecce270eafabc5753888dfc5aeddec44a335d999`.

This independent presentation does not modify the research repository, run inference,
generate attacks, promote provisional results, or claim downstream maritime safety.

## Data

- Reused `adversarial_ai.audit.runner.run_full_audit` before exporting the snapshot.
- Research Evidence Audit PASSED; Paper Claim Audit PASSED (8/8).
- Research checkout pytest directly rerun: 86 passed, 4 skipped. Raw image files,
  model binaries and TensorFlow are unavailable here; no claim of local binary verification.
- Export: 781 samples, 2 models, 4 recorded epsilons, 8 aggregate rows; class counts
  derive from the corresponding canonical per-sample CSVs.
- Four committed comparison PNGs copied byte-for-byte. CSS displays their normal,
  attack and normalized-absolute-difference panels; no synthetic research imagery.
- PNG filename indexes follow `_run_epsilon` global sample indexing and were bound
  to the same ordered Clean/FGSM path, label and attack-success records.
- Images are rendered experiment plots, not raw full-resolution dataset originals.
- Clean scores come from canonical predicted-class probability columns. FGSM
  per-sample scores are absent and shown as unavailable.
- SHA-256 provenance and six rejected mutation cases checked by
  `node scripts/test-evidence.mjs`.

## Browser QA

- Desktop page, first action, all four sample selections, normal/attack/side-by-side
  and amplified-difference views checked.
- Mobile layout checked in a 390px iframe viewport (375px content width after
  scrollbar); no horizontal document overflow. Sample selection, difference view
  and model/epsilon results operated inside that viewport.
- MobileNetV2 epsilon 0.01: 97/781 robust correct and 516/613 ASR; epsilon 0:
  613/781 and zero successes. Class-specific Sailboat denominator and all eight
  model/epsilon table rows compared to exported evidence.
- Mobile CNN epsilon 0.05: 158/781 robust correct and 347/504 ASR.
- Malformed temporary snapshot rejected: error message, zero metric panels, retry
  restored data. Missing temporary PNG displayed an image-error message without
  replacing it with invented imagery. Original snapshot restored byte-for-byte.
- Pause/resume and camera reset controls checked.
- Browser environment has WebGL disabled. The same scene geometry and camera were
  rendered and inspected using Three.js SVGRenderer fallback. WebGL shader rendering
  on a GPU and physical-device performance remain unverified.
- Temporary QA wrapper and malformed data excluded from delivery.

TypeScript and production build checked. No live prediction, external service key,
upload, account form, defense experiment, interpolated result or navigation control.

## Direct-interaction update (2026-09-12)

- Fetched research `origin/main` again: unchanged at the source SHA above. The
  read-only research worktree has no modifications. No new tracked comparison PNG,
  raw normal/adversarial arrays or checkpoints were available.
- Reused Three.js geometry and installed OrbitControls on a bounded viewport.
  Browser mouse drag changed geometry projection; wheel changed the visible zoom;
  reset returned zoom to 1.0×. Auto rotation changed the view, manual interaction
  switched its pressed state off, and the explicit on/off buttons worked.
- `node scripts/test-interactions.mjs` exercises the actual installed OrbitControls
  with synthetic PointerEvents on a 390×275 event surface: one-touch rotation,
  start-event auto-stop, immediate reset during damping, two-touch pinch, min/max
  camera distance and fixed target. Thirty shared-image viewport boundary cases
  passed. This is a logic harness, not browser touch emulation or physical phone QA.
- Browser image zoom to 2× and drag yielded identical transforms for both panels;
  the same transform survived attack/difference tab changes. Reset restored 1×/center.
  All four cases were selected; two flipped predictions and two retained predictions
  matched the evidence. No attack confidence was invented.
- Mobile layout: 390px iframe (375px content with scrollbar), no horizontal document
  overflow. Normal scrolling worked outside the ship region; only the ship region
  has touch-action:none, and image panning locks touch only while zoomed. Mobile case
  selection, synchronized 1.5× zoom, attack tab, reset and result selection worked.
- Aggregate/case mismatch and explicit align control verified. MobileNetV2 ε=.01:
  97/781 robust correct, 516/613 ASR. Sailboat for that condition: 1/74 robust correct,
  22/23 ASR. Mobile CNN ε=.05: 158/781 robust correct, 347/504 ASR. All values came
  from the existing snapshot; no independent numeric answer was added to product code.
- Both chart containers rendered at mobile width: 8 accuracy bars, 6 nonzero ASR
  bars (the two epsilon-zero ASRs are zero). Charts cover both models and recorded
  epsilons; class filter applies, with scope text separate from the single-condition
  cards. No interpolation or model output simulation.
- Invalid temporary data schema produced an alert and zero metric panels. Invalid
  temporary image produced an error for the thumbnail and both panels, with no
  substitute imagery. Restored data and PNG bytes; all four original PNG hashes,
  snapshot hash and six rejected evidence mutations passed again. Temporary QA
  wrapper is excluded from delivery. Normal images loaded again after restoration.
- Verified render path: Chrome with WebGL unavailable, using SVGRenderer fallback.
  GPU/WebGL shader output, Safari/iOS, Android, real one-finger/pinch gestures and
  device performance remain unverified. The managed browser occasionally timed out
  after scrolling; subsequent DOM confirmed the scroll occurred. No claim that
  this proves native touchscreen behavior. No production-URL browser QA is possible
  in this environment; local source QA and the hosting deployment status are separate.
- TypeScript and production build passed. Dependency manifest/lockfile, evidence
  snapshot, provenance and PNGs remain byte-identical to the prior version.

## Presence and readability refinement (2026-09-12)

- Closer initial camera and broader deck angle; existing zoom/polar limits and
  reset behavior retained. Desktop and 390px iframe screenshots show the complete
  initial ship. Mobile zoom and reset to the new default (1.0×) operated successfully.
- Main explanatory copy is 16px, #c5d7e2, line-height 1.85; secondary metadata is
  14px. Browser computed styles confirmed 16px / 29.6px on the model scope note.
- Technical expansion guidance moved into an initially closed, keyboard-accessible
  Radix accordion. Desktop click-open / Enter-close and mobile open/close worked.
  Mobile content width and scroll width both 375px, including expanded guidance.
- Existing evidence/hash/mutation checks and interaction harness passed. No new
  research data, claims, dependencies, or experimental results were introduced.
  Browser render path remains SVGRenderer; physical phones and GPU output are not
  newly verified. Temporary mobile wrapper removed before the production build.


## Exhibition finish — 2026-09-12

- Hero asks “같은 선박, 왜 AI의 판단은 달라질까?” and explicitly directs visitors from the explanatory model to recorded image comparisons. The closer camera, orbit bounds, explanatory copy contrast, and initially collapsed research/data accordion are retained.
- Coated-steel hull, matte deck, beveled deck rim, batched panel/tie-down lines, warmer key light and cool rim light refine the scene. No model movement depends on selected attacks or results.
- WebGL path: one cached 512/1024 shadow map on the static ship; view-dependent water highlights and static contact shading. No textures, HDR, postprocessing, or dependencies added. Water mesh reduces from 72,200 triangles to 8,192 on compact screens / 18,432 otherwise. Compact pixel ratio is capped at 1.25 and rendering at about 30 fps; idle scene still renders on demand. Actual GPU performance is not measured. Shadow resources are disposed on unmount.
- `node scripts/test-evidence.mjs`: PASS (snapshot hash, four original PNG hashes, valid evidence, six invalid mutations rejected). No files under public/evidence, data contracts, result arrays, models, or checkpoints changed.
- `node scripts/test-interactions.mjs`: PASS (installed OrbitControls synthetic touch rotation, auto-stop, two-touch pinch, limits, reset during inertia, fixed target, 30 image viewport boundary cases). Synthetic input is not physical-device testing.
- TypeScript check and production build: PASS.
- Browser preview: desktop drag stopped auto rotation; wheel input changed 1.0× to 1.1×; reset restored 1.0×. The wheel automation call reported a transport timeout although the resulting zoom was observed. No claim is made about wheel smoothness.
- Desktop comparisons: CASE 01 CNN aircraft carrier → pleasure craft; CASE 02 MobileNetV2 aircraft carrier → car carrier; CASE 03/04 each kept aircraft carrier. All four original PNG cases remain at ε=0.03.
- Desktop shared zoom/pan produced identical transforms on both panels; attack tab retained the view; difference tab retained its existing explanatory boundary.
- Local iframe layout checks at 390 px and 320 px (content widths 375/305 px due desktop scrollbars): no document horizontal overflow. On the 320 px layout, all four ship-control buttons fit within the content width and were 44 px tall. Graph tick labels, legends, buttons and metric cards were inspected visually.
- Small-layout mouse input: ship drag, zoom and reset; paired image zoom/pan, all four tabs and image reset. Both images retained exactly matching transforms; reset restored scale 1 and zero translation. Outside-scene wheel input advanced page scroll. The scroll tool timed out, so native touch scrolling / momentum is NOT verified.
- Research/data accordion started closed and opened/closed correctly. Whole-results selection kept separate case conditions. MobileNetV2 ε=0 showed identical clean/attack results and zero ASR; ε=0.03 and CNN results matched the unchanged snapshot.
- Browser used SVGRenderer fallback. Real WebGL shader compilation, water appearance, shadow rendering, context-loss behavior after these edits, physical Android/iOS touch gestures, GPU frame rate, and mobile Safari have NOT been tested. They require actual device review.
- `DEMO_GUIDE.md` supplies an approximately 80-second Korean walkthrough using both success and failure cases; it reads current values from the interface rather than maintaining another set of metric answers.
- Temporary mobile QA wrapper removed before production build.


## Model study update — 2026-09-16

- Added perimeter-following railings, mooring fittings, service hatches, bridge platform and steps. Static explanatory geometry only; no selected-case or attack-dependent motion. Improved coated hull material and lighting exposure; retained bounded pixel ratio, cached shadows and existing water shader.
- Added bow, side and deck camera presets. Presets stop auto rotation; reset returns to the initial camera. Initial framing now fits the hull on narrow screens. Framed stage, contrast, focus rings and mobile controls refined.
- Evidence snapshot, four comparison PNGs and Gaussian data are byte-identical to the previous publication. Mean-filter results were not supplied and are not included.
- Evidence/hash/mutation checks PASS. Installed OrbitControls synthetic rotation/pinch/reset/limits checks PASS, including nine new preset/aspect/reset combinations. These are not physical-device tests.
- Browser preview: three preset buttons, auto-rotation stop on preset, zoom (1.2x), reset, paired image zoom (matching 1.5x transforms), success/failure case selection, and MobileNetV2 epsilon-zero statistics verified. At 390px iframe width, content/scroll widths were both 375px; mobile preset/reset controls were usable and hull framing was corrected after inspection.
- Browser used SVGRenderer fallback. Actual WebGL water/shadow appearance, physical phone touch gestures and GPU performance are unverified. No navigation, sensor or collision simulation is claimed.
