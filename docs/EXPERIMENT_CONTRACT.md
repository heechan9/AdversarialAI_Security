# Experiment Contract

이 문서는 현재 ACK2026 논문에 사용한 실험 조건과 아직 확인되지 않은 재현 정보를 구분한다.
논문 범위와 FGSM ε는 확정됐으며, 원자료 경로의 `provisional`·`experimental` 표기는
실험 생성 당시의 이력이다. 이를 현재 범위 미확정이나 실험 미완료로 해석하지 않는다.

## 현재 확정된 논문 범위

- 모델: CNN, MobileNetV2
- 데이터: 선박 10클래스, 테스트 이미지 781장
- 기준선: 공격 없는 Clean 평가
- 공격: untargeted 1-step FGSM
- ε: `0, 0.01, 0.03, 0.05`
- 전처리 방어: 고정 3×3 가우시안 필터, 고정 3×3 평균 필터
- 비교 조건:
  - 전달 조건: 기존 FGSM 입력에 필터 적용
  - 방어 인지 조건: 필터를 포함한 경로에 대해 공격
- 지표 분모:
  - 정확도·Macro 지표: 전체 781장
  - Untargeted ASR: 해당 경로에서 Clean 입력을 맞힌 표본

위 기능 구현·기록된 실험·보존 결과 감사는 완료됐다. 원본 `.h5` 모델과 테스트 이미지
781장으로 처음부터 다시 수행하는 독립 재실행은 완료되지 않았다.

## 공통 조건

- 동일 테스트셋(781장), 동일 클래스 순서(`configs/classes.json`)을 사용한다.
- 평가 및 공격 입력 값 범위는 **[0, 1]**이다. CNN과 MobileNet 모두 2026-08-05
  Clean 재현에서 `rescale=1./255`를 사용했다.
- `configs/handoff_spec.json`도 두 모델에 `0-1 (rescale=1./255)`를 명세한다.
  다만 MobileNet 학습 코드 자체는 확보되지 않아 학습 당시 전처리의 직접 증거는 아니다.
- 두 모델에 같은 정규화 픽셀 공간의 L∞ ε를 적용한다. 입력 해상도 차이
  (CNN 128×128, MobileNet 224×224)는 비교 한계로 기록한다.

## 공격 정의

FGSM은 true-label categorical cross-entropy를 사용하는 untargeted white-box 공격이다.

`x_adv = clip(x + ε·sign(∇ₓL), 0, 1)`

- 정확히 1-step으로 실행한다.
- 각 표본에서 `L∞ ≤ ε + 1e-6`을 만족해야 한다.
- `ε=0`은 Clean prediction 일치 여부를 확인하는 대조조건이다.
- 기존 결과를 삭제하거나 유리한 ε만 선택하지 않는다.

BIM·PGD·JSMA, 적대적 학습, VLM/LLM 연동은 현재 완료된 논문 실험 범위가 아니다.
멘토 제공 MNIST FGSM 코드는 참고자료이며, 성공할 때까지 FGSM을 반복하는 동작은
1-step FGSM으로 간주하지 않는다.

## 방어 조건과 해석

필터의 효과는 전달 조건과 방어 인지 조건을 분리해 보고한다. 기존 공격 입력에서 정확도가
회복되더라도 방어 인지 공격에서 효과가 유지되지 않았으므로 일반적인 방어 성공으로
주장하지 않는다. 정상 입력에 필터를 적용했을 때의 정확도 변화도 함께 제시한다.

## 평가 지표

| 지표 | 정의 |
|---|---|
| Clean Accuracy | 공격 없는 원본 테스트셋 정확도 |
| Robust Accuracy | 공격 적용 후 올바르게 분류한 비율 |
| Accuracy Drop | Clean Accuracy − Robust Accuracy |
| Macro Precision / Recall / F1 | 클래스 불균형을 고려한 클래스별 평균 |
| Untargeted ASR | Clean 정분류 표본 중 공격 후 오분류로 전환된 비율 |

CNN의 Clean-correct ASR 분모는 504장, MobileNetV2는 613장이다.

## 확인되지 않은 재현 정보

아래 항목은 논문 범위 확정 여부와 별개의 재현 한계다.

- MobileNet 학습 당시 실제 전처리 방식: 학습 코드 미확보
- 학습 random seed: 미확인(Clean 평가는 `shuffle=False`)
- 별도 공식 실행계약의 승인자·승인시각·재실행 run ID: 연결 기록 없음
- 원본 모델·이미지를 이용한 독립 B단계 재실행: 미완료

없는 승인이나 독립 실행 기록을 소급해 만들지 않는다.
