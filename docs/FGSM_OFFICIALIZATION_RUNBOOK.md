# FGSM 공식화 준비 절차

이 문서는 멘토가 epsilon 범위를 확정한 뒤 **새 공식 실험을 실행하기 전** 확인할
절차를 정의한다. 현재 결과와 `configs/experiment.yaml`의 epsilon은 provisional이며,
이 문서와 준비 점검기는 이를 공식 결과로 승격하지 않는다.

## 승인 전 상태

`configs/fgsm_official_contract.json`은 의도적으로 `pending_mentor_approval` 상태이고
epsilon, 승인자, 승인시각, source commit, run ID가 비어 있다. 준비 점검은 이 상태를
실패(exit code 2)로 보고해야 정상이다. 점검기는 모델을 로드하거나 결과를 생성하지 않는다.

```bat
set PYTHONPATH=src
python scripts\check_fgsm_official_readiness.py
```

## 멘토 승인 후 순서

1. 별도 브랜치에서 계약 파일에 승인 근거, 확정 epsilon, 실행할 40자리 commit SHA와
   새 run ID를 기록한다.
2. 로컬 원본 이미지 781장의 manifest SHA와 두 `.h5` 모델 SHA가 모두 일치하는지
   Research Evidence Audit으로 확인한다.
3. 준비 점검이 exit code 0인지 확인한다. 기존 official run 디렉터리가 있으면 새 run
   ID를 사용하며 덮어쓰지 않는다.
4. 고정된 commit에서 CNN과 MobileNetV2를 동일 계약으로 실행한다.
5. 표본 CSV, 요약, confusion matrix, metadata, 모델 weight 실행 전후 SHA를 새
   `results/attacks/official/<run_id>/`에 저장한다.
6. 전체 pytest, Research Evidence Audit, Paper Claim Audit을 실행한다.
7. 팀 검토가 끝난 뒤에만 논문 스냅샷의 FGSM 상태와 수치를 official 근거로 갱신한다.

실행 실패나 감사 실패 시 일부 산출물을 공식 결과로 사용하지 않는다. provisional
디렉터리는 보존하며 복사·덮어쓰기 방식으로 공식화하지 않는다.
