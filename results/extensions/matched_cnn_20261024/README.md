# Matched CNN follow-up: one-seed internal evaluation

**한국어 요약:** 정상 추가학습 대비 PGD 혼합학습의 PGD7 정확도는 +7.43%p,
PGD50·5회 재시작 정확도는 +0.90%p였다. 후자는 정답 수 **순증 7장**이다.
단일 seed·CNN 내부 실험이며 전반적 방어 성능, 독립 재현 성공 또는 학술지 게재 수준을 입증하지 않는다.

This extension is separate from the historical paper/ACK result tables and the
October 2 adversarial-training study. Evaluation finished on **October 24, 2026,
04:38:39 KST** (`2026-10-23T19:38:39.220199+00:00`).
Status: `COMPLETED_NOT_INDEPENDENT_APPROVAL`.

## Test results: 781 images per model

| Condition | Original CNN | Clean-only additional training | 50:50 clean/PGD training | Mixed minus clean-only |
|---|---:|---:|---:|---:|
| Clean | 504/781 (64.53%) | 539/781 (69.01%) | 540/781 (69.14%) | +1 net correct; +0.13 pp |
| PGD7, 1 restart | 87/781 (11.14%) | 90/781 (11.52%) | 148/781 (18.95%) | +58 net correct; +7.43 pp |
| PGD50, 5 restarts | 37/781 (4.74%) | 41/781 (5.25%) | 48/781 (6.15%) | +7 net correct; +0.90 pp |

The clean-only arm controls additional training exposure under the recorded
protocol. The PGD7 gain is descriptive evidence for this pair; the smaller PGD50
gain and 6.15% attacked accuracy show substantial remaining vulnerability.
Seven is the **net difference**, not necessarily seven distinct recovered cases
with no losses. The saved auditor reports newly correct and newly incorrect
cases separately. No significance, confidence interval, cross-seed stability,
or general defense-effectiveness claim is made.

For PGD50 specifically, mixed is newly correct on 28 cases and newly incorrect
on 21 cases compared with clean-only: 28−21=7 net correct.

Accuracy uses **all 781 test images**. Own-clean ASR uses each model's initially
correct subset: baseline 504, clean-only 539, mixed 540. The models' ASR
denominators differ. Do not substitute ASR for attacked accuracy.

## Code and executed conditions

- Training, attack implementation and pair auditor: pinned
  [`db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf`](https://github.com/heechan9/AdversarialAI_Security/tree/db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf),
  from unmerged Draft [#87](https://github.com/heechan9/AdversarialAI_Security/pull/87).
  [Training source](https://github.com/heechan9/AdversarialAI_Security/blob/db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf/src/adversarial_ai/training/adversarial_training.py),
  [PGD implementation](https://github.com/heechan9/AdversarialAI_Security/blob/db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf/src/adversarial_ai/attacks/iterative.py),
  [pair auditor](https://github.com/heechan9/AdversarialAI_Security/blob/db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf/verification/training_control_audit.py).
- Exact executed evaluator: [executed-evaluator-v2.py](provenance/executed-evaluator-v2.py),
  SHA-256 `38f96878ed8a41bf3a1833b50db1c47f4b935dcc91c0173ba4b9e575e4e58b8f`.
- CNN, 128×128 RGB, rescaled to [0,1], 10 classes, no preprocessing defense.
  The canonical [test manifest](../../../configs/test_manifest.json) has SHA-256
  `36059fea372334509404aca0e66155bf99a8df270beb1cc3bf4865b361ae70a6`.
- Training seed **2026**, train 6,147 / validation 689 / test 781. Both arms
  start from the same original CNN; Adam, learning rate 1e-5, batch 8, 3 epochs.
  Clean loss weight is 1.0 for clean-only and 0.5 for mixed training.
  PGD training uses L∞ ε=.03, step=.005, 7 steps, 1 restart.
- Both arms select the highest validation PGD accuracy, with earliest epoch
  winning ties. Clean-only selects epoch 1; mixed selects epoch 3. Equal epochs
  and image order do not equalize computation or stochastic trajectories.
- Test attacks use each evaluated model's own gradients: untargeted L∞ PGD,
  ε=.03, step=.005; PGD7 is 7 steps/1 restart, PGD50 is 50 steps/5 restarts.
  Evaluation seed is **2026 plus zero-based batch index**, modulo 2³¹, batch 8,
  shuffle=False. The implementation uses random starts and retains successful
  adversarial candidates per image; this is neither AutoAttack nor a certificate.
- Colab Tesla T4, Python 3.13.16 / TensorFlow 2.21.0 / Keras 3.15.1 /
  NumPy 2.3.5. [Package freeze](provenance/environment.txt) and
  [GPU/driver snapshot](provenance/nvidia-smi.txt) are preserved. The driver's
  displayed CUDA version is not an assertion about every loaded CUDA library.
  Deterministic ops and oneDNN controls were unset; recorded numerical variables
  appear in each training JSON. Bitwise replay is not established.
- Actual [clean-only command](provenance/clean_only-command.json),
  [mixed command](provenance/pgd_mixed-command.json),
  [evaluation command](provenance/test-evaluation-v2-command.json), and
  [evaluation log](provenance/test-evaluation-v2.log) are retained.
  `/content/...` paths describe the original Colab session; they are not portable
  commands or public input downloads. New inference requires authorized private
  model/data bytes, the pinned checkout, a compatible GPU environment and fresh
  output paths. This review does not start training or inference.

## Test values and validation values are different records

| Selected checkpoint | Validation images | Validation clean | Validation PGD7 | Test clean | Test PGD7 |
|---|---:|---:|---:|---:|---:|
| Clean-only, epoch 1 | 689 | 93.18% | 20.75% | 69.01% | 11.52% |
| Mixed, epoch 3 | 689 | 90.13% | 31.35% | 69.14% | 18.95% |

Validation values in [training-clean_only.json](provenance/training-clean_only.json)
and [training-pgd_mixed.json](provenance/training-pgd_mixed.json) selected the
checkpoint. Test values above come from the three test CSVs only. The
validation/test gap is not explained away by this audit.

## Identity chain and completion-state interpretation

[evidence-index.json](evidence-index.json) maps retained original bytes to their
Drive file IDs and SHA-256 values. Source files were read from the
[evaluation folder](https://drive.google.com/drive/folders/1xSh-avapuvaRx7XFhSzNGjsgVPI7c3BN)
and its [batch folder](https://drive.google.com/drive/folders/1y5uY3mERidP7zaTVmoliVlFGcbTF7zzS).
These links retain their existing access controls. Raw images and model binaries
are not included in this result package. Test CSV filenames/labels match the
already public canonical manifest; retained logs/commands contain generic
Colab paths, without credentials, signed download URLs or personal home paths.

| Model | Recorded model SHA-256 | Original CSV SHA-256 |
|---|---|---|
| Baseline | `cb256b1a5d6f605d355334e4e8667257a2bfbd29e08836cc4114869bd7068701` | `91a04ab3cb3643639f31b90ad31d5a34a5dfa34be2146063ec13dcce66a035fd` |
| Clean-only | `e3b02315482c432ec5a2b5828696f611ad9f167f847d273d746df8c98677d353` | `d61cb35d7b21e21cbe534d0fa046657a77b7f2fee8a49643f4c74a1dd5256312` |
| PGD-mixed | `38767ddb3eb00463e7324ba4371c184c0eed01a87819b4766a66415d69538708` | `cf1ffaeed43b576e8a15eb3e8adb13cbd8b21b50b79b00b547eff9768a9633e6` |

The pair auditor reported
`PAIRED_RECORDED_PROTOCOL_AND_CHECKPOINTS_CONSISTENT`, with protocol hash
`8dee4bb84261c652c5676288b907c02b3d2fe61b210dbc781b3f05a4ccd56187`.
The two training reports record split-audit SHA-256
`4928cca78137841bc40bd4fd241f250d744c0433d0183b3d6ea912cf8a45b8cb`.
The GPU evaluator invoked the pinned pair audit before inference, then checked
each loaded model hash. This publication review compares those **recorded** model
identities; it does not download/re-hash private model or split-audit files anew.

`evaluation.json.paired_audit.test_evaluation_complete=false` is an unchanged
**pre-inference audit snapshot**, also retained in [paired-audit.json](paired-audit.json).
That auditor checks saved training records/checkpoints and intentionally performs
no test inference. It is not the final evaluator's completion flag. Likewise,
the original training reports retain `TRAINED_NOT_TEST_EVALUATED` because they
were emitted before the separate test stage. Final evaluation completion is
established by the top-level status, all three `samples=781` entries, CSV bytes,
hashes and metric recalculation. No historical JSON fields were rewritten.
`independent_verification_approval` remains **false** at every stage:
no independent approval has been granted.

The first evaluator attempt failed **before model inference** because an absolute
model path was checked against a manifest keyed by a repository-relative path.
Its [script](provenance/executed-evaluator-v1.py) and
[failure log](provenance/test-evaluation.log) are preserved. V2 uses the canonical
relative model path and a fresh output directory. It did not weaken the model
hash requirement. The failed attempt is not counted as a completed test run.

## Three-seed plan versus one completed seed

The [planning snapshot](planning-snapshot.md) proposed training seeds
2026/2027/2028, i.e. six new training runs. The actual first Colab batch was
explicitly limited to `SEEDS=[2026]`, as shown by the
[saved setup-cell extract](provenance/colab-setup-cell.json) and its printed
batch ID `intl_20261023T172139`. Only two training runs and this seed's test
evaluation are completed. Seeds 2027/2028 are **not run**, not failed,
not hidden replications and not implicitly covered by the baseline model.
This was staged first-pair execution; no report establishes a quota failure as
the reason for stopping. Completion refers to this one-seed batch, not the
three-seed study.

The proposal also named evaluation seed **4101** and a validation-side attack
saturation check. Actual evaluation uses **2026+batch**, and no 10/20/50-step
validation saturation sweep is supplied here. This is a documented deviation
from an exploratory draft, not a preregistered confirmatory study. The mixed
PGD7 value here is 18.95%; the historical October 2 run's 18.57% remains separate.

Remaining work:

- Execute both arms for seeds 2027/2028 under a reviewed, fixed protocol; retain
  all failures and outcomes, then report seed-level results and descriptive
  mean/range. Do not tune attacks/training against these observed test results.
- Resolve the proposed-versus-executed evaluation-seed rule and validate attack
  saturation on validation data before the next protocol is frozen. Cross-seed
  comparisons must identify the same evaluation rule, or report deviations.
- Report compute/update/gradient budgets and peak memory systematically. Current
  logs and timestamps are not a complete measured compute-budget study.
- Complete planned class/macro-F1/common-clean-correct analyses as explicitly
  descriptive; matched stronger black-box evaluations and validated AutoAttack
  integration remain separate work. Historical black-box results do not cover
  these newly trained checkpoints automatically.
- Resolve historical baseline exposure and vessel/scene independence; establish
  data rights and an independently held external test before generalization
  claims. Repeatedly viewed historical test data are not a fresh holdout.
- Seek independent model/data replay. Existing external
  [Stage B FAIL](../../../docs/STAGE_B_HYEONSU_01_REVIEW.md), unresolved numerical
  discrepancies, [#78](https://github.com/heechan9/AdversarialAI_Security/pull/78)
  and [#86](https://github.com/heechan9/AdversarialAI_Security/pull/86) remain
  separate and unfinished. This extension neither resolves nor replaces them.

## Read-only public verification

From the repository root, using Python 3.11+ and the standard library:

```bash
python verification/matched_cnn_saved_audit.py
python -O verification/matched_cnn_saved_audit.py
```

The auditor checks retained file hashes, canonical ordered identities/labels,
781 unique rows per model, finite recorded perturbation bounds, all accuracies
and own-clean ASR, recorded checkpoint/protocol linkage, and selected validation
epochs. It reports paired gains/losses without statistical independence claims.
It does not regenerate perturbations, inspect image pixels or authenticate
execution, GPU equivalence, private model bytes or leakage-free generalization.
Hashes bind retained bytes; an accompanying manifest is not an external trust
anchor. A passing saved audit is **not independent experimental reproduction**.

Research direction and execution authorization: 최희찬 (heechan9). Colab setup,
evaluation code, saved-evidence verification and this result documentation:
Codex assistance. Connector commits use the authenticated account; attribution
does not assign new experimental work to historical teammates. Publication here
is a review proposal; merge and paper adoption require review.
