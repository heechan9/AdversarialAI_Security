# 자율운항선박 VLM·LLM 기반 AI 보안 프레임워크 구현

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
- 어떤 공격에 대한 ASR·Robust Accuracy
- 방어기법 효과
- 시뮬레이션 충돌률
- Train/Val 정확한 분할 비율, random seed
- MobileNet 학습 당시 실제 전처리(평가와 handoff 명세는 `rescale=1./255`, 학습 코드 미확보)
- 멀티모달 API 실제 호출 결과 (아직 유료 호출 자체를 하지 않음)

## 로컬 설치 예정 방법
```bash
git clone <this-repo>
cd AdversarialAI_Security
python -m venv venv && source venv/bin/activate   # 또는 Anaconda 가상환경
pip install -r requirements.txt
cp .env.example .env   # 실제 키는 로컬에만 채우고 절대 커밋하지 않음
```
모델·데이터 배치 방법은 [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) 참조.

## 저장소 구조
```
configs/     실험·API PoC 설정 (YAML/JSON)
docs/        프로젝트 범위·실험계약·API 선정·재현성 문서
src/adversarial_ai/   data/models/attacks/evaluation/multimodal/simulation 패키지 골격
scripts/     실행 스크립트 (추후 추가)
tests/       스키마 검증 등 테스트
results/     clean/attacks/multimodal/simulation 결과 (실제 수치는 실험 후 채움)
notebooks/   탐색용 노트북 (추후 추가)
```

## 재현성 원칙
- `.h5` 모델과 데이터셋은 Git에 커밋하지 않는다 (`docs/REPRODUCIBILITY.md`)
- 모든 실험은 동일 테스트셋·클래스 순서·seed를 사용한다 (`docs/EXPERIMENT_CONTRACT.md`)
- 확정 전 파라미터는 "proposed"로 표시하고, 확정되면 문서와 config를 함께 갱신한다

## API Key 보안 원칙
- API Key는 코드·노트북·문서·GitHub에 절대 커밋하지 않는다
- `.env`에만 보관하고 `.env`는 `.gitignore`로 제외된다 (`.env.example`만 커밋)
- 아직 어떤 provider도 실제로 선택되지 않았으며, 유료 API 호출도 하지 않은 상태다

## 현재 진행 상태
- ✅ CNN Baseline clean 평가 재현 완료
- ✅ MobileNetV2 Finetuned clean 평가 완료
- ✅ Versioned outputs — test manifest, 표본별 CSV, report, metadata, Confusion Matrix 생성·검증 완료
- ○ 공격 구현(FGSM/BIM/PGD/JSMA) — 계획 단계
- ○ 멀티모달 API PoC — API 후보 비교만 완료([`docs/API_SELECTION.md`](docs/API_SELECTION.md)), 실제 호출 전
- ○ Safety Simulation — 계획 단계

## 업로드 공공 운항데이터 반영 (v0.5)

이 채팅방에 업로드된 실제 CSV 두 개를 원본 그대로 반입하고 SHA-256·스키마·레코드 수를 검증합니다.

- `관제기반_선박운항정보.csv`: 522건
- `선박위치정보.csv`: 528건
- 두 파일의 `callsgn` 교집합: **0건** — 선박 단위 결합 금지
- 용도: 공공 운항정보 품질검증 및 향후 VLM/LLM·Safety Simulation 입력 설계
- 제외: 이미지 정답 라벨, CNN/MobileNet 학습, Clean/FGSM 성능 근거

상세 계약과 해시는 [`docs/PUBLIC_DATA_VTS.md`](docs/PUBLIC_DATA_VTS.md)를 참조하세요.
