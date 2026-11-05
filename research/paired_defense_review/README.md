# Paired FGSM defense review (descriptive saved evidence)

Source data: main `9507e14a551fc697d9466e3257a1249d4579dc3d`.
This additive research slice does not train models, alter predictions, change the paper, resolve independent reproduction discrepancies, or certify robustness.

## Reproduce from repository root

```
python -m unittest discover -s research/paired_defense_review -v
python -O -m unittest discover -s research/paired_defense_review -v
python research/paired_defense_review/paired_defense_review.py /tmp/new-paired-report.json
```

Output uses exclusive creation; choose a new output path. `source_pin.json` pins the 24 existing prediction CSVs, class map and 781-image manifest by Git blob hash. Input CSVs are reused from the repository, not duplicated. `paired-defense-results.json` is the exact generated report, also used by the MARIS panel.

## Scope and interpretation

- Two models × four epsilons × two filters = 16 conditions, 160 class groups, always the same 781 image identities. Never pool repeated conditions as independent images.
- Pair normalized paths and verify manifest coverage/truth, baseline predictions, valid classes, finite epsilon/perturbation bounds and epsilon-zero identities.
- Report wrong→correct and correct→wrong transitions for clean→filtered clean, attack→transfer+filter, attack→adaptive+filter, and transfer→adaptive.
- Own-clean ASRs retain their separate denominators and are explicitly not paired. The additional common-clean-correct subset uses a shared denominator, is selected, and does not represent the full test population. Zero denominator is null.
- Scene/vessel/session independent units are unverified: McNemar p and bootstrap CI are withheld (null), not zero. Image hashes do not prove independent sampling.
- Adaptive attacks are newly constructed against the filter. The comparison is not a causal defense effect under identical perturbations.

Example: CNN Gaussian epsilon .03, transfer comparison gains 128 and loses 47 images; adaptive comparison gains 36 and loses 128. Transfer→adaptive gains 3 and loses 176. These are descriptions of stored outcomes, not new performance improvements.

## Web integration and checks

The additive panel follows the existing model/filter/epsilon controls, permits class selection, shows common-subset denominators and null inference, and reuses the existing worst-class artifact while preserving every tie. Worst-class results are explicitly unfiltered baseline results. Existing verification cards and external reproduction FAIL remain unchanged.

Local checks: 14 Python tests in normal and optimized modes; 352 KO/EN SSR condition/class cases; existing web evidence and UI suites; typecheck; lint (zero errors, one pre-existing img warning); production build. CI now executes the Python slice as well as the existing web workflow.

The clean web checkout requires `.openai/hosting.json`. Existing CI intentionally creates `{d1:null,r2:null}` for compilation only. Local build used the same nondeployable fixture. No live site binding, preview deployment, browser visual QA or independent model inference is established by these checks. Do not deploy the null-binding fixture. Draft PR only; no merge or deployment.

The analysis applies paired comparison, stratification and traceability principles. It does not transplant semiconductor Cp/Cpk or assume that statistical significance proves causation. No lecture PDF, private images, model binaries or submitted paper is included.
