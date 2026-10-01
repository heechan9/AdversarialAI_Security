# 후속 연구 실행 기록 — 2026-10-01 중간 체크포인트

이 문서는 `results/extensions/checkpoints/20261001/index.json`의 촬영 시점 상태다. 실시간 실행 현황이나 최종 성능 표가 아니다. ACK 제출본과 기존 FGSM/Stage B 결과는 변경하지 않는다.

## 실제 확보·실행 근거

- 사용자 보관 ZIP에서 원본 모델 2개·이미지 781장을 복구했고 기존 manifest의 SHA-256과 모두 일치했다.
- 초기 BIM 실행은 절대 모델 경로와 manifest 상대 경로가 달라 입력 검사에서 ERROR로 중단됐다. 추론 전 오류이며 해당 run.json을 보존했다. PR #61로 수정했다.
- BIM: 10 steps, step-size 0.005, clean start, batch 32. PGD: 20 steps, step-size 0.005, 5 restarts, seed 2026, batch 16. 모두 epsilon 0/0.01/0.03/0.05와 두 필터·다섯 경로를 계획한다. 탐색 조건이며 최적 공격 강도라고 주장하지 않는다.
- 실제 실행 코드는 `514fae90f1e5188babe2f729258dea7e9014fddc`. Linux/TF 2.21.0/Keras 3.15.1, CPU 스레드 설정 등은 각 run.json에 기록됐다. 연구 수행 PC 재실행이나 외부 사람 독립 검증으로 이름을 바꾸지 않는다.
- 체크포인트의 BIM/PGD run.json과 이미 완료된 조건 CSV만 복사했다. 상태 RUNNING은 캡처 당시 상태이며 이후 지속 실행 또는 완료를 보증하지 않는다.
- `audit.json`은 저장된 CSV의 해시, 표본 순서·정답, 클래스 범위, perturbation, 정확도/ASR을 별도 재계산한 결과다. **PARTIAL_OUTPUTS_ONLY**이며 모든 16조건 완료 판정이 아니다. 확률·공격 배열 비교도 아니다.

## JSMA·학습

- JSMA 원본 CNN 1장·1회 기울기/feature-pair 실행을 확인했다. 표본은 Clean에서도 오분류됐고, 목표 미도달·step_limit으로 끝났다. 따라서 표적 ASR 분모는 0(null)이다. 성능 평가나 방어 성공 사례가 아니다.
- JSMA 및 PGD 학습 코드는 PR #62로 추가했다. 별도 합성 데이터에서 실제 학습·모델 저장·재로딩·원본 불변을 테스트했다.
- 보관된 전달 ZIP에는 학습·검증 이미지가 없으며, 확인한 추가 자료에서도 별도 선박 train/validation 자료를 확보하지 못했다. **실제 선박 적대적 학습은 해당 자료 대기**다. 테스트 781장을 재분할해 학습용으로 쓰지 않는다.

## 다음 확인

계산 종료 후 각 원본 run.json과 전체 CSV를 수신·검사하고 새 체크포인트를 만든다. 현재 중간 기록을 덮어쓰지 않는다. 아래 검사는 전체 조건이 없으면 전체 완료 판정을 거부한다.

```bash
python verification/iterative_result_audit.py results/extensions/checkpoints/20261001/bim
python verification/iterative_result_audit.py results/extensions/checkpoints/20261001/pgd
```

계산 비용이 큰 실험이며 CPU 환경에서 상당한 시간이 소요된다. JSMA의 정확한 pair 탐색도 별도 계산 예산이 필요하다. 코드 구현·단위 검사·부분 실행·전체 평가·독립 재현을 구분한다.
