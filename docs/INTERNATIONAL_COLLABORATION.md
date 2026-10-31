# International research collaboration

**PaulGuard — Maritime AI Security Research** is our public-facing research name. The existing virtual lab remains **MARIS**; historical submission titles, team credits and the repository URL are preserved. This is a documentation-level name, not a new UI, deployed system or verified trademark clearance.

We welcome narrowly scoped collaboration on **independent reproduction** and **additional attack/defense evaluation** for ten-class ship-image classification. This is a research prototype, not an operational ship-protection system. Checked November 1, 2026 against main `2ed69b00faa3dce098a6a78888032746b6b35d43`; this refresh reuses the existing Draft #103 structure. Start with the [English overview](../README.en.md), [preserved source/evidence boundary](PAPER_RELEASE_STATUS.md#preserved-source-and-submission-boundary--2026-10-30) and [reproduction navigation](REPRODUCIBILITY.md#english-reproduction-navigation).

## What is available, and what is not

- Public evaluation/audit source in [src](../src), [verification](../verification), [tests](../tests), versioned [configuration/manifest](../configs), and saved [result artifacts](../results).
- Existing [attack contract](EXPERIMENT_CONTRACT.md), [threat model](THREAT_MODEL.md), [evidence audit](RESEARCH_EVIDENCE_AUDIT.md), and [review procedure](REVIEW_WORKFLOW.md); these remain authoritative rather than being replaced by another protocol.
- Separate extension [one-seed matched-CNN evidence and executed evaluator](../results/extensions/matched_cnn_20261024/README.md), with its own provenance and limitations.
- Original model binaries and the full image dataset are **not distributed in Git**. Access and redistribution require rights checks and explicit owner/team authorization. Public visibility alone is not a redistribution license; do not promise unrestricted code/data reuse or invent a license.

The research-PC LOCAL_PASS does not erase the external FAIL. The discrepancy cause remains unresolved; selected cross-only work is INCOMPLETE. Asset hash agreement without inference must not be presented as independent reproduction. A successful software audit is not independent experimental approval.

## First external review: one saved-result audit, no private assets

**Task:** recompute the October 24 matched-CNN saved evaluation at the pinned
source below. This is the first small task; model reruns are a later, separate agreement.

1. Use an isolated checkout of `2ed69b00faa3dce098a6a78888032746b6b35d43` and
   Python 3.11+; the selected auditor uses only the standard library. Do not load
   TensorFlow, obtain model/image bytes, regenerate a manifest or rerun training.
2. From the repository root, record `git rev-parse HEAD`, `python --version`,
   then run `python verification/matched_cnn_saved_audit.py` with captured
   stdout/stderr and exit code. The optional `python -O` run checks that explicit
   validation remains active; it is still the same saved-record task.
3. Return a short report and stdout: source SHA, environment, exact commands,
   exit code, output SHA-256, three sample counts, clean/PGD7/PGD50 counts,
   own-clean ASR successes/denominators and mixed-minus-clean-only gains/losses.
   Compare with the linked result package; retain any discrepancy rather than
   adjusting tolerances or editing the reference files.

Expected status is `SAVED_EVIDENCE_CONSISTENT_NOT_INDEPENDENT_REPRODUCTION`;
samples are 781 per model. Clean counts are 504/539/540, PGD7 87/90/148,
PGD50 37/41/48, ordered baseline/clean-only/mixed. PGD50 mixed versus clean-only
has 28 newly correct and 21 newly incorrect cases, net 7 (+0.90 percentage points).
`independent_verification_approval` remains false. A nonzero exit or unavailable
checkout is an issue/not-run result, never a forced PASS.

**Access:** public repository files suffice for this bounded review. Their
visibility does not grant a blanket reuse license; preserve notices and confirm
terms before redistribution. No image/model/manuscript transfer or new account
permission is required by this task. We provide pinned source, three saved CSVs,
evaluation/protocol metadata and the auditor. The reviewer returns an artifact
consistency report, not independent experimental approval. No invitation is sent.

## Condition status: historical FGSM and separate follow-ups

The historical FGSM scope is agreed, but its stored `provisional` label and the
filters' `experimental` labels remain. The separate official execution template
still says `pending_team_confirmation`: the official-promotion approval/rerun
record is **not linked**, not inferred complete from agreed epsilon values.

| Evidence family | Completed / partial / not run | Conditions, cohort and authoritative source |
|---|---|---|
| Historical Clean/FGSM and fixed filters | Recorded experiments and saved-record audit complete in scope; external agreement FAIL; separate official promotion unverified | CNN 128×128, MobileNetV2 224×224, RGB /255; untargeted true-label one-step L∞ FGSM, ε=0/.01/.03/.05, clipping [0,1], tolerance 1e-6; Gaussian/mean 3×3, base-attack-then-filter versus defense-aware gradients. Accuracy N=781. Own-clean D: unfiltered CNN/MobileNet 504/613, Gaussian 445/648, mean 419/622. [Contract](EXPERIMENT_CONTRACT.md), [FGSM results](FGSM_PROVISIONAL_RESULTS.md), [filter results](CURRENT_RESEARCH_STATUS.md), [official gate](FGSM_OFFICIALIZATION_RUNBOOK.md). |
| October 2 CNN additional training/PGD7 | Complete only for recorded one-seed CNN condition | Source `76fc5e5debfc02269e236d15db5d06325802379a`; no filter; 6,147/689/781, train seed2026, 3 epochs, PGD ε=.03/step=.005/7 steps/1 restart, eval seed2026+batch, batch8. Original/trained D=504/540. T4, Python3.13, TF2.21.0/Keras3.15.1. [Own records and CSVs](../results/extensions/cnn_adversarial_20261002/README.md). Not the October24 checkpoints. |
| October 3 CNN Square/SurFree | Recorded bounded runs complete; no independent model replay | Original and October2-trained CNN. Square L∞ .03, 200 queries seed2026 or 1000 queries seeds2026/2027/2028; up to3000 for their union. SurFree top-1 L2, 200 queries, seed2026+image index; RMS cutoffs are not L∞ budgets. D=504/540. [Results](../results/extensions/blackbox/README_20261003.md), [environment/query protocol](TRAINED_BLACKBOX.md). These attack seeds are not three training seeds and do not evaluate the October24 mixed checkpoint. |
| October 24 matched CNN control | One seed2026 complete: `COMPLETED_NOT_INDEPENDENT_APPROVAL`; training seeds2027/2028 not run | Baseline/clean-only/50:50mixed, no filter; own-gradient PGD7 r1 and PGD50 r5, ε=.03/step=.005; N=781, D=504/539/540. Clean64.53/69.01/69.14%; PGD7 11.14/11.52/18.95%; PGD50 4.74/5.25/6.15%. Training/evaluation source is Draft #87 `db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf`, not main's current training code. T4/Python3.13.16/TF2.21.0/Keras3.15.1/NumPy2.3.5, batch8, numerical controls unset. [Model/CSV hashes, executed evaluator, commands, environment and validation/test distinction](../results/extensions/matched_cnn_20261024/README.md). |
| Filtered BIM/PGD matrix | Partial/checkpointed/interrupted work; no full-matrix completion | Dated condition counts are snapshots, not live RUNNING status. Preserve #78/#86 and [follow-up execution](FOLLOWUP_EXECUTION_STATUS.md), [closeout](FOLLOWUP_CLOSEOUT_20261004.md). Each recorded condition owns its steps, restarts, runtime and own-clean cohort; do not borrow settings or D from another family. |
| JSMA, MobileNet training, new matched black-box/AutoAttack, independent external holdout | JSMA one-image smoke only, clean-ineligible D=0 (undefined ASR); full JSMA and other named extensions not completed | Code/synthetic tests are not these experiments. Missing results stay not run/unverified; no attack or training is authorized by this guide. [Scope](PROJECT_SCOPE.md), [JSMA checkpoint](FOLLOWUP_EXECUTION_STATUS.md), [remaining matched work](../results/extensions/matched_cnn_20261024/README.md). |

All ASRs condition on that exact pipeline's clean-correct images. Report
successes/D alongside accuracy correct/N, including D=0 as undefined. Different
own-clean cohorts cannot be pooled; a selected common-clean-correct analysis
must be identified separately. PGD50 6.15% is substantial residual vulnerability,
not broad defense validation or a maritime safety guarantee.

## Evidence tiers and unresolved reproduction

The research-PC full rerun is **LOCAL_PASS**, with labels/summary metrics in its
declared matrix; probabilities were excluded. External Stage B originally had
16 differing prediction cells across14 images. Its later Linux oneDNN-off trace
returned11 cells to the reference while five cells acrossfour images remained.
Keep each run's environment and batch context; this is evidence of numerical
sensitivity, not proof that oneDNN alone caused all discrepancies.

Historical evaluation records and [handoff spec](../configs/handoff_spec.json)
pin input/model identities and normalization; [PC record](STAGE_B_PC_FULL_20260928.md)
and [Linux traces](STAGE_B_TENSOR_TRACE.md) own their distinct Windows/Python3.11.15
and Linux/Python3.12.14 settings. Do not upgrade the original environment to seek
agreement. The original first divergent operation remains unknown.

The separately retained October31 P0 selected cross-only experiment applied one
new Linux scorer to the existing PC/Linux inputs: all15 reported labels followed
their native source, while probability vectors were not bit-identical. It is
four images/five items × three input sources, with row99 duplicated across two
filter items; it is not15 independent images or Hyunsu's completed return.
P1's saved gradient-sign/attack-array checks add arithmetic evidence without
new gradients. Neither closes external FAIL or establishes the first cause.
Hyunsu selected cross-only remains **INCOMPLETE**.

P0/P1 and later data diagnostics are separately retained controlled-access
packages, not files already merged into main. The maintainer can supply their
metadata/hashed review packets after scope and access agreement. Hash matching,
saved-output recalculation, actual classifier inference, AI image review and
independent human approval are separate evidence tiers. CI checks only its
declared software/saved-evidence scope.

## Rights, access and missing source lineage

- Public source and saved tables can support the small review above. No top-level
  project-wide LICENSE has been established here; third-party notices keep their
  own scope. Public readability is not unrestricted redistribution permission.
- Full raw images, model weights, private attack arrays, original handoff ZIPs,
  private permission records and submitted manuscripts remain outside this
  proposed public documentation. Do not copy them into Git or an overseas folder.
- P2 linked public-v3 file content and the preserved 6,147/689/781 follow-up packet;
  exact cross-split raw/RGB matches were zero within the prepared packet, while
  test-internal duplicates and related-image candidates remain. P3's27 AI-reviewed
  candidate pairs and20 unapplied proposals have **no human group approval**.
  These diagnostics do not certify vessel/scene-independent generalization.
- The public reference dataset's CC0 label and its linked upstream CC BY4.0
  label do not settle every image's rights or added-image provenance. Whole-dataset
  use/redistribution remains **UNVERIFIED**; no permission is inferred here.
- `train-inventory.json` expected SHA-256:
  `0b9c00bf872344eed8886d6814b5766ada31cfada7f4a19180444b2fe5313320`;
  `train-staged-manifest.json` expected SHA-256:
  `b5783c1f2fd894ad9c8567d60cb7d7df33c821c9e9ab749886aa5907b4cba39c`.
  Their original bytes are not recovered. Do not substitute a reconstructed file
  or claim its hash is the historical one. The8067 source IDs → staged paths/hashes
  mapping and original baseline training exposure remain unverified.
- Dot's current26 candidate files (13 basenames × two Drive IDs) match prepared
  raw/RGB records, but the historical17 excluded `__source_` paths → source IDs
  are still unconfirmed. Dot performed those actual file checks; Claude reviewed
  public sources/recovery strategy. Codex compared delivered metadata with prior
  records; these roles are not interchangeable independent executions.
- The verified380,783,448-byte packet (SHA
  `eeb5b32a97135007145168ffeaec3eedb06e329333c1e310922e177be68b3be9`)
  has7,622 entries; its preparation/split-audit JSONs and nine retained renamed
  images do not contain the missing two manifests or their staging generator.
  The old approximately690MB description may be a different copy or a size error;
  its existence/content and a user's downloaded backup are not established.

The missing manifests prevent full historical source-ID/preparation replay;
they do **not** prevent the public saved-CSV task. Current inference also requires
authorized exact model/image bytes and an agreed runtime; it is a different task.
Do not repeat the26-file collection,27-pair AI review or1,903 public-candidate audit
as new progress. Report a newly discovered original location with its provenance.

## Further contributions after the first public review

1. **Public-record reproduction:** recalculate one saved table or check one claim-to-artifact mapping using a pinned SHA. Return commands, environment, exit codes, differences and scope. No private inputs are needed for saved-record review.
2. **Independent model rerun/diagnosis:** propose a bounded Stage B or selected cross-only task first. Agree access, exact source/input hashes, comparison criteria and output handling before execution. Never obtain or publish private assets through an unapproved route.
3. **Additional evaluation:** propose one attack/defense condition from the [candidate roadmap](PROJECT_SCOPE.md#bounded-international-research-roadmap--2026-10-30), checking existing PRs first. State the threat model, compute requirements, clean baseline, ASR eligibility cohort and a stopping criterion before any new experiment.

## Agree the comparison before asking for a result

Use this compact condition card to reference the existing contracts, not to create
a second source of truth. Fill one card per condition; differences belong in the
comparison, not in an undocumented environment or metric change.

| Field | Record before execution or saved-record review |
|---|---|
| Threat and access | Target checkpoint and classifier; attacker objective, knowledge and access. Historical FGSM is untargeted, white-box, uses true labels/gradients and changes a digital image tensor, not a ship's control system. |
| Input and budget | Full source/manifest/model/class-map hashes, ordered image identities, preprocessing, image size, norm and epsilon **in the actual input scale**. Recorded evaluation uses RGB rescaled by `1./255` to `[0,1]`; CNN is 128×128 and MobileNetV2 is 224×224. Equal epsilon does not remove this resolution difference. This is not proof of MobileNet's unavailable training preprocessing. |
| Attack and defense path | Historical FGSM is one step with epsilon `0, 0.01, 0.03, 0.05`, `[0,1]` clipping and `L-infinity <= epsilon + 1e-6`. Distinguish an attack generated on the base model then filtered from an adaptive attack through the filter. The former is not automatically model-to-model transfer. For separately proposed PGD/black-box work, also fix steps, step size, restarts, seed and query/compute budget; do not pool it with historical FGSM. |
| Outcome and cohort | Clean accuracy and attacked accuracy use all evaluated images, with their correct counts and N. ASR uses attack-induced errors among the **same pipeline's clean-correct** images, with success count and D. Historical unfiltered D is 504 for CNN and 613 for MobileNetV2; filtered or newly trained pipelines can have different D. Report those cohorts, clean cost and newly correct/incorrect cases separately. D=0 means undefined, not 0% ASR. |
| Evidence and decision | Exact source/tool/comparison-run identities; observed vs reported execution, logs, exit codes, completion scope and unchanged tolerances. A hash check, saved-output audit, actual model inference and independent human review are different evidence levels. |

The [experiment contract](EXPERIMENT_CONTRACT.md),
[threat model](THREAT_MODEL.md), [ASR contract](ASR_INPUT_CONTRACT.md),
[handoff specification](../configs/handoff_spec.json) and each extension's pinned
record own the detailed definitions. A new condition needs an agreed scope; this
card authorizes no attack, training, data transfer or expenditure.

## Later private task: reproduce a failed condition, then compare environments

The useful first question is **whether a specified mismatch is reproducible under
the recorded conditions**, not whether PaulGuard can be declared safe. The original
external report had 16 differing prediction cells across 14 unique images;
later diagnostics and the research-PC LOCAL_PASS are separate observations.
Do not describe all 16 cells as still differing in every later environment.

1. Choose one existing failure/selected cross-only item and record the reference
   run, expected/observed result, evaluation SHA, diagnostic-tool SHA and input
   identities. Use the [existing selected handoff](HYUNSU_CROSS_ONLY_HANDOFF_20261026.md),
   not a newly invented full-run command. Confirm authorized local access first.
2. Keep original settings, batch context and tolerances for the first attempt.
   Record a missing-input/preflight stop as such; absent outputs are not prediction
   mismatches. If the failure does not reproduce, retain that result and its scope.
3. Only after the input/condition comparison, propose an environment diagnostic:
   record OS/CPU/GPU, Python/TF/Keras and numerical flags (including unset), and
   change one agreed comparison factor per fresh process/output. Preserve all
   outcomes; do not search settings until labels match or claim that one-factor
   checks rule out interactions. The cause remains unresolved without evidence.
4. Return label and probability comparisons separately, with commands, logs,
   exit codes and hashes. A selected match does not close the historical external
   FAIL or certify all 781 images; follow the [existing discrepancy lifecycle](DISCREPANCY_LIFECYCLE.md).

The [pinned #101 receipt](https://github.com/heechan9/AdversarialAI_Security/blob/f65d0398a1967a2f3ed763f02de12f0405acb1eb/docs/reviews/20261026/final_submission_integration.md)
records 783 matching asset entries (2 models + 781 images) and
`model_inference_performed=false`; selected cross-only remains **INCOMPLETE**.
This is submitted-JSON consistency evidence, not a new read of the participant's
assets. #101 is still an unmerged Draft as checked on 2026-10-30.

An unsent request to adapt after scope/access agreement:

> Could you first attempt the selected mismatch identified in our agreed packet,
> using its pinned code, inputs, original settings and comparison criteria? Please
> report reproduced / not reproduced / not run, then compare the recorded input
> and environment differences before proposing a cause or fix. Return the exact
> command, log, exit code and output hashes, including negative results. This is
> a bounded reproduction request, not a request to confirm maritime safety or
> independent reproduction of the whole study.

This response loop is our proposed adaptation of co-development/customer-response
themes from the reviewed European semiconductor lecture. The lecture is not
technical evidence for this image benchmark, proof of an established partnership,
or a semiconductor-defect method applied to ship images. No invitations have been
sent and no new diagnostic execution is claimed by this document.

## Propose and return work

Use a repository issue or Draft PR for a public, non-sensitive proposal: research question; existing issue/PR overlap; full base SHA; proposed files/conditions; offered code, artifact or evaluation effort; required access/compute; acceptance criteria; and known limitations. Do not post personal contact details, private links, unpublished binaries or sensitive logs. This guide does not send invitations or create/assign issues automatically.

For a return, include exact reviewed head SHA, changed files, command/environment/log and hash evidence, expected/actual outcomes, and explicit **directly executed / author-reported / not checked** sections. Retain negative results and distinguish saved-data recalculation, actual model inference and human independent review. Use [existing feedback templates](templates) and [SHA-specific review](CPU_CI_REVIEW.md#교차-검수-절차); the English handoff proposed in Draft [#102](https://github.com/heechan9/AdversarialAI_Security/pull/102) is unmerged, not a main dependency.

## Credit and decisions

Preserve [CONTRIBUTIONS.md](../CONTRIBUTIONS.md) and original commit authors. Record actual human work, AI assistance and machine checks separately. Repository contribution does not automatically confer manuscript authorship; authorship/order, artifact release, experiment approval and submission are separate human agreements. Draft publication is not approval to merge, deploy, release or submit.

This documentation structure was requested and scoped by Heechan Choi and prepared with Codex assistance. It does not certify teammate/mentor review, grant new permissions or rename the repository/MARIS interface.
