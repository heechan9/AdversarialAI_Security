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

## 아직 확인되지 않은 것 (재현성 관점)
- Train/Val/Test 정확한 분할 비율과 분할 코드
- Random seed 값
- TensorFlow/Keras 정확한 버전 (프레임워크 종류는 확정: TensorFlow/Keras — 첫 멘토회의 녹취 및 `.h5` 포맷으로 교차 확인됨)
- MobileNet 입력 정규화 방식(rescale vs `preprocess_input`)
