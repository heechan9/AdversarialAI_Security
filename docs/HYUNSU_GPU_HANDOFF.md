# GPU 실행 인계 안내 (현수 배정 아님)

> 현수는 AMD GPU 환경이라 CUDA 실행을 맡지 않는다. 현수의 역할은 CPU로 가능한 독립 검토이며 [검토 묶음](HYUNSU_REVIEW_PACKET.md)을 사용한다. 이 문서는 NVIDIA GPU 접근이 있는 실행자용 절차다.

이 문서는 전달용 초안이며 실제로 메시지를 보내거나 독립검증을 요청한 기록이 아니다.

## 요청 범위

기존 GPU BIM 16조건과 PGD 13조건의 저장 증거는 작성자 감사를 통과했다(PGD 13/16은 부분 결과). 남은 PGD MobileNet Mean ε=.01/.03/.05, CNN 무방어 JSMA 781장, MobileNet PGD7 학습 3epoch, 원본/학습 모델 test781 비교를 실행한다.

먼저 GPU 모델·VRAM, OS, Python/TensorFlow/Keras/NumPy 버전을 확인한다. Colab 계정의 할당 제한과 별개로 본인의 사용 가능한 GPU 환경이 필요하다. 유료 계산 자원을 자동 구매하지 않는다.

## 실행

Colab에서는 `notebooks/AdversarialAI_Recovery_GPU.ipynb`를 사용한다. 부모 실행 폴더와 비공개 입력 ZIP에 이미 접근 가능한 계정에서 실행해야 한다. 새 실행은 검토한 40자리 실행 SHA를 명시적으로 입력한다. 노트북은 checkout 뒤 SHA를 검증하고 비공개 execution-source.json에 기록한다. 이미 실행 중인 3294dcc 세션은 재시작하거나 소스를 바꾸지 않는다. 각 셀을 순서대로 실행하고 실패한 셀이나 전체 노트북을 무조건 재실행하지 않는다.

로컬 GPU에서는 [복구 절차](GPU_RECOVERY_20261005.md)의 PGD 명령과 노트북의 단계별 명령을 사용한다. 비공개 입력 경로를 해당 환경에 맞추고 모델·manifest 무결성을 먼저 검사한다. 부모와 환경이 다르면 기존 `--resume-from` 검사가 중단된다. 검사를 제거하지 말고 환경 차이를 기록해 별도 실행으로 검토한다. CPU 결과를 GPU 완료 결과에 합치지 않는다.

## 반환할 자료 — 비공개 Drive

- PGD: `run.json`, `parent-run.json`, 16개 조건 CSV, 단계 로그 및 GPU probe 기록.
- JSMA: `run.json`과 생성된 JSONL 등 전체 실행 산출물, 단계 로그.
- 학습: `training.json`, `split-audit.json`, `best.keras`, 완료 epoch 체크포인트, 단계 로그.
- 평가: `evaluation.json`, `original.csv`, `trained.csv`, 단계 로그.
- 코드 SHA, 실행 환경, 실행 시작·종료 시각, 중단 여부.

`verification.recovery_stage`는 30초 간격으로 비공개 백업을 갱신하지만 런타임 종료 시 마지막 변경이 손실될 수 있다. 백업 파일 자체가 완료 증거는 아니다. 재중단 시 저장된 완성 조건·epoch를 재감사한 후 복구한다.

## 최종 감사

```bash
python -m verification.full_extension_audit \
  --bim /private/bim --pgd /private/pgd --jsma /private/jsma \
  --training /private/training --evaluation /private/evaluation
```

감사는 private `best.keras`의 실제 바이트 해시까지 확인한다. 공개 저장소에 원본 이미지·입력 ZIP·가중치를 올리지 않는다. 감사 통과 후에도 GPU 로그·실행 출처와 최신 CI를 확인해야 한다. 이번 실행 지원은 외부 독립검증 승인과 구분한다.
