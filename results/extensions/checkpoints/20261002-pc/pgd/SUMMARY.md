# Follow-up experiment snapshot

Coverage: 2/16 conditions.
Audit: **PARTIAL_OUTPUTS_ONLY**. Captured execution status: RUNNING.
This is a fixed snapshot, not live monitoring or independent verification approval.
Accuracy denominator: 781 per condition. ASR denominators are shown explicitly.
Clean and filtered-clean rows describe baseline accuracy; their changes are not attack success.

| Model | Filter | Epsilon | Pipeline | Accuracy (%) | ASR (%) | Successes / denominator |
|---|---|---:|---|---:|---:|---:|
| cnn | gaussian | 0 | clean | 64.53 | N/A | N/A |
| cnn | gaussian | 0 | defended_clean | 56.98 | N/A | N/A |
| cnn | gaussian | 0 | attacked | 64.53 | 0.00 | 0 / 504 |
| cnn | gaussian | 0 | transfer_defended | 56.98 | 0.00 | 0 / 445 |
| cnn | gaussian | 0 | adaptive_defended | 56.98 | 0.00 | 0 / 445 |
| cnn | gaussian | 0.01 | clean | 64.53 | N/A | N/A |
| cnn | gaussian | 0.01 | defended_clean | 56.98 | N/A | N/A |
| cnn | gaussian | 0.01 | attacked | 26.50 | 58.93 | 297 / 504 |
| cnn | gaussian | 0.01 | transfer_defended | 49.42 | 13.26 | 59 / 445 |
| cnn | gaussian | 0.01 | adaptive_defended | 23.69 | 58.43 | 260 / 445 |
