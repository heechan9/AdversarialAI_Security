# 정상 추가학습 대조 실험 — 실행 준비안 v0.1

작성: 2026-10-24. 실제 학습·추론은 이번 문서 작업에서 실행하지 않았다.
PR87 원격 확인: open, head db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf. 이 head의 안내를 읽었으며 현재 main 반영이나 새 학습 완료를 주장하지 않는다.

## 질문과 실험군

질문: 추가 학습 노출을 맞춘 상태에서도 적대적 손실을 사용한 CNN의 강건성 개선이 유지되는가?

| 군 | 초기화·학습 | 역할 |
| --- | --- | --- |
| Original | 고정 원본 CNN, 추가학습 없음 | 기존 참조점; 추가학습 효과를 통제한 군은 아님 |
| Clean-only | 동일 원본 CNN에서 정상 이미지 손실로 새 학습 | 추가 학습 노출 대조군 |
| PGD-mixed | 동일 원본 CNN에서 clean/PGD 손실 50:50으로 새 학습 | 핵심 비교군 |

Clean-only와 PGD-mixed를 같은 새 소스·환경에서 둘 다 실행한다. 과거 GPU 학습 결과를 새 clean-only와 짝지어 원인 분리 결과로 사용하지 않는다. 각 seed에서 같은 초기 가중치를 로드하며 두 군의 난수 소비 궤적이 같다고 가정하지 않는다.

## 제안 고정 설정 — 실행 전 검토·확정

- 첫 대상: CNN, 128×128 RGB, 입력 [0,1], 10클래스.
- 기존 기록과 연결할 탐색 재현: train 6,147/validation 689/test 781. 실제 분할 해시가 기존 감사와 일치할 때만 이 크기를 사용한다. 역사적 테스트는 이미 관찰된 자료로 표시한다.
- Adam, learning rate 1e-5, batch 8, 3 epochs. 학습 seed 2026/2027/2028: 두 학습군 × 3 seed = 새 학습 6회. 환경별 시간·메모리는 미측정이며 비용 견적 후 실행 예산을 확정한다.
- 혼합군 학습 PGD7: Linf .03, step .005. 나머지 공격 seed·배치·시작·재시작 규칙은 고정한 소스/config에서 추출해 실행 manifest에 기록한다. 문서에서 누락된 값을 임의 추정하지 않는다.
- 두 군 동일 PGD validation으로 best epoch 선택, 동점이면 가장 이른 epoch. Clean-only는 학습 손실의 이름이며 validation은 PGD를 사용한다.
- 동일 epochs/update 수는 노출을 맞추는 기준이다. 혼합군 공격 생성의 추가 계산 비용까지 같아지는 것은 아니다. GPU 시간·update 수·공격 질의/경사 횟수·최대 메모리를 별도 보고한다.

## 평가 계획

주 비교는 PGD-mixed minus clean-only의 공격 후 정확도 차이로 정한다. 제안 주 평가: 필터 없는 white-box PGD50, Linf .03, step .005, random starts 5회, 평가 seed 4101. 구현이 각 표본의 최악 후보를 보존하는지·예산 준수·epsilon0 계약을 먼저 확인해야 한다. 이 조건은 준비안이며 아직 구현 검증·실행되지 않았다.

각 조건·모델은 자신의 경사로 공격을 새로 생성한다. 10/20/50 steps 및 재시작별 포화 여부는 validation에서 확인하고 최종 공격 설정을 test 실행 전에 고정한다. 주 설정을 바꾸면 프로토콜 버전과 이유를 기록한다. PGD50도 인증된 강건성은 아니다.

보조 평가: Clean 정확도·macro F1·선종별 정답 수, own-clean ASR, 두 모델 공통 clean-correct 집합의 별도 분석, Square Linf .03/1,000질의 × 평가 seed 4101/4102/4103. 다중 seed 성공 합집합의 총 질의 예산을 별도 표기한다. SurFree L2/RMS는 Linf와 직접 우열 비교하지 않는다. AutoAttack은 TensorFlow 어댑터·logit/gradient·공식 구성 호환 검증을 통과하기 전 완료 항목으로 넣지 않는다.

## 데이터와 불확실성

새 외부 데이터는 출처·사용권·라벨 대응·제외 기준·선박/장면 그룹을 먼저 고정한다. 외부 test는 튜닝에 사용하지 않는다. 기존 학습 노출 미확정은 clean-only 대조로 해결되지 않는다. 선박/장면 단위 독립성이 미확인일 때 이미지별 bootstrap CI나 McNemar p를 독립 표본 근거로 제시하지 않는다. 첫 결과는 seed별 값·범위·평균 및 분자/분모를 기술하며, 독립 단위가 확인되면 사전 확정한 그룹 단위 추론을 별도 수행한다. seed 3회만으로 강한 통계적 결론을 보장하지 않는다.

## 실행 게이트와 산출물

1. PR87의 적용 revision과 소스·입력·split·환경 해시를 고정하고 해당 환경 smoke 검사를 통과한다.
2. 사용 가능한 원본 모델과 train/validation/test 바이트를 검증한다. 권한 없는 외부 배포를 하지 않는다.
3. 각 군·seed별 새 출력 경로를 예약한다. 기존 결과를 덮어쓰지 않는다. 모든 seed와 실패·중단을 기록한다.
4. 두 학습군 완료 후 PR87의 training_control_audit로 saved pair를 확인한다. 그 감사는 새 모델 추론이나 과학적 승인과 다르다.
5. 선택된 checkpoint를 고정 후 같은 평가군으로 테스트하고 표본 결과·요약·공격 예산·환경·시간을 보존한다.
6. main과 별개인 후속 결과 디렉터리에서 감사 후 결과를 정리한다. 기존 ACK 수치와 외부 Stage B FAIL을 변경하지 않는다.

참조: https://github.com/heechan9/AdversarialAI_Security/pull/87

고정 head의 runbook: https://github.com/heechan9/AdversarialAI_Security/blob/db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf/docs/CLEAN_ONLY_TRAINING_CONTROL.md

실제 실행 명령은 선택 소스의 --help와 비공개 입력 경로를 검증한 다음 생성한다. 아직 접근하지 않은 학습 자료·GPU가 있다고 가정하거나 실행 중이라고 표시하지 않는다.
