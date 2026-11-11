# Default-visible ship and optional learning integration

## Release basis and cause

This update starts from public MARIS v23, Site source `d0d0cab8362df083a5884996ce555d1222508758`, corresponding to the saved-evidence HUD in GitHub PR #116. The vessel was not deleted. That HUD layout placed it in a default-closed disclosure below the evidence panel. Opening the disclosure on the live v23 page showed the original vessel.

## Changes

- Restore the explanatory vessel as a default-visible panel before the saved-evidence HUD. On narrow screens the order is vessel, mission controls, then HUD.
- Keep the actual experiment records separate from the explanatory model. No target/scan overlay or inference is introduced.
- Guard zero-size renderer hosts and skip drawing/updating while the vessel is off-screen or the document is hidden. Existing low-power, compact pixel-ratio and frame-rate limits remain.
- Integrate optional bilingual evidence-interpretation learning with diagnostic choices, concept guidance, three scenarios, gated predictions, explanations, follow-up checks and explicit opt-in device storage.
- Learning content uses synthetic examples and pinned public aggregates. It does not claim learning efficacy, mastery, independent verification, or new model inference.
- Preserve all existing public assets and evidence. Keep external Stage B FAIL, generation cause UNRESOLVED, and the limited meaning of 4/4 matrix cells and 10/10 same-array label pairs.
- Replace the two old layout hash pins with explicitly labeled restoration pins. The other 22 public/HUD files remain locked unchanged. The old disclosure assertion is replaced by KO/EN rendered default-visibility and ordering assertions, not removed without replacement.

## Verification

Passed on the merged candidate:

- Full UI suite, including 16 mission paths, 352 paired-review renders, 64 HUD renders and default-visible model ordering.
- Learning: 27 diagnostic paths, 718 transitions, 294 bilingual renders, 23 malformed-record rejections, 7 injected storage contracts and complete Home KO/EN integration.
- TypeScript and lint: no errors; one existing image-comparison Next image warning.
- Full evidence suite in a separate complete research checkout carrying the exact merged web source. This includes matched-follow-up and Python audit fixtures that need the research tree. The standalone hosting checkout alone cannot run those repository-relative checks.
- Research source verifier: 8 FGSM conditions, 16 defense conditions and 4 sample cards. No model execution.
- Production build and whitespace checks.
- Actual cloud Chromium desktop: default-visible ship, sea/CAD switch, hull selection, zoom/reset, mission gated reveal/reset, and bilingual learning open/close with focus restoration.
- Actual cloud Chromium 360px/390px iframe viewports: full ship visible, sea/CAD and KO/EN layouts without horizontal overflow. Mobile learning keyboard-open, skip diagnostic, scenario gate, direct explanation and close-focus return passed.

Limits: the cloud browser selected the existing SVG fallback because WebGL was unavailable. These checks validate that fallback and the rendered UI; they do not certify physical mobile hardware, GPU WebGL rendering, performance benchmarks, or full accessibility compliance. Browser extension metadata errors were distinct from application behavior. The existing SSR chart-size warning and build chunk-size warning remain.

The packaged runtime must exclude local QA harnesses, source ZIPs, private model/data artifacts and review logs. Preserve the Site's existing public audience. GitHub PR #116 remains a separate repository review; this Site update does not claim a GitHub merge.
