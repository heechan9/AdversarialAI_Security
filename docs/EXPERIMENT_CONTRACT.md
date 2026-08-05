# Experiment Contract

모든 실험은 아래 계약을 따른다. 값이 "proposed"로 표시된 항목은 팀 확정 전까지 제안값이며, 확정되면 이 문서와 `configs/experiment.yaml`을 함께 갱신한다.

## 공통 조건
- 동일 테스트셋(781장), 동일 클래스 순서(`configs/classes.json`), 동일 seed 사용
- 평가 및 공격 입력 값 범위: **[0, 1]**. CNN과 MobileNet 모두 2026-08-05 clean 재현에서 `rescale=1./255`를 사용했다.
- `configs/handoff_spec.json`도 두 모델을 구분하지 않고 `0-1 (rescale=1./255)`로 명세한다. 이는 동일 전처리를 의도했다는 강한 정황이지만, MobileNet **학습 코드 자체는 아직 확인되지 않았으므로 학습 당시 전처리의 직접 증거는 아니다.**
- 두 모델에는 동일한 정규화 픽셀 공간의 L∞ ε를 적용할 수 있다. 단, 입력 해상도(CNN 128×128, MobileNet 224×224)가 다르다는 비교 한계를 결과에 함께 기록한다.

## 공격 대상 구분
| 대상 | 공격 유형 |
|---|---|
| CNN / MobileNet | **White-box Attack** (gradient 직접 접근) |
| 멀티모달 API (GPT/Claude/Gemini) | **Transfer Attack** (CNN/MobileNet이 생성한 적대적 이미지를 입력, API 내부 gradient 접근 없음) |

## 공격 기법 정의
- **FGSM**: 단일 1-step, `x_adv = x + ε·sign(∇ₓL)`
- **BIM**: FGSM을 step size α로 T회 반복
- **PGD**: BIM + random start(ε-ball 내 임의 시작점) + 매 스텝 epsilon projection
- **JSMA**: targeted white-box, **L0** 관점(변경 픽셀 수 최소화, saliency map 기반 픽셀 쌍 선택)

> 멘토 제공 MNIST FGSM 코드는 **참고자료**일 뿐이다. "성공할 때까지 FGSM을 반복" 하는 기존 노트북 동작을 그대로 단일 FGSM 결과로 사용하지 않는다 — FGSM은 정의상 1-step이며, 반복이 필요하면 그것은 BIM/PGD다.

## 평가 지표
| 지표 | 정의 |
|---|---|
| Clean Accuracy | 공격 없는 원본 테스트셋 정확도 |
| Robust Accuracy | 공격 적용 후에도 올바르게 분류한 비율 |
| Accuracy Drop | Clean Accuracy − Robust Accuracy |
| Macro Precision / Recall / F1 | 클래스 불균형(support 45~102) 고려한 클래스별 평균 |
| Untargeted ASR | **(proposed)** Clean 상태에서 정분류된 표본만을 분모로, 공격 후 오분류로 전환된 비율 |
| Targeted ASR | **(proposed)** Clean 정분류 표본 중 공격 후 지정 목표 클래스로 전환된 비율 — Untargeted와 혼용 금지 |

## 아직 확정되지 않은 것 (proposed 상태)
- ASR 분모 정의 최종 확정
- epsilon / step size / iteration 수치
- MobileNet 학습 당시 실제 전처리 방식(학습 코드 미확보)
- 학습 random seed 값(clean 평가는 `shuffle=False`로 고정)
