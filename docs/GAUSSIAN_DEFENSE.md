# 작은 전처리 방어: experimental v1.0

상태: 구현 후보. 실제 781장/CNN/MobileNetV2 방어 효과 미검증. 공식 채택 아님.

## 고정 계약

- 모델 입력 직전의 [0,1] NHWC float32 이미지에만 적용한다.
- 고정 3×3 커널 `[[1,2,1],[2,4,2],[1,2,1]]/16`, 가장자리는 reflect.
- 색 채널별 독립 처리, 크기 보존. 학습·파라미터 탐색 없음.
- 모델 로딩/기존 리사이즈/정규화/모델 내부 전처리는 변경하지 않는다.
- NumPy 함수는 비교용 참조 구현이다. 공격 계산에는 TensorFlow 구현만 사용한다.
- PNG 비교 패널을 원본 공격 배열로 취급하지 않는다.

## 사용

```python
from adversarial_ai.defenses.gaussian import GaussianDefendedModel, generate_adaptive_fgsm
# model: 기존 로더로 읽은 모델. x: 기존 경로로 준비한 [0,1] 배치.
# y: 실제 정답 one-hot. epsilon: 기존 계약에 기록된 실험 강도.
defended = GaussianDefendedModel(model)
clean_defended_scores = defended(x)
x_adv = generate_adaptive_fgsm(model, x, y, epsilon)
attacked_defended_scores = defended(x_adv)
```

기존 FGSM 생성기를 재사용하여 `f(D(x))` 전체를 미분한다. 공격 예산은
방어 전 입력 `x_adv - x`에 적용한다. ε=0에서는 입력이 동일하지만
`f(D(x))`는 원래 `f(x)`와 다를 수 있다. 이를 방어의 정상 성능 손실로 기록한다.

## 다음 실제 평가 계약

같은 manifest 순서/모델 hash를 확인하고 다음 네 조건을 모두 저장한다:
1. 원래 모델 정상 입력 `f(x)`
2. 방어 모델 정상 입력 `f(D(x))`
3. 원래 모델 대상으로 생성한 FGSM을 방어에 전달 `f(D(A_f(x)))`
4. 방어를 알고 생성한 FGSM `f(D(A_(f∘D)(x)))`

정확도 분모는 모든 평가 표본이다. 방어 ASR은 **방어 적용 정상 입력에서
맞힌 표본**을 분모로 따로 계산한다. 원래 모델 ASR 분모와 혼용하지 않는다.
모델 간 직접 비교에는 양쪽 정상 정답 교집합도 별도로 보고한다.
분모 0은 0%가 아닌 null로 표시한다. 원래 정상 오답의 회복/정상 정답의
방어 후 손실도 따로 집계한다. 클래스별 표본 수와 분모를 함께 제공한다.

두 모델, 기존 기록된 ε=0/0.01/0.03/0.05만 후속 평가한다. 테스트셋으로
커널을 고르거나 튜닝하지 않는다. 새 결과는 별도 experimental 위치에만
저장하고 원본·가중치 전후 hash 및 전체 테스트/두 감사를 확인한다.
이 PR은 전체 데이터 실행기·결과를 추가하지 않는다. 먼저 이 작은 구성요소를
검증하고, 실제 데이터 평가 연결은 별도 단계로 진행한다.

FGSM 한 단계만 통과해도 일반적 방어 성공을 주장할 수 없다. 반복 공격 등
더 강한 방어 인지 공격 평가가 필요하며 선박 운항/충돌 방지를 검증하지 않는다.

## 근거

- TensorFlow depthwise convolution: https://www.tensorflow.org/api_docs/python/tf/nn/depthwise_conv2d
- TensorFlow reflect padding: https://www.tensorflow.org/api_docs/python/tf/pad
- Athalye et al., gradient masking 경고: https://arxiv.org/abs/1802.00420
