# 현수 독립 검토 묶음 (CPU 전용)

이 문서는 전달용 초안이며 실제 송신·검토 요청·승인 기록이 아니다. GPU나 CUDA 실행은 요청하지 않는다.
검토 결과는 작성자 자체검사, 기계 CI, 독립 검토를 구분해 기록하며 이 문서만으로 독립 승인이 되지 않는다.

## 1. 검토 대상 SHA (반드시 정확히 일치시킬 것)

| 항목 | 값 |
|---|---|
| base (main) | `9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf` |
| head (PR #78 브랜치) | `<HEAD_SHA>` — 전달 시 PR 최신 head 40자리로 채운다. 다르면 중단하고 확인한다. |
| 실험 실행 소스 | `3294dcc5d6e34330be36b16d950d27e49e7a32ec` (PGD 13조건 부모의 `source_commit`) |
| 사후 감사·게시 개선 | `8d3445a630a62630075b361a12b2fac8e526cf84` 이후 커밋 — 실행 소스와 구분 |

실험 실행 소스와 사후 감사 소스를 같은 것으로 취급하지 않는다. 이전 SHA에서의 통과를 새 head의 통과로 쓰지 않는다.

```bash
git clone https://github.com/heechan9/AdversarialAI_Security.git review && cd review
git fetch origin <HEAD_SHA> && git checkout --detach <HEAD_SHA>
git rev-parse HEAD        # <HEAD_SHA>와 일치해야 함
git diff --stat 9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf <HEAD_SHA>
```

## 2. 검토 파일

- 논문 표·공개 집계: `README.md`(확장 실험 상태표), `docs/GPU_RECOVERY_20261005.md`, `results/extensions/bim_gpu_20261004/README.md`
- 공격 구현: `src/adversarial_ai/attacks/iterative.py`(BIM·PGD), `src/adversarial_ai/attacks/` 아래 JSMA
- 방어와 평가 경로: `src/adversarial_ai/defenses/`, `src/adversarial_ai/evaluation/iterative_evaluation.py`, `continuation.py`
- 지표 정의·감사: `verification/iterative_result_audit.py`, `verification/jsma_saved_audit.py`, `verification/full_extension_audit.py`
- 복구 절차: `verification/build_recovery_notebook.py`, `notebooks/AdversarialAI_Recovery_GPU.ipynb`, `verification/recovery_stage.py`
- 검토 범위 밖(GPU 필요): 실제 PGD 잔여 3조건·JSMA·MobileNet 적대적 학습·최종 평가의 실행

## 3. 수용 기준

1. 공격 조건: BIM·PGD의 steps, step size, restarts, seed, batch size가 비교 대상 간 같은지, 다른 부분은 문서에 명시됐는지.
2. 방어 경로: transfer는 f(D(x_adv)), adaptive는 필터까지 포함한 공격임을 코드가 그대로 구현하는지. `defended_clean`의 ASR은 공격 성공률이 아니라 필터로 인한 오류율임을 문서가 구분하는지.
3. 지표 분모: 정확도 분모 781, ASR 분모(깨끗이 맞힌 샘플)가 pipeline별로 다른 점이 표에 반영됐는지.
4. 범위·한계: ε=0 대조, L∞ 범위, 781장 순서·커버리지, 알려진 MobileNet FGSM 16셀·14장 불일치와 oneDNN on/off 차이가 보존됐는지. 허용오차를 넓혀서 통과시키지 않았는지.
5. 복구 절차: 13조건 PGD 부모만 상속하고(11조건 부모 미사용), 입력 SHA가 부모 `source_commit`과 같을 때만 진행하며, 환경 불일치 시 중단하는지.
6. 표현: 부분 결과를 완료로, 저장 증거 일관성 감사를 모델 재추론으로, 기계 CI 통과를 독립 승인으로 표기하지 않았는지.
7. 논문 제출본 결과를 확장 실험 결과로 교체하지 않았는지.

## 4. 실행 가능한 CPU 검사 명령

```bash
python -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements-ci.txt
python -m pip check
PYTHONPATH=src:. CUDA_VISIBLE_DEVICES=-1 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1 python verification/ci_cpu.py
# 부분 체크포인트 재감사 (예)
PYTHONPATH=src:. python verification/iterative_result_audit.py results/extensions/checkpoints/20261002-evening/bim
```

`ci_cpu.py`는 CPU에서 저장 증거의 내부 일관성과 회귀 테스트를 확인한다. 공식 모델 781장 재추론이나 GPU 실험 완료를 뜻하지 않는다.
CPU CI 통과 수는 실행 환경에 따라 달라질 수 있으므로, 실제 수치와 Python 버전을 함께 기록한다.

## 5. 기록 양식

자료 수령 시 [재현 자료 안내](REPRODUCTION_MATERIALS_GUIDE.md)에 따라 원시 바이트와 텍스트 사본을 구분한다.
각 항목을 다음 넷으로 구분해 적는다.

- 직접 확인: 파일·줄 번호와 읽은 내용
- 직접 실행: 명령, exit code, 결과(passed/skipped/failed)
- 전달 보고: 보고자, 대상 SHA, 보고서 위치와 보고된 결과(직접 실행으로 표기하지 않음)
- 미검증: 못 읽었거나 못 돌린 것과 이유

결함은 심각도, 파일·줄, 최소 재현, 기대/실제, 영향, 최소 수정으로 쓴다. 결함이 없으면 억지로 만들지 않는다.
