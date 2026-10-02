# Exact JSMA block pruning

The original selector evaluates every eligible feature pair. At 49,152 CNN
features or 150,528 MobileNet features, this dominates CPU execution time.
The updated selector orders block pairs by an upper bound and skips a block
only when it cannot improve the current winner. It does not restrict the
candidate set with top-k selection or change theta, gamma, targets, or steps.

For positive theta, a feasible score is `alpha * (-beta)`. The sum of the
maximum target gradients in two blocks bounds alpha; the sum of the maximum
negated other-class gradients bounds -beta. Their product therefore bounds
every feasible score in those blocks, even if the two maxima belong to
different feature pairs. Negative theta flips both signs for the bound only.
The product is rounded outward. Equal bounds are evaluated so original
lexicographic tie-breaking is retained. Nonfinite bounds fall back to original
block order without pruning. Original feasibility, budget checks and scores
remain in the candidate evaluation.

Worst-case pair evaluation remains quadratic. Block-bound metadata uses
quadratic space in the number of blocks, rather than the number of features;
the default block size is 256. This is not a universal runtime guarantee.

## Verification

- 600 seeded comparisons with independent exhaustive enumeration cover both
  theta signs, eligibility masks, remaining L0 budgets, repeated features,
  near-cancelling gradients and ties.
- Two complete toy attacks compare adversarial arrays and termination metadata
  against exhaustive selection, with positive and negative theta.
- Relevant local test suite: 65 tests passed.
- Actual original-model first-sample gradient comparison selected the same
  pair in both implementations:

| Model | Features | Original selection | Pruned selection | Same pair |
|---|---:|---:|---:|---|
| CNN | 49,152 | 18.931 s | 0.037 s | yes |
| MobileNet | 150,528 | 137.451 s | 0.256 s | yes |

These timings concern one pair selection on one image per model, with other
experiments sharing the CPU. They are not full-attack speedup estimates or
robustness results. Exact measurements and gradient hashes are recorded in
`results/extensions/checkpoints/20261002-mobile/jsma-exact-benchmark.json`.
New full JSMA evaluations must retain their own source commit and run metadata.

## Gradient-grouped blocks

A second exact optimization groups eligible features by signed target gradient
before partitioning them into blocks. No eligible feature is discarded. Cross-
block pairs are canonicalized to the original feature indices, including ties.
A global minimum new-feature cost also rejects impossible remaining L0 budgets.
Nonfinite bounds retain the original traversal fallback.

The recorded CNN sample 63, truncated to three attack steps, decreased from
15.441 s to 0.328 s with identical adversarial bytes and termination metadata.
This is one probe, not a full-dataset speed or attack-success claim. The probe
is in `results/extensions/checkpoints/20261002-mobile/jsma-grouped-benchmark.json`.
