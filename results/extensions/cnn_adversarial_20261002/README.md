# CNN 적대적 학습 및 테스트 평가 — 2026-10-02

ACK 제출 이후의 별도 GPU 후속 실험이다. CNN 학습 3에폭과 테스트 781장의 일반/PGD7 비교를 완료했다. MobileNet 학습, BIM·PGD 전체 조건, JSMA 및 외부 독립 재현 완료를 뜻하지 않는다.

| 테스트 정확도 | 원본 CNN | 적대적 학습 CNN | 차이 |
|---|---:|---:|---:|
| 일반 이미지 | 504/781 (64.53%) | 540/781 (69.14%) | +4.61%p |
| PGD7 | 87/781 (11.14%) | 145/781 (18.57%) | +7.43%p |

PGD는 epsilon=0.03, step size=0.005, 7 steps, 1 restart, seed=2026+batch, batch=8이며 필터를 사용하지 않았다. 두 모델 각각에 대해 white-box 공격을 새로 생성했다. 원래 맞힌 이미지 중 공격 성공률은 82.74% → 73.15%다. 이는 제한된 공격 설정에서의 개선이며 충분한 방어, 강한 다중 재시작 공격에 대한 견고성 또는 통계적 유의성을 입증하지 않는다.

## 학습과 모델 선택

- 학습 6,147장, 검증 689장, 테스트 781장. 학습/검증/테스트 정확한 파일·RGB 중복 검사를 통과한 분할을 사용했다. 근접 중복은 미검사다.
- PGD7 epsilon=0.03으로 clean/adversarial loss를 50:50 혼합, Adam learning rate=1e-5, batch=8, seed=2026, 3 epochs.
- 검증 PGD 정확도로 선택한 best epoch=3. 검증 일반 정확도 90.13%, PGD 31.64%이며 위 테스트 수치와 구분한다.
- 실행 코드: `76fc5e5debfc02269e236d15db5d06325802379a`. Colab Tesla T4, Python 3.13, TensorFlow 2.21.0, Keras 3.15.1. CPU/배치32와 동일 재현을 주장하지 않는다.
- 기존 원본 모델의 과거 train/test 노출 가능성은 이번 추가학습으로 제거되지 않는다. 원본 데이터의 테스트 중복과 source-train 중복 민감도는 기존 후속 감사 문서를 참조한다. 여기 수치는 고정 781장 전체 기준이다.
- 모델은 비공개 보관하며 공개 파일에는 모델 해시만 포함한다.

## 보존 파일과 확인

`training.json`은 학습 종료 당시 원본 기록이므로 `TRAINED_NOT_TEST_EVALUATED`를 그대로 유지한다. 그 뒤 수행한 `evaluation.json`의 `COMPLETED`가 이번 테스트 평가 완료 근거다. 두 파일의 모델 해시가 연결된다. `original.csv`, `trained.csv`는 Drive 원본 바이트를 보존한다.

```bash
python verification/cnn_pgd7_saved_audit.py
```

감사는 2×781행의 해시, manifest 경로·정답, 클래스 범위, 교란 범위, 정확도·ASR과 모델 식별자를 재계산한다. 저장 결과 감사이며 독립 GPU 재실행은 아니다.

## 재실행

실제 Colab 실행 셀에서 추출한 평가기를 `verification/cnn_pgd7_test_evaluation.py`로 보존했다. 저장 위치만 CLI 인자로 바꾸었으며 이 인자화 버전은 구문 검사만 수행했다. 위 소스 커밋 checkout에 스크립트를 복사하고 원본 모델, 검증된 test 데이터, `training.json`과 `best.keras`를 준비한다. GPU 라이브러리 경로 설정은 GPU 노트북을 따른다.

```bash
PYTHONPATH=src MPLBACKEND=Agg python verification/cnn_pgd7_test_evaluation.py \
  --trained-dir /private/cnn-training \
  --test-dir /private/test \
  --output-dir /private/new-cnn-evaluation
```

테스트 결과를 본 뒤 추가 학습·모델 선택은 하지 않았다. MobileNet 및 추가 공격 실험은 사용자 요청으로 보류했다. 기존 논문·FGSM·Stage B 결과는 변경하지 않았다.
