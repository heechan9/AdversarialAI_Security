# Reproducibility

## English reproduction navigation

Choose a level before running anything. The older setup notes below are historical guidance, not permission to regenerate canonical manifests or overwrite reference results. Work from an isolated checkout of a recorded full SHA; record the environment and command exit codes. See [the preserved snapshot](PAPER_RELEASE_STATUS.md#preserved-source-and-submission-boundary--2026-10-30).

| Level | Start here | What completion means |
|---|---|---|
| Public saved evidence, no private assets | [Evidence audit](RESEARCH_EVIDENCE_AUDIT.md), [historical claim audit](PAPER_CLAIM_AUDIT.md), [CPU gate](CPU_CI_REVIEW.md) | Record/contract consistency and synthetic software regression, not model reproduction |
| Separate saved matched-CNN extension | [Result package and pinned evaluator](../results/extensions/matched_cnn_20261024/README.md) | Recalculation of a one-seed follow-up; not general robustness or independent approval |
| Original-model rerun | [Independent verification](INDEPENDENT_VERIFICATION.md), [Stage B contract](STAGE_B_EXECUTION_CONTRACT.md) | Requires separately authorized models/images and agreed comparison criteria; retain failures |
| Existing mismatch diagnosis | [External FAIL](STAGE_B_HYEONSU_01_REVIEW.md), [research-PC LOCAL_PASS](STAGE_B_PC_FULL_20260928.md), [selected cross-only handoff](HYUNSU_CROSS_ONLY_HANDOFF_20261026.md) | A bounded diagnosis, not automatic resolution of the external FAIL |

Minimal public-only check of the **separate extension**, from repository root (Python standard library; no model loading/training/inference):

```bash
git rev-parse HEAD
python verification/matched_cnn_saved_audit.py
```

The full public CPU regression environment and command are maintained in [CPU_CI_REVIEW.md](CPU_CI_REVIEW.md) and [.github/workflows/iterative-attacks.yml](../.github/workflows/iterative-attacks.yml), rather than duplicated here. Follow their dependency setup; do not interpret CI success as private-model inference. The Stage B contract owns model execution commands, output isolation, approvals and comparison thresholds; do not relax them after observing a mismatch.

Return the full source SHA, environment, exact commands, stdout/stderr and exit codes, input/output hashes, comparison scope and discrepancies. Label **direct execution**, **reported evidence**, and **not checked** separately. Do not publish private assets, personal filesystem paths or access links. A 783-entry asset hash match with `model_inference_performed=false` must remain an asset check.

## 모델·데이터는 Git에 커밋하지 않는다
이유: 데이터 출처·라이선스 미확정 / Git 저장소 용량 증가 / 모델 정본 관리 문제.
`.gitignore`에서 `data/`, `datasets/`, `models/*.h5`, `models/*.keras`를 제외한다.

향후 Git LFS·GitHub Release·외부 저장소(Google Drive 등) 중 하나로 관리할지는
**팀이 결정한 뒤 이 문서에 반영**한다. 현재는 미확정 상태다.

## 로컬 배치 경로 (제안)

```
models/
  cnn_baseline.h5
  mobilenet_stage1.h5
  mobilenet_finetuned.h5
data/
  test/            # 781장 테스트셋
  train/           # 미확인 — 실제 분할 경로 확인 필요
  val/             # 미확인
```

## 필요한 파일명 (확인된 것만)
| 파일명 | 상태 |
|---|---|
| `cnn_baseline.h5` | 확인됨 — CNN, 입력 128×128×3 |
| `mobilenet_stage1.h5` | 확인됨 — backbone 대부분 동결 |
| `mobilenet_finetuned.h5` | 확인됨 — 일부 unfreeze |

## SHA-256 기록 방식 (제안)
모델·데이터 파일을 로컬에 배치한 뒤 아래 명령으로 해시를 기록하고, 그 출력을
`docs/CHECKSUMS.txt`(추후 생성)에 커밋한다. 이렇게 하면 실제 바이너리를
Git에 올리지 않고도 "이 실험이 어떤 파일 버전으로 수행됐는지"를 검증할 수 있다.

```bash
sha256sum models/*.h5 > docs/CHECKSUMS.txt
```

저장소의 manifest 생성기를 사용하면 테스트 이미지 781장과 평가 모델의 상대경로·SHA-256을 JSON으로 기록할 수 있다.

```bash
PYTHONPATH=src python -m adversarial_ai.data.manifest
```

이 명령은 `configs/test_manifest.json`을 만든다. 데이터와 모델 바이너리는 포함하지 않으며, 정확히 781장이 아니면 실패한다.

## Clean baseline 재현

확인된 실행환경은 Python 3.11.15, TensorFlow 2.21.0, Keras 3.15.1, Conda 환경 `adversarial_ai`이다.

```bash
PYTHONPATH=src python -m adversarial_ai.evaluation.evaluate_cnn_baseline
PYTHONPATH=src python -m adversarial_ai.evaluation.evaluate_mobilenet
```

각 실행은 `results/clean/`에 표본별 예측 CSV, classification report JSON·CSV, summary JSON, metadata JSON, confusion matrix CSV·PNG를 저장한다. 모델과 데이터가 없는 환경에서는 결과 파일을 생성하지 않는다.

## FGSM 실행(확정 ε 범위)

```bash
PYTHONPATH=src python -m adversarial_ai.evaluation.evaluate_fgsm_cnn
PYTHONPATH=src python -m adversarial_ai.evaluation.evaluate_fgsm_mobilenet
```

논문 평가의 확정 ε는 `0, 0.01, 0.03, 0.05`이다. `--epsilons` 옵션으로 다른 값을 실행하더라도 확정 논문 범위의 결과로 취급하지 않는다. 결과는 `results/attacks/`에 모델별 요약 CSV, ε별 표본 CSV·report JSON·confusion matrix CSV/PNG, 성공·실패 예시 이미지와 metadata JSON으로 저장한다.

## 아직 확인되지 않은 것 (재현성 관점)
- Train/Val/Test 정확한 분할 비율과 분할 코드
- Random seed 값
- MobileNet 학습 코드의 실제 입력 정규화 방식. 평가와 handoff 명세는 `rescale=1./255`로 일치하지만 학습 코드 직접 확인은 아직이다.
- Train/Val/Test 사이 중복 이미지 여부. 현재 로컬에는 test만 있어 split 간 해시 비교를 수행하지 못했다.
