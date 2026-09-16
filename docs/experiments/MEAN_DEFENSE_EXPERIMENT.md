# 고정 평균 필터 방어 비교 실험 (실행 준비, experimental)

## 목적과 사전 고정 조건

가우시안 방어보다 낫다고 가정하지 않는다. 같은 3×3 이웃에서 중심 가중치를
주는 binomial Gaussian(/16)과 동일 가중치 mean(/9)를 비교한다.
테스트셋 결과를 보고 필터 크기·가중치를 고르지 않는다. 추가 학습이나 모델 변경은 없다.
TensorFlow 연산은 https://www.tensorflow.org/api_docs/python/tf/nn/depthwise_conv2d 를 참고한다.

- 입력: 기존 manifest, CNN 128×128 / MobileNetV2 224×224, rescale 1/255.
- 방어: 고정 3×3 arithmetic mean, reflect padding, stride 1, 채널별 독립 처리.
- 공격: 기존 true-label untargeted 1-step FGSM, ε=0/0.01/0.03/0.05.
- 정상, 방어 정상, 기존 공격, 기존 공격+방어, 방어 인지 공격+방어를 모두 기록.
- 방어 인지 공격은 실제 필터 연산을 통과하는 gradient 사용. 교란은 필터 이전
  x_adv-x에서 측정하며 clipping과 L∞≤ε+1e-6을 검사한다.
- ASR 분모는 평가하는 pipeline의 clean-correct. 공통 clean-correct 부분집합도 별도 기록.
- 정상 손실/회복, 클래스별 수치, 모델 가중치·입력 해시 불변 검사는 기존 runner 재사용.
- 결과는 별도 새 디렉터리에만 기록. 기존 출력이 있으면 실패하고 덮어쓰지 않는다.

## 실행 (Windows Anaconda Prompt)

GitHub 저장소 루트에서 아래 명령을 한 줄씩 실행한다. 기존 작업 브랜치는 바꾸지 않는다.
기존 모델과 data/test는 원래 저장소에서 읽고, 코드는 별도 worktree에서 읽는다.

```bat
conda activate adversarial_ai
cd /d "%USERPROFILE%\AdversarialAI_Security"
git fetch origin codex/mean-defense-experiment
git worktree add --detach "%USERPROFILE%\adversarial-mean-defense-code-01" origin/codex/mean-defense-experiment
set "PYTHONPATH=%USERPROFILE%\adversarial-mean-defense-code-01\src"
python -m pytest "%USERPROFILE%\adversarial-mean-defense-code-01\tests\test_mean_defense.py" "%USERPROFILE%\adversarial-mean-defense-code-01\tests\test_mean_defense_evaluation.py" -q -rs
```

테스트 실패 시 실험 실행을 중단하고 로그를 검토한다. 통과 후:

```bat
python -m adversarial_ai.evaluation.mean_defense_evaluation --defense mean --output "%USERPROFILE%\adversarial-mean-defense-run-01"
```

완료 문구와 COMPLETE.json을 확인한 후 ZIP으로 묶어 검토한다. FAILED.json 또는
부분 CSV만으로 완료를 주장하지 않는다. 실행 중 절전하면 계산도 중단될 수 있다.

## 채택 기준과 한계

실행 후 전체 표본/조건의 CSV를 재계산하고 canonical clean 및 기존 가우시안
결과와 비교한다. 깨끗한 이미지 손실을 포함하고 불리한 클래스·강도도 보고한다.
특정 ε에서의 개선만으로 새로운 방어가 우수하다고 선택하거나 논문 결론을 바꾸지 않는다.
한 단계 adaptive FGSM도 최악의 공격을 보장하지 않는다. PGD 등 반복 공격과
독립 검증 전에는 일반적 강건성 또는 gradient masking 부재를 주장하지 않는다.
현재 원본 이미지와 H5가 없는 환경의 합성 테스트는 실제 선박 성능 실험을 대신하지 않는다.
기존 Gaussian archive 감사 스크립트를 새 mean 출력에 그대로 적용해 통과했다고
주장하지 않는다. 새 결과의 독립 감사·팀 검토·채택은 후속 단계이며 자동 승격/병합하지 않는다.
