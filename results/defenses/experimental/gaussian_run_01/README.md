# Gaussian defense experimental result v1.0

Status: experimental; not promoted. Original Clean/FGSM evidence remains unchanged.

## Clean accuracy

| Model | Original correct / 781 | Defended correct / 781 | Change (percentage points) |
|---|---:|---:|---:|
| cnn | 504 | 445 | -7.55 |
| mobilenet | 613 | 648 | +4.48 |

## Attack accuracy (denominator: all 781 samples)

| Model | epsilon | Original attack, no defense | Original attack + defense | Defense-aware attack + defense |
|---|---:|---:|---:|---:|
| cnn | 0.01 | 41.61% | 50.45% | 31.37% |
| cnn | 0.03 | 24.33% | 34.70% | 12.55% |
| cnn | 0.05 | 20.23% | 27.66% | 8.32% |
| mobilenet | 0.01 | 12.42% | 43.66% | 9.48% |
| mobilenet | 0.03 | 13.19% | 26.63% | 7.17% |
| mobilenet | 0.05 | 16.13% | 25.10% | 8.71% |

## Interpretation / claim boundary

고정 가우시안 전처리는 방어를 고려하지 않은 FGSM 입력에서 정확도를 높였으나,
방어 인지 FGSM에서는 높은 공격 성공률을 보여 단독 방어의 한계가 확인되었다.
CNN 정상 정확도는 감소했고 MobileNetV2는 이 테스트셋에서 증가했다.
다른 데이터셋이나 실제 자율운항 안전성으로 일반화하지 않는다.

ASR denominators are pipeline-specific: original clean-correct vs defended clean-correct.
The JSON also reports each model’s original/defended clean-correct intersection and class counts.
Do not compare ASRs without their denominators. No kernel tuning was performed on these results.

## Evidence audit

- Original ZIP preserved as `original_bundle.zip`; exact hash in `PROVENANCE.json`.
- All 12 original member files retained byte-for-byte (Windows line endings preserved).
- 10 internal hashes and both completion hash links matched.
- 8 CSVs × 781 rows: canonical order/labels/clean predictions matched.
- Original attack predictions matched existing provisional FGSM evidence.
- 8 aggregate + 80 class summaries independently recalculated and matched.
- Recorded L-infinity finite/bounded; epsilon=0 invariants and normal prediction stability passed.
- PC reports weights/input hashes unchanged; raw arrays/models unavailable for independent rerun.

Tables above were generated from the uploaded summary only after independent row recomputation;
the CSV/JSON remains canonical for this separate experimental run. No paper snapshot was modified.
