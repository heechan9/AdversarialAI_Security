# International research collaboration

**PaulGuard — Maritime AI Security Research** is our public-facing research name. The existing virtual lab remains **MARIS**; historical submission titles, team credits and the repository URL are preserved. This is a documentation-level name, not a new UI, deployed system or verified trademark clearance.

We welcome narrowly scoped collaboration on **independent reproduction** and **additional attack/defense evaluation** for ten-class ship-image classification. This is a research prototype, not an operational ship-protection system. Start with the [English overview](../README.en.md), [preserved source/evidence boundary](PAPER_RELEASE_STATUS.md#preserved-source-and-submission-boundary--2026-10-30) and [reproduction navigation](REPRODUCIBILITY.md#english-reproduction-navigation).

## What is available, and what is not

- Public evaluation/audit source in [src](../src), [verification](../verification), [tests](../tests), versioned [configuration/manifest](../configs), and saved [result artifacts](../results).
- Existing [attack contract](EXPERIMENT_CONTRACT.md), [threat model](THREAT_MODEL.md), [evidence audit](RESEARCH_EVIDENCE_AUDIT.md), and [review procedure](REVIEW_WORKFLOW.md); these remain authoritative rather than being replaced by another protocol.
- Separate extension [one-seed matched-CNN evidence and executed evaluator](../results/extensions/matched_cnn_20261024/README.md), with its own provenance and limitations.
- Original model binaries and the full image dataset are **not distributed in Git**. Access and redistribution require rights checks and explicit owner/team authorization. Public visibility alone is not a redistribution license; do not promise unrestricted code/data reuse or invent a license.

The research-PC LOCAL_PASS does not erase the external FAIL. The discrepancy cause remains unresolved; selected cross-only work is INCOMPLETE. Asset hash agreement without inference must not be presented as independent reproduction. A successful software audit is not independent experimental approval.

## Choose one first contribution

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

## First external request: reproduce a failed condition, then compare environments

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
