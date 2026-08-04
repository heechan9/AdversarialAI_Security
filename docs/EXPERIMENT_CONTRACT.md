# Experiment Contract

모든 실험은 아래 계약을 따른다. 값이 "proposed"로 표시된 항목은 팀 확정 전까지 제안값이며, 확정되면 이 문서와 `configs/experiment.yaml`을 함께 갱신한다.

## 공통 조건
- 동일 테스트셋(781장), 동일 클래스 순서(`configs/classes.json`), 동일 seed 사용
- 입력 값 범위: [0, 1] — MobileNet도 동일 전제인지는 **unconfirmed** (rescale vs `preprocess_input` 확인 필요)

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
- MobileNet 입력 값 범위 및 전처리 방식
- random seed 값
