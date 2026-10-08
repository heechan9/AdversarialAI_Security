# GPU 확장 실험 저장 결과와 복구

2026-10-05 기록. 실행 ID: `full-gpu-20261004T120332`.
실험 소스: `e974c4bb21ac2041dfbb93fdb18c1983dd6e402e`.

## 확인된 범위

Colab T4 실행은 종료됐으며 2026-10-05 14:45 KST 재연결 시도에서도 GPU 사용량 제한을 확인했다. PGD 보고서의 `RUNNING`은 중단 전에 저장된 값으로 실시간 실행을 뜻하지 않는다.

| 단계 | 저장 증거 및 감사 | 남은 작업 |
|---|---|---|
| BIM | 16/16조건, `FULL_OUTPUTS_CONSISTENT` | 전체 통합 결과와 함께 최종 검토 |
| PGD | 13/16조건, `PARTIAL_OUTPUTS_ONLY` (2026-10-05 두 번째 복구 `recovery-20261005T165652`, 실행 소스 3294dcc; 이전 부모는 11조건·e974c4bb) | MobileNet Mean ε=.01/.03/.05 |
| CNN 무방어 JSMA | GPU 전체 완료 증거 없음 | 781장 |
| MobileNet PGD7 학습 | GPU 완료 epoch 증거 없음 | 3 epoch |
| MobileNet 원본/학습 비교 | GPU 완료 증거 없음 | test 781장 평가 |

2026-10-05 저장된 BIM·PGD 보고서와 27개 CSV를 `verification/iterative_result_audit.py`로 재검산했다. 모델 식별 해시, manifest/classes 해시, CSV 해시, 조건별 781장 순서·커버리지, 클래스, L∞ 범위, 정확도 및 ASR 재계산을 통과했다. 이는 저장 증거의 일관성 감사이며 원본 모델 독립 재추론 또는 외부 독립검증 승인이 아니다. 확률 배열 비교도 포함하지 않는다.

## 조건 단위 복구

1. 무료 GPU 할당과 실제 TensorFlow GPU 인식을 확인한다. 원래 전체 실행 셀은 재실행하지 않는다.
2. 비공개 Drive의 부모 PGD `run.json`(13조건, `recovery-20261005T165652/pgd/outputs`)과 보고서에 등재된 13개 CSV, `parent-run.json`을 별도 디렉터리에 내려받아 동결한다. 11조건 부모(`full-gpu-20261004T120332-pgd`)에서 다시 시작하지 않는다. 부모 파일을 수정하거나 잔존 `RUNNING`을 완료로 바꾸지 않는다.
3. 부모 디렉터리를 `verification/iterative_result_audit.py`로 감사한다. 모델·입력 파일은 기존 무결성 검사를 통과해야 한다.
4. 기존 `--resume-from` 기능으로 새 실행 ID를 사용한다. PGD 설정은 steps=20, step-size=.005, restarts=5, seed=2026, batch-size=16으로 유지한다. 데이터 경로는 검증된 test 781장 디렉터리다.
5. `continuation.py`는 부모 보고서 해시와 소스 커밋, 상속 조건 수를 기록하고 완성된 조건만 복사한다. 부모에 없는 MobileNet Mean ε=.01/.03/.05 3조건만 새로 수행한다. 노트북은 입력한 실행 SHA가 부모 보고서의 `source_commit`(3294dcc)과 같을 때만 진행한다.
6. Python/platform/TensorFlow/Keras/NumPy 및 기록된 환경변수가 부모와 다르면 기존 복구 검사가 중단된다. 검사를 해제하거나 환경이 다른 결과를 같은 실행으로 합치지 않는다. 별도 실행·별도 출처로 처리 방식을 검토한다.
7. PGD 16조건 감사 후 JSMA, 학습 3 epoch, test 평가를 수행하고 각 단계의 완료 산출물을 확인한다. 로그·체크포인트를 비공개 Drive에 저장한다.

복구 명령의 형태(검증된 환경·경로를 준비한 뒤 실행):

```bash
python -m adversarial_ai.evaluation.iterative_evaluation \
  --attack pgd --steps 20 --step-size .005 --restarts 5 \
  --seed 2026 --batch-size 16 --run-id NEW_UNIQUE_RUN_ID \
  --data-dir /verified/test --resume-from /verified/parent-pgd
```

## 공개 및 병합 기준

공개 저장소에는 검토한 요약·검증 근거만 반영한다. 비공개 원본 이미지, 입력 ZIP, 모델 가중치는 업로드하지 않는다. CPU 부분 결과는 이 GPU 실행과 분리한다.

전체 5단계의 실제 저장 증거 감사와 최신 커밋 CI 통과 전까지 PR #78은 draft를 유지한다. 이 문서 갱신은 실험 전체 완료 또는 최종 병합을 의미하지 않는다.

## 2026-10-09 상태 대조

- 13/16 PGD 부모 `run.json`은 비공개 Drive 원본을 직접 읽어 확인했다: `status=RUNNING`, 조건 13개(CNN 8, MobileNet Gaussian 4, MobileNet Mean ε=0), `source_commit=3294dcc5d6e34330be36b16d950d27e49e7a32ec`, 상속 11조건·부모 소스 e974c4bb. CSV 바이트와 해시 재감사는 이번 세션에서 수행하지 않았다(저장 결과 감사 통과는 작성자 Codex 보고).
- 이 Drive 폴더에서 2026-10-05 18:57 UTC 이후 갱신된 PGD 산출물과 새 복구 폴더는 확인되지 않았다. GPU 런타임 상태는 이 세션에서 확인할 수 없다.
- 노트북 재빌드: 13조건 부모를 상속하고 실행 SHA–부모 소스 일치를 강제한다. 이는 코드 준비이며 GPU 실행 완료가 아니다.
