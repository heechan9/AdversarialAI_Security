# Reproducibility

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

## 아직 확인되지 않은 것 (재현성 관점)
- Train/Val/Test 정확한 분할 비율과 분할 코드
- Random seed 값
- MobileNet 학습 코드의 실제 입력 정규화 방식. 평가와 handoff 명세는 `rescale=1./255`로 일치하지만 학습 코드 직접 확인은 아직이다.
- Train/Val/Test 사이 중복 이미지 여부. 현재 로컬에는 test만 있어 split 간 해시 비교를 수행하지 못했다.
