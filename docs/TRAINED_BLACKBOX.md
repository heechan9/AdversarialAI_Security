# 학습 전후 CNN 블랙박스 평가 프로토콜

기존 PGD7 적대적 학습의 best epoch=3 모델을 재학습·재선택 없이 평가한다. checkpoint는 `results/extensions/cnn_adversarial_20261002/training.json`의 SHA-256과 일치해야 한다. 비공개 모델과 원본 이미지는 Git에 넣지 않는다.

## 사전 고정 조건

- 고정 테스트 781장, 원본 CNN과 기존 적대적 학습 CNN.
- Square: ε=.03, p_init=.05, batch=20, 정상 조회를 포함한 200회(seed 2026), 1,000회(seed 2026/2027/2028). 두 모델 각각 새 공격을 생성한다. CPU intra-op 2/inter-op 1, oneDNN off.
- Square의 면적 변화 스케줄은 전체 예산에 따라 달라지므로 1,000회 실험은 200회 실행을 이어 돌린 것이 아니다. seed별 결과와 각 이미지에서 3개 seed 중 하나라도 성공하면 성공으로 보는 union을 함께 보존한다. union은 한 번의 1,000회 공격이 아니다.
- SurFree: 전체 781장, 각 모델 총 200회, seed=2026+manifest index, batch=1, CPU intra-op 1/inter-op 1, oneDNN off. L2 거리 최소화 공격이다. RMS=L2/√(128×128×3) .01/.03/.05 기준을 사전 고정한다. Square의 Linf ε와 같은 제약이 아니다.
- 정상 이미지를 틀리면 공격을 하지 않고 질의 1회로 기록한다. ASR은 각 모델의 정상 정답 집합 기준이며, Square는 공통 정상 정답 집합 비교도 제공한다.
- 테스트 결과로 모델이나 설정을 선택하지 않는다. 세 seed를 모두 보고한다.

## SurFree 공식 구현 연결

논문: Maho, Furon, Le Merrer, *SurFree: A Fast Surrogate-Free Black-Box Attack*, CVPR 2021, https://arxiv.org/abs/2011.12807.

공식 소스: https://github.com/t-maho/SurFree, commit `c9920f2c289a4ad3c2d8d203006bb5964bf71816`. 원본은 GPL-2.0-or-later 고지를 포함한다. 프로젝트에 원본 파일을 복사하지 않고 별도 checkout을 로드한다. adapter는 실제 사용되는 4개 파일 SHA-256을 확인한다. 현재 원본 코드는 PyTorch로 동작하며 README의 오래된 Foolbox 설명과 차이가 있어, 실제 커밋의 API를 기준으로 연결했다.

외부 oracle은 TF 모델에서 **top-1 클래스만** 받아 one-hot으로 전달한다. 확률·logit·gradient는 공격에 전달하지 않는다. 초기 정상 조회, .5 Gaussian noise 초기화, 중복 조회, 원본의 placeholder 조회까지 실제 호출을 모두 세며 예산 도달 시 다음 호출 전에 중단한다. 원본의 자체 질의 카운터만으로 완료 여부를 판단하지 않는다.

초기화는 최대 min(200,예산−1)회다. 실패하면 `initialization_failed`로 기록하고 원본 입력을 유지한다. 이는 견고성 인증이 아니다. 원본이 반환한 미조회 후보를 그대로 쓰지 않고 oracle이 실제로 오분류를 확인한 후보 중 가장 작은 L2 후보를 보존한다. 원본 출력 candidate, 원본의 누락된 초기화 집계와 차이가 있으므로 공식 논문 실험의 비트 단위 재현이라고 주장하지 않는다. geometry/search 코드는 변경하지 않는다.

공식 예제의 DCT full/constant/frequency [0,.5], BS γ=.01/max iterations=10, rho=.98, theta_max=30, n_ortho=10, T=1, alpha line search on, distance line search/interpolation/quantization off를 사용한다. 최대 steps는 query budget과 같고 마지막 binary search도 외부 예산에 포함된다. float32, [0,1] 입력이다. 실제 실행 전 toy oracle과 10장×50회 실제 CNN smoke 실행을 통과했다.

## 실행

기존 requirements 설치 후 PyTorch CPU를 추가한다. 모델 파일은 `models/cnn_adversarial.keras`, 원본은 `models/cnn_baseline.h5`, 데이터는 `data/test`에 준비한다.

```bash
python -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
git clone https://github.com/t-maho/SurFree.git /tmp/surfree-reference
git -C /tmp/surfree-reference checkout c9920f2c289a4ad3c2d8d203006bb5964bf71816

TF_ENABLE_ONEDNN_OPTS=0 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1 \
PYTHONPATH=src python -m adversarial_ai.evaluation.square_evaluation \
  --run-id trained_q1000_new --per-class 0 --epsilons 0 .03 \
  --max-queries 1000 --seed 2026 --batch-size 20 \
  --trained-model models/cnn_adversarial.keras
# 원본 모델은 --trained-model을 생략한다. seed 2027/2028도 각각 새 run-id로 실행한다.

TF_ENABLE_ONEDNN_OPTS=0 TF_NUM_INTRAOP_THREADS=1 TF_NUM_INTEROP_THREADS=1 \
PYTHONPATH=src python -m adversarial_ai.evaluation.surfree_evaluation \
  --upstream /tmp/surfree-reference --model-role trained \
  --max-queries 200 --seed 2026 --run-id trained_surfree_new
# 원본 모델은 --model-role original.

python verification/square_saved_audit.py
python verification/surfree_saved_audit.py
python verification/blackbox_series_summary.py
```

실제 실행 결과는 `results/extensions/blackbox`의 요약과 각 Square/SurFree run 폴더에 보존한다. 저장 결과 감사와 독립 모델 재실행은 구분한다. 원본 CNN의 과거 데이터 중복 노출 문제, near-duplicate 미검사, 실제 해상 운항 안전성은 이번 평가로 해결되지 않는다.

실행 초반의 로컬 커밋과 GitHub 커넥터 게시 커밋은 메타데이터만 다르다. `results/extensions/blackbox/source_mapping_20261003.json`에 동일 Git tree를 확인한 매핑을 보존했다. 실행 원본 run.json의 source_commit은 수정하지 않았다.
