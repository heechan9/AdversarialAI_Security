# FGSM 공식 실험 조건 잠정안 및 멘토 검토 자료

> **상태: Team proposal / mentor approval pending**
>
> 이 문서는 팀 내부 잠정안과 기존 예비평가 결과를 정리한 검토 자료다. 아래 FGSM 수치는 아직 공식 결과가 아니며, 멘토 승인 후 동일 계약으로 재실행하여 확정한다.

## 1. 팀 잠정안

- 공격: untargeted FGSM, true-label categorical cross-entropy, 정확히 1-step
- 후보 ε: `0, 0.01, 0.03, 0.05`
- 입력·출력 범위: `[0,1]`
- 제약: 표본별 `L∞ ≤ ε + 1e-6`, 공격 후 `[0,1]` clipping
- 평가 대상: 동일한 781장 테스트셋과 10개 클래스
- 모델: CNN(128×128×3), MobileNetV2(224×224×3)
- Robust Accuracy·Macro F1: 전체 781장을 분모로 계산
- Untargeted ASR: clean-correct 표본만 분모로 계산
  - CNN: 504장
  - MobileNetV2: 613장
- ε=0: clean prediction, accuracy drop, ASR, `L∞`의 대조조건

이 후보군은 낮은 강도부터 상대적으로 높은 강도까지 동일한 정규화 픽셀 공간에서 비교하고, 이미 생성된 예비평가와 공식 재실행의 연속성을 유지하기 위한 팀 잠정안이다.

## 2. Canonical 예비평가 결과

원자료: `results/attacks/provisional/fgsm_comparison_summary.csv`

| 모델 | ε | Clean Acc. | Robust Acc. | Accuracy Drop | Untargeted ASR | 성공/분모 |
|---|---:|---:|---:|---:|---:|---:|
| CNN | 0.00 | 0.645327 | 0.645327 | 0.000000 | 0.000000 | 0/504 |
| CNN | 0.01 | 0.645327 | 0.416133 | 0.229193 | 0.355159 | 179/504 |
| CNN | 0.03 | 0.645327 | 0.243278 | 0.402049 | 0.623016 | 314/504 |
| CNN | 0.05 | 0.645327 | 0.202305 | 0.443022 | 0.688492 | 347/504 |
| MobileNetV2 | 0.00 | 0.784891 | 0.784891 | 0.000000 | 0.000000 | 0/613 |
| MobileNetV2 | 0.01 | 0.784891 | 0.124200 | 0.660691 | 0.841762 | 516/613 |
| MobileNetV2 | 0.03 | 0.784891 | 0.131882 | 0.653009 | 0.831974 | 510/613 |
| MobileNetV2 | 0.05 | 0.784891 | 0.161332 | 0.623560 | 0.794454 | 487/613 |

검증된 예비 계약:

- ε=0에서 두 모델 모두 clean accuracy 재현
- ε=0에서 `accuracy_drop=0`, `ASR=0`, `linf_max=0`
- 전체 ε에서 `linf_max ≤ ε + 1e-6`
- 테스트 이미지 781장과 두 모델의 SHA-256 무결성 검증
- ASR은 clean-correct 표본만 분모로 사용

## 3. 논문에 사용할 수 있는 잠정 서술

> CNN과 MobileNetV2에 대해 ε∈{0, 0.01, 0.03, 0.05}의 untargeted FGSM 예비평가를 수행하였다. 공격은 true label 기반 categorical cross-entropy의 입력 gradient 부호를 이용한 단일 단계 방식으로 구현하였고, 입력 및 출력은 [0,1] 범위로 제한하였다. 모든 표본에서 L∞≤ε+10⁻⁶ 조건을 확인하였다. 공격성공률은 clean 상태에서 정분류된 표본만을 분모로 계산하였다. ε=0에서는 두 모델 모두 clean 결과를 재현하였고 accuracy drop, ASR 및 최대 L∞가 모두 0이었다. 본 수치는 멘토의 ε 범위 승인 전 예비 결과이며, 공식 결론은 승인된 동일 조건의 재실행 이후 확정한다.

## 4. 예비 관찰과 해석 제한

- CNN은 ε 증가에 따라 Robust Accuracy가 감소하고 ASR이 증가하는 패턴을 보였다.
- MobileNetV2는 ε=0.01에서 큰 성능 하락을 보였지만, 이후 ε 증가에 따라 ASR이 감소하는 비단조 패턴이 관찰됐다.
- MobileNetV2의 비단조 패턴을 overshoot 또는 특정 원인으로 확정하지 않는다. 필요하면 공식 실험과 분리된 보조 ε 실험을 사전등록한다.
- CNN과 MobileNetV2의 입력 해상도가 다르므로 모델 구조만의 인과효과로 해석하지 않는다.
- 높은 clean accuracy가 모든 조건에서 높은 adversarial robustness를 보장한다고 일반화하지 않는다.
- MobileNetV2 학습 당시 실제 전처리는 학습 코드가 없어 미확정이며, 평가와 handoff 명세에서 사용한 `rescale=1./255`만 확인된 사실로 기록한다.
- 공공 AIS 자료는 해양 맥락 참고자료이며, 이미지 라벨·모델 학습·Clean/FGSM 성능의 근거로 사용하지 않는다.

## 5. 멘토 확인 요청 항목

1. ε 후보 `0, 0.01, 0.03, 0.05`를 공식 FGSM 범위로 확정해도 되는가?
2. CNN·MobileNetV2에 동일한 정규화 픽셀 공간의 ε를 적용하는 현재 비교계약을 유지해도 되는가?
3. MobileNetV2 비단조 패턴 확인을 위한 보조 ε 실험이 필요한가?
4. 이번 논문 범위를 FGSM 공식 평가까지로 제한하고 BIM·PGD·JSMA 및 방어기법은 후속연구로 둘 것인가?

## 6. 승인 후 공식화 절차

1. 멘토 승인 내용을 날짜·조건과 함께 기록한다.
2. `docs/EXPERIMENT_CONTRACT.md`와 `configs/experiment.yaml`의 proposed 표시를 동일하게 갱신한다.
3. 데이터·모델 hash와 실행환경을 다시 확인한다.
4. 승인된 ε 전체를 CNN·MobileNetV2에 대해 재실행한다.
5. 공식 산출물을 `results/attacks/`에 새로 생성한다. 예비 산출물은 삭제하거나 덮어쓰지 않는다.
6. Accuracy, Robust Accuracy, Accuracy Drop, ASR, Macro F1, `L∞`를 canonical CSV/JSON에서 재계산한다.
7. 연구근거 감사 CLI와 전체 테스트를 실행하고 non-zero 오류가 없는지 확인한다.
8. 논문의 표·그래프·본문 수치를 공식 canonical 산출물로 교체한다.
9. 공식 결과와 예비 결과의 차이가 있으면 숨기지 않고 실행환경 및 원인을 함께 기록한다.

## 7. 변경 통제

멘토 승인 전에는 다음을 수행하지 않는다.

- 예비 결과를 공식 결과로 이름 변경
- 유리한 ε만 선택하거나 불리한 결과 삭제
- BIM·PGD·JSMA·방어기법을 FGSM 공식 결과와 혼합
- 모델·가중치·전처리·테스트셋 변경
- 공공 AIS 자료를 Clean 또는 FGSM 성능 근거로 연결
