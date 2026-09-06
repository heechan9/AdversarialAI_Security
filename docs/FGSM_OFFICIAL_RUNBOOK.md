# FGSM 공식 실행 런북

상태: **계약 확정 / 실행 전**

이 문서는 공식 FGSM 후보를 재현하고 검토하기 위한 절차다. 계약 확정만으로 기존 예비 결과가 공식 결과가 되지는 않는다.

## 1. 고정 계약

- 모델: CNN, MobileNetV2
- 테스트셋: `configs/test_manifest.json`에 기록된 781장
- 공격: untargeted FGSM, true-label categorical cross-entropy, 정확히 1-step
- epsilon: `0`, `0.01`, `0.03`, `0.05`
- 입력 및 clipping 범위: `[0,1]`
- 표본별 제약: `L∞ <= epsilon + 1e-6`
- Robust Accuracy와 Macro F1 분모: 전체 781장
- ASR 분모: clean-correct 표본만 사용
- epsilon 0: Clean 예측·정확도, ASR 0, accuracy drop 0, L∞ 0 확인

모델, 가중치, 전처리, manifest, 클래스 순서 또는 epsilon을 실행 중 변경하면 같은 공식 실험으로 인정하지 않는다.

## 2. 실행 전 확인

Windows Anaconda Prompt에서 저장소와 환경을 확인한다.

```bat
conda activate adversarial_ai
cd C:\Users\hc247\AdversarialAI_Security
set PYTHONPATH=src
git status --short
git rev-parse HEAD
python --version
python -c "import tensorflow as tf; print(tf.__version__)"
python scripts\audit_research_evidence.py
python scripts\audit_paper_claims.py
python scripts\capture_official_fgsm_context.py
```

`git status --short`에서 사용자의 기존 untracked 파일은 삭제하거나 추가하지 않는다. 데이터 781장과 로컬 `.h5` 모델의 SHA-256 검증이 통과하지 않으면 실행을 중단한다. 환경 기록기는 보호된 연구 입력에 tracked 변경이 있거나 `official_candidate`가 비어 있지 않으면 fail-closed로 중단하며, 실행 commit·Python·TensorFlow·Keras·플랫폼을 후보 디렉터리에 고정한다.

## 3. 격리된 후보 실행

기존 `results\attacks\provisional\`을 출력 대상으로 사용하지 않는다.

```bat
python -m adversarial_ai.evaluation.evaluate_fgsm_cnn --output results\attacks\official_candidate --epsilons 0 0.01 0.03 0.05
python -m adversarial_ai.evaluation.evaluate_fgsm_mobilenet --output results\attacks\official_candidate --epsilons 0 0.01 0.03 0.05
python scripts\audit_official_fgsm_candidate.py
```

두 모델 실행 또는 후보 감사 중 하나라도 실패하면 부분 산출물을 공식 결과로 사용하지 않는다. 실패 원인과 실행 로그를 보존한 뒤 빈 후보 디렉터리에서 환경 기록부터 전체 sweep을 다시 실행한다.

## 4. 공식 승격 전 검증

다음을 모두 만족해야 한다.

1. 두 모델 모두 781장과 네 epsilon을 완주한다.
2. epsilon 0 불변조건과 모든 표본의 L∞ 상한이 통과한다.
3. Clean 정답 수를 canonical Clean CSV에서 동적으로 다시 계산하고 실행 결과와 일치시킨다.
4. 표본 CSV에서 Robust Accuracy, Macro F1, ASR, 성공 수 및 confusion matrix를 다시 계산해 요약 파일과 대조한다.
5. 모델과 데이터 SHA-256, Python·TensorFlow·Keras 버전, 실행 commit SHA를 기록한다.
6. provisional 결과와 차이가 있으면 수치를 숨기거나 선택하지 않고 전체 차이를 기록한다.
7. 전체 pytest, Research Evidence Audit, Paper Claim Audit이 통과한다.
8. 변경 diff에 모델·가중치·전처리·manifest·기존 provisional 결과가 포함되지 않는다.

공식 후보 감사기는 파일 인벤토리, 실행 commit·환경, manifest·모델 해시, canonical Clean 행 결합, 네 epsilon, 표본별 공격 성공·L∞, 요약·classification report·confusion matrix를 동적으로 재계산한다. 감사 통과는 후보의 내부 일관성을 의미하며 자동 승격이나 논문 수치 교체를 의미하지 않는다.

## 5. 병합 경계

- 실행 준비 문서와 계약 변경은 Draft PR에서 검토한다.
- 공식 후보 산출물은 별도 결과 PR로 제출한다.
- 결과 PR에는 전체 변경 파일, 산출물 SHA-256, 실행 환경, 테스트 및 두 감사 결과를 기록한다.
- 리뷰 완료 전에는 `official_candidate`를 `official`로 이름 변경하거나 README·논문 수치를 교체하지 않는다.
- 최종 병합은 프로젝트 책임자의 명시적 확인 후 수행한다.
