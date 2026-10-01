# 제출 이후 후속 연구: BIM·PGD

2026-10-01 사용자 요청으로 확장을 시작했다. ACK2026 제출 원고와 FGSM 기준 결과는 보존한다. **BIM·PGD 구현 및 합성 모델 검증 단계**이며 원본 CNN·MobileNetV2 / 781장 결과는 아직 없다. 기존 외부 독립 검증 FAIL과 환경 차이 미해결 상태도 유지한다.

## 구현

- untargeted L∞ BIM: 정상 입력 시작, 반복 sign-gradient 상승 및 매 단계 예산/입력 범위 투영.
- untargeted L∞ PGD: seed를 지정한 무작위 시작과 복수 restart. 이미지 범위는 [0,1].
- 평가 목적의 best-so-far 선택: 정상 입력·초기점·모든 반복에서 표본별 오분류 성공을 먼저, 같은 성공 여부에서는 CE loss를 비교한다. 마지막 반복만 반환하는 구현과 구분한다. 전처리 전 입력에서 예산을 측정한다.
- 기존 미분 가능한 Gaussian/Mean에 대해 전달 공격과 방어 인지 공격을 별도로 생성한다. 각 ASR 분모는 해당 경로의 정상 정답 표본이다. 분모 0이면 null이다.
- 모델 2개 × 필터 2개 × epsilon 4개, 조건별 781행과 다섯 경로 예측을 기록한다. run.json에 설정·코드 커밋·모델/manifest/CSV 해시·실행 환경·완료/오류를 보존한다.
- 결과는 `results/extensions/iterative/<run-id>`에만 생성한다. 기존 run-id는 거부한다. 완료는 독립 검증 승인이나 방어 성공을 의미하지 않는다.

## 실행 예시

저장소 루트의 원본 models와 데이터가 필요하다. 기존 manifest의 해시·순서 검증을 통과해야 한다. 다음은 **탐색용 예시 설정**이며 최적 공격 강도가 입증된 값은 아니다. 공격 반복수·step-size·restart를 바꾼 수렴성 비교 후 후속 논문의 조건을 정한다.

```bash
# Windows Anaconda Prompt: set PYTHONPATH=src
# Linux/macOS: export PYTHONPATH=src
python -m adversarial_ai.evaluation.iterative_evaluation --attack bim --steps 10 --step-size 0.005 --run-id bim-explore-01 --data-dir data/test
python -m adversarial_ai.evaluation.iterative_evaluation --attack pgd --steps 20 --step-size 0.005 --restarts 5 --seed 2026 --run-id pgd-explore-01 --data-dir data/test
```

소스/config 수정은 커밋 후 실행한다. 동일 seed도 하드웨어 간 동일 결과를 보장하지 않으며 배치 크기·순서가 달라지면 random start도 달라질 수 있다. 현재 확률 벡터와 공격 텐서는 저장하지 않는다. 후속 평가 결과를 Stage B 기존 출력 형식으로 섞지 않는다. 비용은 FGSM보다 높으므로 먼저 단위 검사를 통과시키고 실행 예산을 확인한다.

```bash
PYTHONPATH=src python -m pytest tests/test_iterative.py -q
```

## 이후 단계

적대적 학습은 별도 train/validation 자료와 중복·누출 검사를 확보한 뒤 구현한다. 테스트 781장을 학습·하이퍼파라미터 선정에 사용하지 않는다. 새 방어 모델은 별도 이름·해시로 저장한다. JSMA는 희소 교란 및 target/success 기준을 별도 설계하는 다음 단계로 남긴다. 둘 다 현재 구현 완료로 표시하지 않는다.

## 방법 근거

- Kurakin et al., *Adversarial examples in the physical world*: https://arxiv.org/abs/1607.02533
- Madry et al., *Towards Deep Learning Models Resistant to Adversarial Attacks*: https://arxiv.org/abs/1706.06083
- ART 공식 evasion attack 문서의 BIM/PGD 정의: https://adversarial-robustness-toolbox.readthedocs.io/en/main/modules/attacks/evasion.html

본 코드는 기존 TensorFlow 모델 규약에 맞춰 작성했으며 외부 프로젝트 공격 코드를 복사하지 않았다.
