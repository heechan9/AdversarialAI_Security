# Follow-up experiment snapshot

Coverage: 12/16 conditions.
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
| cnn | gaussian | 0.01 | attacked | 27.66 | 57.14 | 288 / 504 |
| cnn | gaussian | 0.01 | transfer_defended | 48.78 | 14.38 | 64 / 445 |
| cnn | gaussian | 0.01 | adaptive_defended | 24.20 | 57.53 | 256 / 445 |
| cnn | gaussian | 0.03 | clean | 64.53 | N/A | N/A |
| cnn | gaussian | 0.03 | defended_clean | 56.98 | N/A | N/A |
| cnn | gaussian | 0.03 | attacked | 10.37 | 83.93 | 423 / 504 |
| cnn | gaussian | 0.03 | transfer_defended | 33.29 | 41.57 | 185 / 445 |
| cnn | gaussian | 0.03 | adaptive_defended | 5.63 | 90.11 | 401 / 445 |
| cnn | gaussian | 0.05 | clean | 64.53 | N/A | N/A |
| cnn | gaussian | 0.05 | defended_clean | 56.98 | N/A | N/A |
| cnn | gaussian | 0.05 | attacked | 9.73 | 84.92 | 428 / 504 |
| cnn | gaussian | 0.05 | transfer_defended | 26.50 | 53.71 | 239 / 445 |
| cnn | gaussian | 0.05 | adaptive_defended | 4.61 | 91.91 | 409 / 445 |
| cnn | mean | 0 | clean | 64.53 | N/A | N/A |
| cnn | mean | 0 | defended_clean | 53.65 | N/A | N/A |
| cnn | mean | 0 | attacked | 64.53 | 0.00 | 0 / 504 |
| cnn | mean | 0 | transfer_defended | 53.65 | 0.00 | 0 / 419 |
| cnn | mean | 0 | adaptive_defended | 53.65 | 0.00 | 0 / 419 |
| cnn | mean | 0.01 | clean | 64.53 | N/A | N/A |
| cnn | mean | 0.01 | defended_clean | 53.65 | N/A | N/A |
| cnn | mean | 0.01 | attacked | 27.66 | 57.14 | 288 / 504 |
| cnn | mean | 0.01 | transfer_defended | 48.14 | 10.26 | 43 / 419 |
| cnn | mean | 0.01 | adaptive_defended | 22.92 | 57.28 | 240 / 419 |
| cnn | mean | 0.03 | clean | 64.53 | N/A | N/A |
| cnn | mean | 0.03 | defended_clean | 53.65 | N/A | N/A |
| cnn | mean | 0.03 | attacked | 10.37 | 83.93 | 423 / 504 |
| cnn | mean | 0.03 | transfer_defended | 37.77 | 29.59 | 124 / 419 |
| cnn | mean | 0.03 | adaptive_defended | 4.48 | 91.65 | 384 / 419 |
| cnn | mean | 0.05 | clean | 64.53 | N/A | N/A |
| cnn | mean | 0.05 | defended_clean | 53.65 | N/A | N/A |
| cnn | mean | 0.05 | attacked | 9.73 | 84.92 | 428 / 504 |
| cnn | mean | 0.05 | transfer_defended | 31.88 | 40.57 | 170 / 419 |
| cnn | mean | 0.05 | adaptive_defended | 3.33 | 93.79 | 393 / 419 |
| mobilenet | gaussian | 0 | clean | 78.49 | N/A | N/A |
| mobilenet | gaussian | 0 | defended_clean | 82.97 | N/A | N/A |
| mobilenet | gaussian | 0 | attacked | 78.49 | 0.00 | 0 / 613 |
| mobilenet | gaussian | 0 | transfer_defended | 82.97 | 0.00 | 0 / 648 |
| mobilenet | gaussian | 0 | adaptive_defended | 82.97 | 0.00 | 0 / 648 |
| mobilenet | gaussian | 0.01 | clean | 78.49 | N/A | N/A |
| mobilenet | gaussian | 0.01 | defended_clean | 82.97 | N/A | N/A |
| mobilenet | gaussian | 0.01 | attacked | 0.00 | 100.00 | 613 / 613 |
| mobilenet | gaussian | 0.01 | transfer_defended | 39.44 | 52.62 | 341 / 648 |
| mobilenet | gaussian | 0.01 | adaptive_defended | 0.00 | 100.00 | 648 / 648 |
| mobilenet | gaussian | 0.03 | clean | 78.49 | N/A | N/A |
| mobilenet | gaussian | 0.03 | defended_clean | 82.97 | N/A | N/A |
| mobilenet | gaussian | 0.03 | attacked | 0.00 | 100.00 | 613 / 613 |
| mobilenet | gaussian | 0.03 | transfer_defended | 5.76 | 93.06 | 603 / 648 |
| mobilenet | gaussian | 0.03 | adaptive_defended | 0.00 | 100.00 | 648 / 648 |
| mobilenet | gaussian | 0.05 | clean | 78.49 | N/A | N/A |
| mobilenet | gaussian | 0.05 | defended_clean | 82.97 | N/A | N/A |
| mobilenet | gaussian | 0.05 | attacked | 0.00 | 100.00 | 613 / 613 |
| mobilenet | gaussian | 0.05 | transfer_defended | 3.07 | 96.30 | 624 / 648 |
| mobilenet | gaussian | 0.05 | adaptive_defended | 0.00 | 100.00 | 648 / 648 |
