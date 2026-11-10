# Pixel sandbox v1

Base: deployed MARIS v24, source ccbc2b5843d831b350cbd4e7c796e48914bb1265.

The standalone laboratory captures the existing illustrative 3D model at 256×144 or starts with generated 2D shapes. It applies deterministic, bounded 8-bit RGB noise, optionally a 3×3 edge-clamped mean filter, and computes actual input/output L-infinity, MAE and changed-pixel fraction. The difference map shows the maximum absolute RGB difference at each pixel, amplified eightfold and clipped for display. All frames stay in memory on the visitor's device. No uploads, persistence or new API calls are added.

This is not model inference, FGSM, Grad-CAM or XAI. No classifier score or attack success rate is generated. The capture resolution is a pixel-demo choice, not CNN/MobileNet preprocessing. Existing saved scores, images, 781-image denominators, external FAIL and UNRESOLVED remain unchanged. The mean-filter output may exceed the pre-filter noise bound, and this is labeled separately.

Validation:
- Pixel unit tests: epsilon-zero identity, deterministic seeds, 24 epsilon/seed norm bounds, alpha preservation, immutable inputs, edge handling, invalid input rejection and exact identity metrics.
- Real component event handlers: capture success/failure, stale capture ignored after reset, unmount cancellation, controls and reset.
- Full evidence suite passed in an isolated copy of the parent repository, including public source hashes and Python saved-evidence audits. The standalone Site checkout cannot run repository-root audit scripts by itself.
- Full UI suite, Korean/English SSR, type check, full lint and production build passed. The initial lint scan exhausted its heap while scanning generated runtime caches; after adding standard ignores for .sites-runtime, .wrangler and .vinext, full lint passed with one existing image warning. Existing 22 public/HUD file pins unchanged. After removing the explicit capture adapter and reconstructing the extracted scene-sync block, the old 3D source exactly matches the v24 pin; no pin or assertion was relaxed.
- Actual Chrome: SVG fallback capture succeeded; changing to the deck camera and recapturing visibly changed input; epsilon zero gave identical input/output, zero metrics and a black difference map; filtering changed measured values; seed, reset and Korean/English controls worked.
- GPU WebGL is unavailable in this cloud browser. The actual WebGL capture branch, physical mobile hardware and performance benchmarks were not tested. Existing chart SSR warnings and bundle-size warnings remain.

Rollback: deploy saved v24. This change does not alter databases, access policy, data records or the original research repository.
