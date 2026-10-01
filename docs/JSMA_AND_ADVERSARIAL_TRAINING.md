# 후속 연구: JSMA와 적대적 학습

2026-10-01 확장 요청에 따라 코드를 추가했다. 제출본·기존 FGSM 수치와 별도이며 실제 실험 완료 여부는 실행 기록으로 구분한다.

## JSMA

표적 클래스 확률의 입력 미분과 나머지 클래스 미분으로 feature pair의 saliency를 구한다. 전체 가능한 pair를 블록 단위로 탐색하며 후보 top-k 근사를 쓰지 않는다. theta의 부호에 맞춰 확률 변화 방향을 검사하고, 원본 대비 **서로 다른 채널 원소 수(L0)**를 gamma 이하로 유지한다. RGB 픽셀 수와 다르다. 같은 feature를 재선택할 수 있으며 [0,1] 범위를 유지한다. 목표 도달·budget·saliency 부재·반복 상한을 구분한다.

정확한 pair 탐색은 O(d²)이므로 128×128×3 및 224×224×3에서는 비용이 크다. `--max-steps`로 끝난 사례는 공격 실패나 강건성 입증으로 단정하지 않는다. `--limit` 사용 시 부분 평가임을 명시한다. target은 `(true_index+1)%10`으로 고정한다. Gaussian/Mean은 필터를 포함해 미분하는 방어 인지 경로다. JSMA의 표적 ASR과 FGSM/PGD untargeted ASR을 같은 값처럼 비교하지 않는다.

```bash
# Windows: set PYTHONPATH=src / Linux: export PYTHONPATH=src
python -m adversarial_ai.evaluation.jsma_evaluation --model cnn --defense none --theta 1 --gamma 0.01 --max-steps 1 --limit 1 --run-id jsma-smoke-01
```

위 명령은 기능 확인용 1장·1회 예시이고 전체 성능 평가가 아니다. 전체 평가에는 `--limit 781`과 사전에 정한 반복 한도를 사용한다. `results/extensions/jsma/<run-id>`의 신규 폴더만 사용한다.

## PGD 적대적 학습

원본 모델을 복제해 clean/PGD loss를 0.5/0.5로 혼합하여 fine-tuning한다. 원본 파일을 덮어쓰지 않는다. 공격 생성은 inference mode, 학습은 training mode이며 PGD 입력에 stop-gradient를 적용한다. 학습률·epoch·epsilon·step-size·steps·seed는 기록한다. 검증 세트 PGD 정확도로 best.keras를 선택하며 테스트 781장은 선택에 쓰지 않는다.

학습 전 train/validation/test의 raw SHA-256 및 디코딩한 RGB hash 중복을 차단한다. 다른 이름/무손실 포맷의 동일 영상도 검출한다. 유사 이미지·동일 선박의 다른 프레임까지 판별하는 검사는 아니므로 데이터 출처와 분할 검토가 별도로 필요하다. 모든 클래스가 train/validation에 있어야 한다. 테스트 이미지는 누출 검사에만 읽는다.

```bash
python -m adversarial_ai.training.adversarial_training --model cnn --train-dir data/train --validation-dir data/validation --test-dir data/test --epochs 5 --epsilon 0.03 --step-size 0.005 --steps 10 --run-id cnn-advtrain-explore-01
```

이는 탐색 예시이고 최적 조건이나 방어 성능을 보장하지 않는다. 새 학습 모델은 `results/extensions/adversarial_training/<run-id>/best.keras`에 저장한다. 완료 상태 `TRAINED_NOT_TEST_EVALUATED`는 테스트 평가 완료가 아니다. 학습 후 별도 고정 공격 설정으로 평가해야 한다. 새 모델 평가는 iterative 실행기의 `--trained-model <best.keras> --trained-model-sha256 <기록된 해시> --trained-model-kind cnn`을 함께 지정한다. 해당 모델의 8조건만 별도 평가하며 원본 모델 경로를 덮어쓰지 않는다. 원본 모델과 manifest 입력 검사도 유지한다.

현재 보관된 원본 전달 ZIP에서 모델 2개·test 781장을 확인했다. 별도 선박 train/validation 자료는 확보하지 못했으므로 **실제 선박 적대적 학습은 데이터 대기**다. 합성 모델 학습 테스트는 실제 선박 방어 결과가 아니다.

## 근거

- Papernot et al., The Limitations of Deep Learning in Adversarial Settings: https://arxiv.org/abs/1511.07528
- Madry et al., Towards Deep Learning Models Resistant to Adversarial Attacks: https://arxiv.org/abs/1706.06083

선행 방식에 맞춘 TensorFlow 구현이며 기존 외부 독립 검증 FAIL·원인 미확정 상태를 바꾸지 않는다.
