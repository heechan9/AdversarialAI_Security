# Minimal evidence handoff (English template)

Copy only for an agreed review task. Replace placeholders with observed facts;
leave unavailable evidence **NOT RUN / UNKNOWN / PENDING**. This template creates
no issue, PR, reviewer assignment, experiment or approval by itself.

## One review question

- Local issue ID or authorized issue URL: `<id>`
- Claim or defect: `<one sentence>`
- Expected / observed: `<both; include the first known divergence>`
- Acceptance criterion and scope exclusions: `<checkable outcome; no new models,
  data, attacks, training or deployment unless separately authorized>`
- Owner / author / executor / reviewer / AI assistance: `<distinct roles;
  reviewer and deadline pending until agreed>`

## Exact version and inputs

- Repository / base SHA / reviewed head SHA: `<full values>`
- If unpublished: `<base SHA + patch SHA-256; no remote head exists yet>`
- Changed files: `<small diff; check overlap with open PRs>`
- Evaluation SHA / diagnostic-tool SHA / comparison run: `<do not conflate>`
- Input manifest / model / class map / selection or array SHA-256: `<values>`
- Image identities and order / labels / preprocessing / checkpoint: `<values>`
- Attack / norm / epsilon / steps / restarts / seed / transfer or adaptive:
  `<exact condition; do not mix FGSM and PGD>`
- Paired comparison axis / held-fixed conditions: `<one question; report deviations>`
- Planned / completed / failed / not-run conditions: `<counts and reasons>`
- Private-input access: `<authorized route pending or verified; no private links,
  credentials, personal paths, image/model/array binaries in the public packet>`

## Minimum reproduction and evidence

- Environment: `<OS, CPU/GPU, Python/TF/Keras; numerical flags or unset>`
- Exact command / working directory / fresh output location: `<sanitized>`
- Started / finished / exit code / log / output artifact SHA-256: `<evidence>`
- Input-integrity result: `<directly checked / submitter-reported / unknown>`
- Inference performed: `<yes/no/unknown and by whom; asset checks are not inference>`
- Saved-output comparison: `<source/target, label and probability differences
  separately, unchanged tolerances, numerator/denominator/cohort>`
- Hypothesis / unresolved alternatives / next discriminating check: `<not a cause claim>`

If inputs are unavailable or preflight stops, report the exact stage and logs;
do not fabricate an inference result or treat missing output as a label mismatch.
An example command is not an execution log. A saved audit is not model replay.

## Small-PR review and closure

- Checks directly run: `<command, exact revision or patch identity, outcome, log>`
- Submitter-reported checks: `<source; not personally observed>`
- Not run / blocked: `<check, reason, smallest authorized next action>`
- Reviewer finding → changed file/line → correction SHA → retest → reviewer reply:
  `<one trace per finding; a new head invalidates the previous head's approval>`
- Publication: **PENDING owner/author approval** until explicitly recorded.
- Review acceptance: **PENDING** until the agreed reviewer confirms this version.
- Merge / independent experimental approval / final submission / deployment:
  **separate decisions; not implied by CI or documentation acceptance**.

Preserve historical provisional/experimental labels and unresolved failures.
Input hash agreement is not reproduction PASS; selected matches are not a full
781-image replay. Keep the research PC's LOCAL_PASS separate from the external
FAIL with unresolved cause. Different own-clean ASR cohorts must not be treated
as a matched denominator. Do not silently remove interrupted or failed runs.

Use the existing [analysis checklist](../DATA_ANALYSIS_REVIEW_CHECKLIST.md),
[review workflow](../REVIEW_WORKFLOW.md) and [CPU review contract](../CPU_CI_REVIEW.md).
Do not create a duplicate scientific status registry from this work record.
