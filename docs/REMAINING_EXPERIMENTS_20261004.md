# 2026-10-04 잔여 실험 실행 설정

## 18:22 KST 요청 이후 확인한 현재 상태

앞선 재실행 세션과 대기·백업 프로세스는 더 이상 존재하지 않는다. RUNNING 보고서는 현재 실행의 증거가 아니다. 파일은 남아 있으며 저장 자료 감사에서 BIM 13/16, PGD 2/16, JSMA 71/781장만 확인했다. 신규 BIM 9/25 batch·PGD 6/49 batch 로그는 완성 조건으로 계산하지 않는다. MobileNet 학습은 시작되지 않았다.

연결된 Hugging Face 계정은 Pro가 아니며, Jobs 조회도 UNAVAILABLE을 반환했다. 유료 작업은 제출하지 않았다. 지속 실행 가능한 환경이 확보되지 않아 전체 실험 완료 및 최종 병합은 차단된 상태다.

`notebooks/AdversarialAI_Full_Extensions_GPU.ipynb`를 추가했다. GPU에서 원본 모델 BIM·PGD 각 16조건, CNN 무방어 JSMA 781장, MobileNet PGD7 3 epoch 학습, 원본/학습 모델 PGD7 비교를 순차 실행하고 Drive에 중간 결과를 복사한다. 소스는 e974c4bb21ac2041dfbb93fdb18c1983dd6e402e로 고정했다. GPU에서는 기존 CPU 부분 결과를 계승하지 않는다. Python 구문 검사는 통과했으나 실제 GPU 통합 실행은 미검증이다. 런타임 연결 종료 가능성이 있으며, 새 실행용 노트북이므로 중단 복구는 결과를 감사한 뒤 별도로 수행한다.


## 작업 환경 정리 후 복구

2026-10-04 작업 환경 정리로 앞선 실행 프로세스와 임시 결과가 소실되었다. 마지막 로그는 BIM 신규 첫 조건 23/25 batch, PGD 신규 첫 조건 17/49 batch, JSMA 107/781장이지만 로그만으로 결과를 복원하거나 완료로 인정하지 않는다. GitHub에 보존된 BIM 13/16, PGD 2/16 조건부터 다시 이어 실행한다. JSMA는 새로 시작하며 MobileNet 학습 완료 epoch는 없다.

원래 준비 ZIP에서 train6147/valid689/test781과 두 원본 모델을 복원하고 모델 SHA256을 확인했다. JSMA는 원자적 보고서 저장과 동일 코드·모델·데이터·환경·설정의 감사된 표본 prefix 재개를 지원한다. 과거 환경 정보가 없는 보고서는 이 재개 경로에서 거부한다. 큐는 JSMA 원자료 감사도 통과해야 학습을 시작한다.

`verification/remaining_checkpoint_backup.py`는 실행 결과만 정기적으로 별도 복구 ZIP에 저장한다. 학습 가중치가 포함될 수 있으므로 복구 ZIP은 개인 저장 공간에만 보관하며 공개 GitHub에 올리지 않는다. 업로드 실패/불확실 시 자동 재시도하지 않는다. 저장 성공한 ZIP만 복구 근거이며, 실행 환경 종료 뒤 프로세스가 자동 유지되는 것은 아니다. 최종 실험 완료나 병합은 아직 아니다.

사용자가 BIM·PGD 잔여 조건, JSMA 전체 평가, MobileNet 적대적 학습의 실제 실행을 요청했다. 결과는 기존 제출본과 분리한다.

- BIM: 기존 evening 13/16조건을 감사하여 계승. 10 steps, step .005, batch32, 나머지 3조건 실행.
- PGD: 기존 pc 2/16조건을 감사하여 계승. 20 steps, 5 restarts, step .005, seed2026, batch16, 나머지 14조건 실행.
- 두 실행 모두 기존 Python 3.12.14/TF2.21.0/Keras3.15.1/NumPy2.3.5 및 CPU intra2/inter1 조건과 manifest를 대조한 뒤 계승한다.
- JSMA: CNN 무방어 781장, target=(true+1)%10, theta=1, gamma=.01. 49,152채널 원소 중 최대491개 변경; 최대246회 pair 탐색. 전체 pair를 정확 탐색하며 top-k 근사는 사용하지 않는다. 이 조건의 전체 표본 평가이며 MobileNet·필터 조건까지 전체를 실행했다는 뜻이 아니다.
- MobileNet: manifest의 원본 모델 SHA256 `58c4878fa1480035d0bd5a63f8c3e22beac3a03f27f1aada6690b27f167129ae` 확인. 기존 준비 ZIP에서 train6147/valid689 복원, 고정 test781과 정확 raw/RGB 중복 재검사.
- 학습: 3 epochs, PGD7 epsilon .03/step .005/1 restart, seed2026, batch8, Adam1e-5, clean/adv loss .5/.5. validation PGD 정확도로 최적 epoch 선택. 기존 모델의 trainable 속성을 유지한다.
- 테스트: 선택된 MobileNet과 원본에 각각 새 PGD7 공격, test781, batch8, seed2026+batch, 필터 없음. 모델 해시·원본 가중치 불변·Linf 범위를 검증한다. CPU 실행이며 독립 승인으로 취급하지 않는다.

## 실행과 저장

`results/extensions/iterative/bim-complete-20261004` 및 `pgd-complete-20261004`, `results/extensions/jsma/cnn-full-20261004`가 신규 실행 경로다. 기존 근거를 덮어쓰지 않는다.

MobileNet 첫 시도 `mobilenet-pgd7-20261004`는 동시 실행 메모리 압박 때문에 첫 epoch 완료 전에 프로세스를 중지했다. 완료 epoch나 복구 checkpoint는 없다. 원본 training.json의 RUNNING은 종료 핸들러가 기록되지 않은 잔여 상태이므로 현재 실행으로 해석하지 않는다.

`verification/remaining_experiments_queue.py`는 세 평가의 종료를 기다린 뒤 두 반복공격 결과를 감사하고, 별도 `mobilenet-pgd7-20261004-serial`에서 처음부터 학습한다. 이어 `verification/mobilenet_pgd7_test_evaluation.py`로 별도 테스트를 실행한다. 학습은 epoch 단위 모델·optimizer checkpoint를 보존한다. 실패한 의존 작업은 자동으로 완료 처리하지 않는다.

큐가 끝나도 상태는 `COMPLETED_AWAITING_RESULT_AUDIT_AND_PUBLICATION`이다. 사용자에게 완료로 보고하기 전 최종 원자료 감사·GitHub/Drive 반영이 필요하다. 보고서에 RUNNING이 남은 것만으로 프로세스 생존을 단정하지 않는다. 실행 환경 종료 시 자동 지속을 보장하지 않는다.
