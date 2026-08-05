# Clean Baseline Reproduction

실행일: 2026-08-05  
환경: Python 3.11.15 / TensorFlow 2.21.0 / Keras 3.15.1 (`adversarial_ai` Conda 환경)  
평가셋: `ships_dataset/test` 781장, 10개 클래스, `shuffle=False`

## 재현 결과

| 모델 | 입력 | Test loss | Test accuracy | 정분류 | Macro F1 | Weighted F1 |
|---|---:|---:|---:|---:|---:|---:|
| CNN Baseline | 128×128×3 | 4.026247978210449 | 0.6453264951705933 | 504/781 | 0.66 | 0.65 |
| MobileNetV2 Finetuned | 224×224×3 | 1.1212257146835327 | 0.7848911881446838 | 613/781 | 0.79 | 0.78 |

MobileNet은 CNN보다 정확도가 0.13956469297409058(약 13.96%p) 높고, 정분류 표본이 109장 많았다. 두 모델 모두 Sailboat recall(CNN 0.12, MobileNet 0.31)과 DDG recall(CNN 0.37, MobileNet 0.50)이 낮았다. Recreational은 recall이 매우 높지만 precision이 낮아(CNN 0.31/0.98, MobileNet 0.51/0.97; precision/recall) 다른 클래스가 Recreational로 쏠리는지 confusion matrix로 확인해야 한다.

## 증거 수준과 제한

- CNN accuracy는 기존 기록 `0.6453265`와 재현 결과가 일치한다.
- 원본 `handoff_spec.json`의 CNN loss `4.026344299316406`과 이번 실행 loss `4.026247978210449`은 약 `9.63e-05` 차이가 있다. accuracy가 기존 기록과 정확히 일치하므로 부동소수점 연산 순서·TensorFlow 실행환경 차이로 발생한 것으로 추정하며, 최신 실행로그 값을 현재 재현 결과로 사용한다.
- `handoff_spec.json`은 normalization을 두 모델 공통 `0-1 (rescale=1./255)`로 명세하고, 두 clean 평가도 이를 사용했다. 다만 MobileNet 학습 코드 자체가 없어 **학습 당시 실제 전처리는 미확정**이다.
- test manifest와 모델 SHA-256은 모델·데이터가 있는 로컬 환경에서 생성해야 한다. 이 저장소 작업환경에서는 바이너리를 확보하지 못했으므로 값을 만들지 않았다.
