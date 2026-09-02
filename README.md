# 자율운항선박 VLM·LLM 기반 AI 보안 프레임워크 구현

![적대적 AI 프로젝트 비전 이미지](docs/assets/adversarial-ai-project-vision.png)

> **Concept / Target Vision:** 자율운항선박 AI 보안의 목표 운영상을 표현한 비전 이미지입니다. 현재 저장소는 선박 이미지 분류 모델의 Clean Baseline 재현과 FGSM 기반 연구용 검증을 중심으로 하며, 이미지에 표현된 실시간 위협탐지·공격방어·모니터링은 구현 또는 실증 완료 기능이 아닙니다.

2026 스마트해운물류 × ICT 멘토링

## 프로젝트 소개
CNN·MobileNet 기반 선박 10클래스 인식 모델에 적대적 공격(FGSM·BIM·PGD·JSMA)을 적용해 취약성을 분석하고, 인식 오류가 항로판단에 미치는 영향을 **연구용 안전영향 시뮬레이터**로 검증하는 프로젝트입니다. (※ 실제 자율운항 제어시스템이 아닙니다.)

## 연구질문
> 선박 유형 분류 모델에서 공격 방법과 모델 구조에 따라 적대적 공격 취약성과 전이성이 어떻게 달라지는가?

## 3단계 연구 구조
1. **Clean Baseline** — CNN·MobileNet 인식 모델의 공격 없는 기준 성능
2. **Adversarial Attack** — FGSM·BIM·PGD·JSMA를 CNN/MobileNet에 White-box로 적용
3. **Safety Simulation** — 인식 오류 → 항로판단 영향을 보는 연구용 안전영향 시뮬레이터

자세한 범위·Decision Gate는 [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md), 공격·평가 정의는 [`docs/EXPERIMENT_CONTRACT.md`](docs/EXPERIMENT_CONTRACT.md) 참조.

## 확보된 기술자산 (사실)
| 자산 | 내용 |
|---|---|
| `cnn_baseline.h5` | CNN, 입력 128×128×3 |
| `mobilenet_stage1.h5` | MobileNetV2, backbone 대부분 동결 |
| `mobilenet_finetuned.h5` | MobileNetV2, 일부 unfreeze |
| 정규화(명세상) | 0~1 (`rescale=1./255`) |
| 클래스 | 10개 ([`configs/classes.json`](configs/classes.json)) |
| 테스트 표본 | 781장 |

## 현재 확인된 결과 (사실 — 이것만 기록)
- CNN Baseline Test Accuracy: **0.6453264951705933** (2026-08-05 재현)
- MobileNetV2 Finetuned Test Accuracy: **0.7848911881446838** (2026-08-05 최초 clean 평가)
- 상세 결과와 증거 수준: [`docs/CLEAN_BASELINE_RESULTS.md`](docs/CLEAN_BASELINE_RESULTS.md)

## 아직 확인되지 않은 사항 (계획/미확인 — 수치를 만들지 않음)
- 멘토 승인 후 확정할 공식 FGSM ASR·Robust Accuracy (현재 값은 provisional)
- 방어기법 효과
- 시뮬레이션 충돌률
- Train/Val 정확한 분할 비율, random seed
- MobileNet 학습 당시 실제 전처리(평가와 handoff 명세는 `rescale=1./255`, 학습 코드 미확보)

## 로컬 설치 예정 방법
```bash
git clone <this-repo>
cd AdversarialAI_Security
python -m venv venv && source venv/bin/activate   # 또는 Anaconda 가상환경
pip install -r requirements.txt
```
모델·데이터 배치 방법은 [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) 참조.

## 저장소 구조
```
configs/     실험·API PoC 설정 (YAML/JSON)
docs/        프로젝트 범위·실험계약·API 선정·재현성 문서
src/adversarial_ai/   data/models/attacks/evaluation 패키지
scripts/     실행 스크립트 (추후 추가)
tests/       스키마 검증 등 테스트
results/     clean/attacks/multimodal/simulation 결과 (실제 수치는 실험 후 채움)
notebooks/   탐색용 노트북 (추후 추가)
```

## 재현성 원칙
- `.h5` 모델과 데이터셋은 Git에 커밋하지 않는다 (`docs/REPRODUCIBILITY.md`)
- 모든 실험은 동일 테스트셋·클래스 순서·seed를 사용한다 (`docs/EXPERIMENT_CONTRACT.md`)
- 확정 전 파라미터는 "proposed"로 표시하고, 확정되면 문서와 config를 함께 갱신한다

## 현재 진행 상태
- ✅ CNN Baseline clean 평가 재현 완료
- ✅ MobileNetV2 Finetuned clean 평가 완료
- ✅ Versioned outputs — test manifest, 표본별 CSV, report, metadata, Confusion Matrix 생성·검증 완료
- ✅ FGSM — 구현·테스트 완료, CNN·MobileNet 781장 provisional ε 스윕 완료 ([예비 결과](docs/FGSM_PROVISIONAL_RESULTS.md))
- ◐ FGSM 공식 결과 — 멘토 ε 범위 승인 후 별도 경로에 재실행 예정
- ○ BIM/PGD/JSMA — 계획 단계
- ○ 멀티모달 API PoC — 이 PR 범위 밖이며 별도 브랜치에서 검토 예정
- ○ Safety Simulation — 계획 단계

## 직무 연계·인터뷰 가이드

프로젝트의 구현 증거, 직무 연결, 자소서 구성과 주장 한계는 [`docs/ROLE_ALIGNMENT.md`](docs/ROLE_ALIGNMENT.md)에서 확인할 수 있습니다.
