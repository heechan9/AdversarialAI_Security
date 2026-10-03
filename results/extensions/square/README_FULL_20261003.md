# CNN Square Attack 전체 781장 및 Gaussian 비교

2026-10-03에 기존 고정 테스트 781장 전체를 CPU에서 평가했다. 이번 ε=0.03·최대 200회 질의 조건에서는 Gaussian 필터 적용이 원본 CNN보다 정상 정확도와 공격 후 정확도 모두 낮았다. 방어 개선을 확인하지 못했으므로 기본 추론 경로를 변경하지 않았다.

| 평가 | 원본 CNN | Gaussian → CNN |
|---|---:|---:|
| 정상 정확도 | 504/781 (64.53%) | 445/781 (56.98%) |
| 공격 후 정확도 | 468/781 (59.92%) | 372/781 (47.63%) |
| 정상 정답에서의 공격 성공률 | 36/504 (7.14%) | 73/445 (16.40%) |
| 전체 이미지 평균 총 질의 | 121.77 | 97.80 |
| 성공 이미지 평균 총 질의 | 34.14 | 22.58 |

ASR 분모는 각 조건의 정상 정답 수다. 두 조건 모두 정상 정답인 공통 389장에서도 원본 공격 성공 14/389(3.60%), Gaussian 66/389(16.97%)였다. 필터 적용으로 공격 후 정답이 된 이미지는 57장, 반대로 오답이 된 이미지는 153장으로 순 96장 감소(−12.29%p)했다. 질의 평균에는 정상 오분류 이미지의 eligibility query 1회도 포함된다. 평균 질의가 낮다는 것만으로 방어가 강하다고 해석할 수 없다.

## 고정 조건

- 원본 `cnn_baseline.h5`, SHA-256은 기존 `configs/test_manifest.json`과 일치한다. 10종 781장 모두 원본 파일 해시 검증을 통과했다.
- 소스 커밋: `cfa5a9442ca7ae63e0b5aeb105cfa01c80dfbb2d` (PR #74 병합 코드). 공격/evaluation 소스를 변경하지 않고 실행했다.
- Square Linf untargeted adapter, native softmax score, ε=0.03, p_init=.05, seed=2026+batch 시작 인덱스, batch=20, 최대 총 질의 200(정상 eligibility query 포함).
- TensorFlow 2.21.0, Keras 3.15.1, NumPy 2.5.3, Python 3.13.15. CPU, oneDNN off, intra-op 4/inter-op 1. 두 조건은 같은 환경이며, 이전 파일럿의 intra-op 2와는 구분한다.
- Gaussian은 기존 고정 필터를 사용한다. f(D(x))를 직접 공격하며, 교란 예산은 필터 전 입력 기준이다. 각 조건에서 ε=0 정상 대조군도 별도로 실행했다.
- 각 조건의 run.json에 환경, 모델/manifest 해시, CSV 해시, 지표를 보존했다. 이미지는 공개하지 않는다.

## 재실행 및 감사

```bash
TF_ENABLE_ONEDNN_OPTS=0 TF_NUM_INTRAOP_THREADS=4 TF_NUM_INTEROP_THREADS=1 \
PYTHONPATH=src python -m adversarial_ai.evaluation.square_evaluation \
  --run-id cnn_none_full_new --per-class 0 --defense none \
  --epsilons 0 .03 --max-queries 200 --batch-size 20

TF_ENABLE_ONEDNN_OPTS=0 TF_NUM_INTRAOP_THREADS=4 TF_NUM_INTEROP_THREADS=1 \
PYTHONPATH=src python -m adversarial_ai.evaluation.square_evaluation \
  --run-id cnn_gaussian_full_new --per-class 0 --defense gaussian \
  --epsilons 0 .03 --max-queries 200 --batch-size 20

python verification/square_saved_audit.py
python verification/square_defense_comparison.py \
  results/extensions/square/cnn_none_full_20261003 \
  results/extensions/square/cnn_gaussian_full_20261003
```

전체 실험 2조건 × (정상+공격) × 781장 = 3,124행의 파일 해시, manifest 경로·정답, 교란 범위, 질의 제한 및 지표를 재계산했다. 기존 파일럿 120행도 계속 검증한다. `comparison_full_20261003.json`은 같은 이미지끼리 대응시킨 비교이며 CI에서 다시 계산한다. McNemar exact p값은 보조적인 탐색 통계다. 원본 모델의 과거 학습/테스트 노출 가능성, 이미지 간 의존성과 근접 중복이 있으므로 일반화·통계적 독립성을 입증하는 근거로 사용하지 않는다.

이는 전체 **고정 테스트 세트**에 대한 한 공격 예산의 결과다. 더 큰 질의 예산, 여러 seed, 다른 공격·모델, 실제 해상 영상이나 항법 안전성까지 검증한 것은 아니다. 20장 파일럿, 기존 PGD/FGSM 및 제출 논문 수치를 대체하지 않는다. 추가학습이나 테스트 결과에 따른 하이퍼파라미터 선택은 하지 않았다.
