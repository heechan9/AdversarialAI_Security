# Square Attack 확장 실험

후속 [전체 781장 평가 및 Gaussian 비교](../results/extensions/square/README_FULL_20261003.md)를 완료했다. ε=.03·최대 200회 질의에서 원본 공격 후 정확도 59.92%, Gaussian 47.63%로 방어 개선은 확인하지 못했다. 아래 20장 파일럿 기록은 그대로 보존한다.

안현주 멘토 논문에 등장하는 점수 기반 블랙박스 공격을 선박 분류기에 적용했다. 공식 Square Attack의 Linf 무표적 공격을 NHWC/NumPy + TensorFlow 2.21/Keras 3.15.1에 맞게 이식했다. 학습 또는 방어 성능 개선 기능이 아니라 기존 모델의 취약성을 평가하는 기능이다.

- 원 논문: https://arxiv.org/abs/1912.00049 (ECCV 2020)
- 공식 코드: https://github.com/max-andr/square-attack
- 참조 커밋: `ea95eebb5aca62ec790a927b5aa985ba4e87245c`
- 저자 소속은 EPFL·Tübingen으로, 영국·프랑스 연구로 분류하지 않는다. BSD-3-Clause 고지는 `docs/licenses/square-attack.txt`에 보존했다.

## 구현 범위와 원본과의 차이

수직 줄무늬 초기화, 정사각형 국소 변경, 감소하는 면적 비율, true-class score − max(other scores) 최소화를 사용한다. 모델의 native 출력(현재 CNN은 softmax 확률)만 조회한다. logits 기반 실험과 검색 경로가 다를 수 있다.

원본과 달리 NHWC float32, 지역 `default_rng`, 테두리까지 포함하는 사각형 좌표, 최대 32회의 변경 재시도, argmax에 의한 성공 판정, clean query를 포함하는 총 질의 예산을 사용한다. clean보다 나빠진 초기 후보만 보존한다. 원 논문의 수치를 그대로 재현한 구현이라고 주장하지 않는다. ε=0은 clean 1회만 조회한다. clean 오분류는 그대로 두며 ASR 분모에서 제외한다. 반환된 공격 샘플을 재조회하지 않고 마지막으로 저장한 출력으로 평가하므로 숨겨진 추가 질의가 없다. 입력값은 [0,1], 교란 예산은 필터 적용 전 입력 기준이다.

가우시안/평균 필터 선택 시 f(D(x)) 전체를 직접 조회해 공격한다. 필터 미포함 모델에서 만든 공격을 단순히 필터링한 transfer 평가와 다르다. 필터 유무의 ASR은 각자 clean 정확도에 따른 분모를 갖는다.

## 실행

원본 모델은 `models/`, 데이터는 `data/test/`에 비공개로 준비한다. 실행 전 소스 변경을 커밋해야 한다. 선택된 이미지와 모델은 기존 manifest SHA-256으로 확인한다. 클래스마다 manifest 순서의 앞 2장을 사용하며 예측 결과로 이미지를 고르지 않는다.

```bash
TF_ENABLE_ONEDNN_OPTS=0 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1 \
PYTHONPATH=src python -m adversarial_ai.evaluation.square_evaluation \
  --run-id cnn_square_new --max-queries 200

# 같은 예산으로 필터 포함 모델을 직접 공격
TF_ENABLE_ONEDNN_OPTS=0 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1 \
PYTHONPATH=src python -m adversarial_ai.evaluation.square_evaluation \
  --run-id cnn_gaussian_square_new --defense gaussian --epsilons 0 .03 --max-queries 200

# 전체 원본 781장이 있을 때 --per-class 0 으로 전체 평가 가능
# --model mobilenet, --defense mean 도 지원하지만 이번 실행에는 포함하지 않았다.
PYTHONPATH=src python -m pytest tests/test_square.py -q
python verification/square_saved_audit.py
```

결과는 `results/extensions/square/<새 run-id>/`에만 저장한다. 기존 디렉터리를 덮어쓰지 않는다. 200회 결과로 1,000/10,000회 공격의 견고성을 추론하지 않는다. 재현에는 동일 seed뿐 아니라 동일 이미지 순서·배치 크기·환경이 필요하다.

## 2026-10-03 CPU 파일럿

고정 20장(10종 × 2장), seed=2026, batch=20, p_init=.05, 최대 총 질의 200회. TF 2.21.0/Keras 3.15.1, oneDNN off, 원본 CNN. 학습이나 모델 선택은 하지 않았다.

| 모델 입력 경로 | ε | clean 정답 | 공격 후 정답 | ASR |
|---|---:|---:|---:|---:|
| 원본 CNN | 0 | 16/20 | 16/20 | 0/16 |
| 원본 CNN | .01 | 16/20 | 15/20 | 1/16 (6.25%) |
| 원본 CNN | .03 | 16/20 | 12/20 | 4/16 (25%) |
| 원본 CNN | .05 | 16/20 | 12/20 | 4/16 (25%) |
| Gaussian → CNN | 0 | 14/20 | 14/20 | 0/14 |
| Gaussian → CNN | .03 | 14/20 | 10/20 | 4/14 (28.57%) |

이 표는 파이프라인 실행 확인용이다. 균등 20장 파일럿은 전체 데이터의 선종 분포와 다르고 표본도 작다. 방어 개선·통계적 유의성·실제 운항 안전성을 입증하지 않는다. 기존 781장 PGD 결과와 직접 비교하지 않는다. 원본 모델의 과거 train/test 노출 가능성도 해소하지 않는다.

실행 소스의 로컬 커밋은 `4dba787ec27bf10f26ba4fe979ab14518744710a`로 원본 run.json에 기록되어 있다. GitHub 커넥터로 게시한 동일 소스 커밋은 `a320350b78a2fe0d67b4fd225bc4660d85515fb3`이다. 두 커밋의 Git tree는 `4be06b27dded107e1b9bdfaba59fcb608cd34db7`로 일치한다. 커밋 메타데이터만 다르며 실행 기록을 사후 변경하지 않았다.

## 영국·프랑스 자료의 적용 범위

영국 Plymouth의 *Adversarial AI Testcases for Maritime Autonomous Systems*와 RED-AI는 해상 시나리오 기반 검증의 참고다. 이번 실험은 정지 이미지 분류기 평가이며 해상 영상·패치·항법 위험을 검증하지 않았다.

프랑스 RoBIC(arXiv:2102.05368)는 clean 성능과 공격 내성을 분리해 보는 참고자료다. 여기서는 ε별 정확도, 조건부 ASR, 질의 예산별 성공 개수만 제공하며 RoBIC의 half-distortion을 구현했다고 주장하지 않는다. SurFree의 top-1 decision-only 공격도 이 점수 기반 공격과 별개이며 아직 추가하지 않았다. Xplique/deel-lip은 현재 Keras 3 환경의 호환성 확인이 더 필요하여 의존성을 추가하지 않았다.
