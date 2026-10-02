# First complete-data adversarial fine-tuning run

This follow-up run does not replace ACK/FGSM results or independent Stage B
verification. Training is blocked until all 8,067 source IDs have verified
local records. Source images and private Drive identifiers stay out of Git.

## Data preparation

`verification.prepare_training_data` checks source coverage, downloaded hashes,
file sizes, image decoding and exact split overlap. It makes a new copy:

- Remove all training copies of an image found in validation or fixed test.
- Exclude all training copies with conflicting training class labels.
- For each remaining exact RGB group, retain the lexicographically first path.
- Reject validation duplicates or validation/test overlap for separate review.
- Require all classes to remain nonempty and rerun the training integrity gate.

Originals and held-out splits are not modified. Near duplicates or related
frames can remain; the resulting status is PREPARED_EXACT_AUDIT_ONLY.

```bash
PYTHONPATH=src python -m verification.prepare_training_data \
  --inventory /private/train-inventory.json \
  --staged /private/train-staged-manifest.json \
  --train /private/data/train-audit --valid /private/data/valid \
  --test /private/data/test --destination /private/data/train-prepared
```

## Settings fixed before evaluating the trained models

Both original model clones use three epochs, Adam learning rate 0.00001,
batch size 32 and seed 2026. Each batch mixes clean and PGD losses equally.
Training PGD uses epsilon 0.03, step size 0.005, seven steps and one random
start. The best epoch is selected by validation PGD accuracy, never by test
results. Original model hashes must match the fixed manifest and their files
must remain unchanged. This is an initial configured run, not optimized training
or a claim that these settings are sufficient for robustness.

```bash
PYTHONPATH=src python -m adversarial_ai.training.adversarial_training \
  --model cnn --train-dir /private/data/train-prepared/images \
  --validation-dir /private/data/valid --test-dir /private/data/test \
  --epochs 3 --epsilon 0.03 --step-size 0.005 --steps 7 \
  --seed 2026 --batch-size 32 --learning-rate 0.00001 \
  --run-id cnn-pgd-training-20261002
```

Repeat with `--model mobilenet` and a different run ID. Training completion is
TRAINED_NOT_TEST_EVALUATED, not a final result. Each saved best model must then
be evaluated through the separate trained-model BIM/PGD evaluator, retaining
its model SHA-256 and all 781 fixed test samples. Trained-model comparison uses
the same BIM 10-step and PGD 20-step/five-restart settings as the original
models, across the four epsilons and two filters. Full iterative CSV audits are
required before reporting completion.

Long-running process existence and a RUNNING report are not completion evidence.
Interruption may require restarting an unfinished epoch or condition.

The sequential per-model runner verifies the prepared images, runs training,
then invokes and audits both trained-model evaluations. Run once for each model
with distinct output IDs:

```bash
PYTHONPATH=src python -m verification.run_training_pipeline \
  --model cnn --prepared /private/data/train-prepared \
  --valid /private/data/valid --test /private/data/test \
  --run-prefix pgd-train-20261002
```

Each runner writes `results/extensions/pipelines/<prefix>-<model>/pipeline.json`
with its active stage and errors. It never marks the whole project complete or
automatically publishes raw data or models to GitHub.
