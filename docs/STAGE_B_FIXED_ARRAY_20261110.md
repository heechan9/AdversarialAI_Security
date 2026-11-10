# Selected fixed-array cross-scoring · November 10, 2026

This is a public aggregate of a privately retained diagnostic, not a new accuracy benchmark or external Stage B approval. **Windows/Linux scoring × PC/Linux attack-array origin: 4/4 matrix cells completed**, with **four selected images and five selected conditions per cell**. Images are reused across conditions and cells.

## What was executed and checked

- The user ran two Windows cross-only scoring processes on existing saved arrays. Both returned exit 0 and COMPLETE. This added ten selected-condition outputs; no model training, attack generation or weight changes were performed.
- Previously retained Linux oneDNN=1 scoring results fill the other two cells. Linux inference was not repeated for this receipt.
- The same frozen runner at [491b973](https://github.com/heechan9/AdversarialAI_Security/blob/491b973cd9f4840664044a83c0d62d1ee1bb98e8/verification/stage_b_trace.py) was used for the matrix. This run does not demonstrate use of the separate, later strict selection-parser candidate.
- Receipt verification and comparison were run in ordinary and optimized Python. These checks validated saved reports and the matrix; they did not repeat inference and do not establish a fresh pass of every earlier software test suite.

| Saved attack-array origin | Windows scorer | Linux scorer, oneDNN=1 |
|---|---:|---:|
| PC | 5 selected outputs, COMPLETE | 5 selected outputs, COMPLETE |
| Linux | 5 selected outputs, COMPLETE | 5 selected outputs, COMPLETE |

**20 matrix outputs are not 20 independent samples.** The new Windows execution contributes ten outputs from two processes, using four selected images across five conditions.

## Observed comparisons

- **Same arrays, different scoring environments:** ten of ten predicted-label pairs agree. No compared probability vector is exactly identical (0/10); the largest absolute probability-component difference is **2.9206275939941406 × 10⁻⁶**. Label agreement is not probability identity or accuracy.
- **Different array origins, same scoring environment:** all five selected labels change in each environment (ten of ten origin-pair comparisons). The source-dependent label differences persist under both scorers.

Class indices below are saved predictions, not correctness scores. Each selected condition denotes its own saved selection; matching method names do not imply the same selected image.

| Selected condition | ε | PC-origin, Windows / Linux | Linux-origin, Windows / Linux |
|---|---:|---:|---:|
| Gaussian · adaptive defended | 0.03 | 7 / 7 | 6 / 6 |
| Gaussian · attacked | 0.03 | 1 / 1 | 6 / 6 |
| Mean · adaptive defended | 0.05 | 3 / 3 | 7 / 7 |
| Mean · attacked | 0.03 | 1 / 1 | 6 / 6 |
| Mean · transfer defended | 0.05 | 1 / 1 | 6 / 6 |

The [compact public summary](../web/maris/public/evidence/fixed-array-cross-score.json) records these counts and class indices. Its consistency/KO–EN rendering test checks public presentation, not the authenticity of private inference. Raw arrays, images, model binaries, original reports/logs and personal PC paths remain private; the public aggregate alone cannot independently reproduce or fully audit the underlying run.

## Interpretation and remaining limits

Within these selected saved inputs, a Windows-versus-Linux **scoring-label disagreement was not observed**. The diagnostic narrows where the retained discrepancy appears, but **the single cause of attack-generation differences remains UNRESOLVED**. It does not exclude operating-system effects during generation or identify a specific implementation, preprocessing, seed or numerical setting as the cause.

Windows used Python 3.11.15, TensorFlow 2.21.0 and Keras 3.15.1, with oneDNN unset/native defaults; the retained Linux scorer used Python 3.12.14, the same TensorFlow/Keras versions and oneDNN=1. The differing builds, runtime, CPU/ISA and execution settings are not a controlled one-variable experiment.

- Historical research-PC full-run status remains **LOCAL_PASS**.
- Historical external Stage B status remains **FAIL**, with **stage_b_approved=false** and cause **UNRESOLVED**. The selected 4/4 matrix is a separate diagnostic scope.
- Hyeonsu's separately recorded selected cross-only handoff remains **INCOMPLETE**; the user's new Windows run does not substitute for that independent work.
- No new full 781-image evaluation or model-performance improvement is claimed.
- Source-byte matching of 610 available files, preparation checks and software regression results are separate evidence, not model accuracy or Windows inference.

## Contributions and public disclosure

**최희찬 / heechan9:** selected the verification scope, operated the guided Windows commands and returned the execution evidence. **AI assistance (Codex):** prepared guidance/tooling, checked the returned artifacts offline and prepared this public aggregate and interface. This does not establish independent manual implementation or a live interview demonstration. Earlier team and external-review contributions retain their original scope in [CONTRIBUTIONS.md](../CONTRIBUTIONS.md); no new external reviewer approval is claimed.

Only the aggregate and its limitations are published. Original evidence and historical results are preserved privately; no raw photographic material is distributed by this update.
