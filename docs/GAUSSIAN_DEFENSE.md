# 작은 전처리 방어: experimental v1.0

상태: 사용자 Windows PC에서 첫 781장 실험 완료, 업로드 기록 독립 재계산 일치. 공식 채택 아님.
결과와 한계: [실험 기록](../results/defenses/experimental/gaussian_run_01/README.md).

## 고정 계약

- 모델 입력 직전의 [0,1] NHWC float32 이미지에만 적용한다.
- 고정 3×3 커널 `[[1,2,1],[2,4,2],[1,2,1]]/16`, 가장자리는 reflect.
- 색 채널별 독립 처리, 크기 보존. 학습·파라미터 탐색 없음.
- 모델 로딩/기존 리사이즈/정규화/모델 내부 전처리는 변경하지 않는다.
- NumPy 함수는 비교용 참조 구현이다. 공격 계산에는 TensorFlow 구현만 사용한다.
- PNG 비교 패널을 원본 공격 배열로 취급하지 않는다.

## 사용

```python
from adversarial_ai.defenses.gaussian import GaussianDefendedModel, generate_adaptive_fgsm
# model: 기존 로더로 읽은 모델. x: 기존 경로로 준비한 [0,1] 배치.
# y: 실제 정답 one-hot. epsilon: 기존 계약에 기록된 실험 강도.
defended = GaussianDefendedModel(model)
clean_defended_scores = defended(x)
x_adv = generate_adaptive_fgsm(model, x, y, epsilon)
attacked_defended_scores = defended(x_adv)
```

기존 FGSM 생성기를 재사용하여 `f(D(x))` 전체를 미분한다. 공격 예산은
방어 전 입력 `x_adv - x`에 적용한다. ε=0에서는 입력이 동일하지만
`f(D(x))`는 원래 `f(x)`와 다를 수 있다. 이를 방어의 정상 성능 손실로 기록한다.

## 다음 실제 평가 계약

같은 manifest 순서/모델 hash를 확인하고 다음 네 조건을 모두 저장한다:
1. 원래 모델 정상 입력 `f(x)`
2. 방어 모델 정상 입력 `f(D(x))`
3. 원래 모델 대상으로 생성한 FGSM을 방어에 전달 `f(D(A_f(x)))`
4. 방어를 알고 생성한 FGSM `f(D(A_(f∘D)(x)))`

정확도 분모는 모든 평가 표본이다. 방어 ASR은 **방어 적용 정상 입력에서
맞힌 표본**을 분모로 따로 계산한다. 원래 모델 ASR 분모와 혼용하지 않는다.
모델 간 직접 비교에는 양쪽 정상 정답 교집합도 별도로 보고한다.
분모 0은 0%가 아닌 null로 표시한다. 원래 정상 오답의 회복/정상 정답의
방어 후 손실도 따로 집계한다. 클래스별 표본 수와 분모를 함께 제공한다.

두 모델, 기존 기록된 ε=0/0.01/0.03/0.05만 후속 평가한다. 테스트셋으로
커널을 고르거나 튜닝하지 않는다. 새 결과는 별도 experimental 위치에만
저장하고 원본·가중치 전후 hash 및 전체 테스트/두 감사를 확인한다.
전체 데이터 실행기는 `adversarial_ai.evaluation.defense_evaluation`이다. 첫 실제 연구 결과는 별도 experimental 경로에 보존했다. 아래 CLI로 기존 모델/이미지가 있는 PC에서 실행한다.

FGSM 한 단계만 통과해도 일반적 방어 성공을 주장할 수 없다. 반복 공격 등
더 강한 방어 인지 공격 평가가 필요하며 선박 운항/충돌 방지를 검증하지 않는다.

## 근거

- TensorFlow depthwise convolution: https://www.tensorflow.org/api_docs/python/tf/nn/depthwise_conv2d
- TensorFlow reflect padding: https://www.tensorflow.org/api_docs/python/tf/pad
- Athalye et al., gradient masking 경고: https://arxiv.org/abs/1802.00420

## 전체 데이터 실행 (Windows Anaconda Prompt)

별도 소스 worktree를 사용해 기존 작업 브랜치를 바꾸지 않는다. 다음 경로가 이미
존재하면 덮어쓰지 말고 상태를 확인한다. 모듈은 현재 작업 디렉터리에서
`models/`, `data/test/`, `configs/`, `results/clean/`을 읽는다.

```bat
conda activate adversarial_ai
cd /d "%USERPROFILE%\AdversarialAI_Security"
git fetch origin codex/gaussian-defense
git worktree add --detach "%USERPROFILE%\adversarial-defense-code-01" origin/codex/gaussian-defense
set "PYTHONPATH=%USERPROFILE%\adversarial-defense-code-01\src"
python -m pytest "%USERPROFILE%\adversarial-defense-code-01\tests\test_gaussian_defense.py" "%USERPROFILE%\adversarial-defense-code-01\tests\test_defense_evaluation.py" -q -rs
python -m adversarial_ai.evaluation.defense_evaluation --output "%USERPROFILE%\adversarial-defense-run-01"
```

테스트가 실패하면 실험 명령을 실행하지 않는다. CNN 128×128 / MobileNetV2
224×224, 기존 rescale/리사이즈/배치32/shuffle=False를 재사용한다. 두 모델 및
모든 이미지 SHA-256을 실행 전후 확인하고 canonical clean 예측과 다르면 중단한다.
전체 실험은 CPU에서 시간이 걸리며 배치마다 진행 상황을 출력한다.

산출물은 8개 sample CSV, 클래스별/전체 `summary.json`, `contract.json`,
`SHA256.json`, 성공 시에만 `COMPLETE.json`이다. 실패 시 `FAILED.json`이 남고
완료로 취급하지 않는다. 기존 출력 디렉터리를 덮어쓰지 않는다. 원본 공격 배열은
저장하지 않으므로 clipping/L∞는 실행 중 검사 기록이며 사후 독립 픽셀 검증은 아니다.
방어 유무의 모델 간 비교는 각 조건/모델의 분모를 함께 확인한다. 이 실행기의
공통 정답 집합은 한 모델 안에서 방어 전후 교집합이며 CNN/MobileNetV2 사이의
교집합 분석은 별도 후처리다.

이 실행기는 기존 Research/Paper 감사를 자동 실행하거나 논문 수치를 갱신하지
않는다. 새 방어 산출물은 별도 검토하고 두 기존 감사도 후속 통합 전에 실행한다.
테스트 종료 후 만들어진 실험 폴더를 공유하면 수치를 독립 재계산할 수 있다.

## 독립 결과 재검증

`python scripts/audit_gaussian_defense.py`는 TensorFlow/평가기 코드를 실행하지 않고
원본 ZIP과 보존 파일, 해시, canonical 예측, 전체/클래스별 요약을 독립 재계산한다.
변조 테스트는 해시를 재작성한 경우의 잘못된 분모/클래스 집계/ε=0도 포함한다.

논문 문안: [v2.5 반영용 보충안](PAPER_DEFENSE_SUPPLEMENT_v2_5.md).
