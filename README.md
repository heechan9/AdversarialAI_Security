<div align="center">

# 자율운항선박 이미지 분류 모델 적대적 AI 검증

### Clean → FGSM → Evidence Audit 기반 해양 AI 보안 연구

<img src="docs/assets/adversarial-ai-industrial-security-hero.jpg" alt="산업형 스마트항만과 자율운항선박 AI 보안 프로젝트 비전" width="900">

<br>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.21-FF6F00?logo=tensorflow&logoColor=white)
![Keras](https://img.shields.io/badge/Keras-3.15-D00000?logo=keras&logoColor=white)
![Tests](https://img.shields.io/badge/tests-47_passed_%7C_2_skipped-2EA44F)
![Evidence Audit](https://img.shields.io/badge/evidence_audit-PASS-2EA44F)
![Paper Claims](https://img.shields.io/badge/paper_claims-7%2F7_PASS-2EA44F)
![Data](https://img.shields.io/badge/test_images-781-0054A6)

선박 사진을 인식하는 AI가 미세한 입력 교란에도 안전한지 확인하고,  
실험 결과가 원자료와 일치하는지 자동으로 다시 검증합니다.

[30초 요약](#30초-요약) · [작동 방식](#한눈에-보는-검증-방식) · [핵심 결과](#핵심-결과를-쉽게-읽으면) · [재현 방법](#빠른-시작) · [기술문서](#문서-안내)

**2026 스마트해운물류 × ICT 멘토링**

</div>

---

## 30초 요약

> **한 문장으로:** 선박 분류 AI가 정상 사진은 얼마나 잘 맞히는지, 사람이 거의 느끼기 어려운 작은 교란을 넣었을 때 얼마나 쉽게 틀리는지, 그 결과를 다시 검증할 수 있는지를 연구합니다.

자율운항선박은 카메라로 주변 선박의 종류와 상황을 파악할 수 있습니다. 그런데 공격자가 이미지의 픽셀을 아주 조금 바꾸면 사람 눈에는 비슷해 보여도 AI의 판단은 달라질 수 있습니다. 이 프로젝트는 이러한 **적대적 공격(adversarial attack)**을 선박 이미지 분류 모델에 적용해 취약성을 측정합니다.

- CNN과 MobileNetV2가 공격 없는 사진 781장을 분류하는 기준 성능을 확인했습니다.
- 가장 기본적인 1단계 공격인 FGSM을 구현하고 교란 크기가 약속된 범위를 넘지 않는지 검사했습니다.
- 공격 성공률은 원래 정답을 맞힌 사진만 대상으로 계산해 수치가 과장되지 않도록 했습니다.
- CSV·JSON·manifest·모델 해시·문서의 수치가 서로 맞는지 독립 감사 도구로 다시 확인합니다.
- 현재 FGSM 수치는 멘토의 epsilon 범위 승인 전 **예비 결과(provisional)**이며 공식 결과로 확정하지 않았습니다.

## 한눈에 보는 검증 방식

<div align="center">

<img src="docs/assets/adversarial-ai-evidence-pipeline-hero.svg" alt="Clean baseline부터 FGSM 공격과 근거감사까지 이어지는 검증 파이프라인" width="1000">

</div>

1. **기준 성능을 측정합니다.** 공격하지 않은 781장으로 CNN과 MobileNetV2의 Clean 성능을 확인합니다.
2. **사진에 작은 교란을 넣습니다.** FGSM이 손실이 커지는 방향으로 픽셀을 한 번 변경합니다.
3. **취약성을 수치로 비교합니다.** 공격 후 정확도, 정확도 하락폭, 공격 성공률(ASR), 최대 교란량을 계산합니다.
4. **결과의 근거를 다시 검사합니다.** 원자료와 요약표·문서가 다르거나 데이터가 변조되면 감사 프로그램이 실패 코드로 종료됩니다.

> 이 이미지는 연구의 검증 흐름을 설명하기 위한 시각화입니다. 실제 선박을 자동 제어하거나 실시간 항만 운영시스템과 연동한 화면이 아닙니다.

## 지금 어디까지 완료됐나

| 연구 단계 | 상태 | 확인된 범위 |
|---|---:|---|
| Clean baseline | ✅ 검증 완료 | CNN·MobileNetV2, 테스트 이미지 781장 |
| FGSM 구현 | ✅ 검증 완료 | 공격 방향·입력 clipping·$L_\infty$ 상한·epsilon 0 대조군 |
| FGSM 성능 수치 | 🟡 예비 결과 | $\epsilon=0, 0.01, 0.03, 0.05$ |
| 연구근거 감사 | ✅ 검증 완료 | manifest·모델 해시·CSV·JSON·문서 일관성 |
| 논문 Claim 감사 | ✅ 7/7 통과 | 정본 근거에서 논문용 주장을 동적으로 재계산 |
| BIM·PGD·JSMA·방어 | ⚪ 향후 연구 | 아직 구현·검증하지 않음 |
| VLM/LLM·안전영향 시뮬레이터 | ⚪ 목표 범위 | 현재 완료 기능이나 성능 근거가 아님 |

## 핵심 결과를 쉽게 읽으면

### 1. 공격 전에는 MobileNetV2가 더 정확했습니다

| 모델 | 정답 수 | 정확도 | 쉽게 읽으면 |
|---|---:|---:|---|
| CNN | 504 / 781 | 0.6453264951705933 | 약 64.5% |
| MobileNetV2 | 613 / 781 | 0.7848911881446838 | 약 78.5% |

MobileNetV2는 CNN보다 109장을 더 맞혔습니다. 다만 두 모델 모두 Sailboat와 DDG의 재현율이 상대적으로 낮아, 공격 이전부터 클래스별 약점이 존재했습니다.

### 2. 작은 FGSM 교란에도 성능이 크게 떨어졌습니다

아래 값은 **멘토 승인 전 예비 결과**입니다.

| epsilon | CNN 공격 후 정확도 | CNN ASR | MobileNetV2 공격 후 정확도 | MobileNetV2 ASR |
|---:|---:|---:|---:|---:|
| 0.00 | 64.53% | 0.00% | 78.49% | 0.00% |
| 0.01 | 41.61% | 35.52% | 12.42% | 84.18% |
| 0.03 | 24.33% | 62.30% | 13.19% | 83.20% |
| 0.05 | 20.23% | 68.85% | 16.13% | 79.45% |

- **epsilon**은 이미지에 허용한 최대 변화량입니다. 값이 클수록 더 강한 교란입니다.
- **공격 후 정확도**는 교란된 전체 테스트셋에서 모델이 정답을 맞힌 비율입니다.
- **ASR(Attack Success Rate)**은 공격 전에는 맞혔지만 공격 후 틀린 사진의 비율입니다.
- MobileNetV2는 Clean 정확도가 더 높았지만 $epsilon=0.01$에서 ASR이 약 84.18%였습니다. 따라서 이번 실험에서는 **높은 일반 정확도가 공격 강건성을 보장하지 않았습니다.**
- 비단조적인 MobileNetV2 결과의 원인을 FGSM overshoot라고 단정하지 않으며, 추가 실험 전에는 관찰 사실로만 기록합니다.

상세 근거: [Clean 결과](docs/CLEAN_BASELINE_RESULTS.md) · [FGSM 예비 결과](docs/FGSM_PROVISIONAL_RESULTS.md)

## 기술 구조와 검증 원칙

```mermaid
flowchart LR
    A["781장 manifest"] --> B["Clean 평가"]
    B --> C["FGSM epsilon sweep"]
    C --> D["Accuracy · ASR · L∞"]
    D --> E["Evidence audit"]
    E --> F["논문 Claim 검증"]
```

- **입력 범위:** `rescale=1./255`, `[0,1]`
- **공격 방식:** Untargeted FGSM, true-label categorical cross-entropy, 정확히 1 step
- **공격 식:** `x_adv = clip(x + epsilon * sign(grad_x L), 0, 1)`
- **교란 계약:** `L_infinity <= epsilon + 1e-6`
- **대조 조건:** epsilon 0에서 정확도 하락·ASR·최대 $L_\infty$가 모두 0
- **ASR 분모:** 공격 전 정답을 맞힌 표본만 사용(CNN 504장, MobileNetV2 613장)
- **변조 탐지:** canonical 근거가 바뀌거나 문서 수치와 불일치하면 non-zero exit

## 프로젝트에서 증명한 역량

| 문제와 판단 | 수행 내용 | 확인 가능한 근거 | 실무 연결 |
|---|---|---|---|
| 높은 Clean 정확도만으로 AI 안전성을 판단할 수 없다고 정의 | 두 모델에 동일한 FGSM 평가계약과 epsilon sweep 적용 | 표본별 CSV·요약 JSON·모델별 보고서 | AI 모델 강건성 평가 |
| ASR 계산 방식에 따라 결과가 과장될 수 있음을 통제 | Clean-correct 표본만 분모로 사용하고 epsilon 0 대조군 적용 | 실험 계약·단위 테스트·변조 테스트 | 공정한 KPI 설계·품질보증 |
| 논문 수치와 원자료가 따로 변할 위험을 관리 | manifest·모델 SHA-256·CSV·JSON·문서를 동적으로 교차 검증 | Evidence Audit PASS·Paper Claims 7/7 | 데이터 거버넌스·감사 가능성 |
| 구현 범위와 향후 목표가 섞이지 않도록 구분 | FGSM 예비 결과와 BIM·PGD·VLM/LLM 계획을 명시적으로 분리 | 프로젝트 범위·결과 문서·주장 경계 | 책임 있는 기술 커뮤니케이션 |

> **최희찬의 역할:** 연구 범위와 감사 요구사항을 정의하고, Windows 환경에서 원본 이미지 781장과 로컬 모델 바이너리를 사용해 무결성·재현성·테스트를 검증했으며, 결과 리뷰와 저장소 통합을 담당했습니다. 구현·검증의 세부 출처는 [기여 기록](CONTRIBUTIONS.md)에 구분합니다.

## 왜 결과를 신뢰할 수 있나

| 검증 대상 | 확인 방법 |
|---|---|
| 테스트 데이터 | 781개 파일의 순서·구조·SHA-256 manifest 검사 |
| 모델 | CNN·MobileNetV2 메타데이터와 로컬 바이너리 SHA-256 대조 |
| Clean 결과 | 표본별 예측 CSV에서 정답 수와 정확도를 다시 계산 |
| FGSM 결과 | epsilon별 표본 CSV에서 정확도·ASR·$L_\infty$를 다시 계산 |
| 문서·논문 주장 | canonical CSV·JSON과 README·결과문서 수치를 교차 검사 |
| 변조 내성 | 수치·분모·해시·manifest·문서를 고의로 바꾸는 mutation test |

원본 이미지와 `.h5` 모델이 없는 깨끗한 Git checkout에서는 해당 바이너리의 내용 검사가 `UNAVAILABLE`로 기록되며, 확인하지 못한 항목을 PASS로 보고하지 않습니다.

## 빠른 시작

```bash
pip install -r requirements.txt
export PYTHONPATH=src

python -m pytest -q
python scripts/audit_research_evidence.py
python scripts/audit_paper_claims.py
```

Windows CMD:

```bat
conda activate adversarial_ai
cd C:\Users\hc247\AdversarialAI_Security
set PYTHONPATH=src

python -m pytest -q
python scripts\audit_research_evidence.py
python scripts\audit_paper_claims.py
```

- `audit_research_evidence.py`: 데이터·모델·Clean·FGSM·문서의 연구근거를 종합 검사
- `audit_paper_claims.py`: 논문에 사용할 7개 Claim을 canonical 근거에서 재계산
- 모든 검사가 통과하면 exit code 0, 누락·변조·계약 위반이 있으면 exit code 1

## 저장소 구성

| 경로 | 역할 |
|---|---|
| `configs/` | 클래스·테스트 manifest·실험 설정 |
| `src/adversarial_ai/` | 공격·평가·무결성·감사 패키지 |
| `scripts/` | 감사 및 실험 실행 진입점 |
| `tests/` | 계약·무결성·변조 탐지 테스트 |
| `results/clean/` | canonical Clean 결과 |
| `results/attacks/provisional/` | 멘토 승인 전 FGSM 예비 결과 |
| `results/audit/` | 연구근거 감사 보고서 |
| `docs/` | 범위·실험계약·결과·재현성 문서 |

## 문서 안내

| 문서 | 내용 |
|---|---|
| [프로젝트 범위](docs/PROJECT_SCOPE.md) | 완료 범위·Decision Gate·향후 연구 |
| [실험 계약](docs/EXPERIMENT_CONTRACT.md) | 입력·FGSM·지표·재현 기준 |
| [Clean 결과](docs/CLEAN_BASELINE_RESULTS.md) | 모델별 기준 성능과 클래스별 한계 |
| [FGSM 예비 결과](docs/FGSM_PROVISIONAL_RESULTS.md) | epsilon별 결과와 해석 제한 |
| [재현성 안내](docs/REPRODUCIBILITY.md) | 데이터·모델 배치와 실행 방법 |
| [연구근거 감사](docs/RESEARCH_EVIDENCE_AUDIT.md) | 감사 범위·상태·CLI |
| [논문 Claim 감사](docs/PAPER_CLAIM_AUDIT.md) | 7개 Claim과 canonical 근거 |
| [인과적 안전성 검증](docs/CAUSAL_SECURITY_VALIDATION.md) | 분류 취약성과 실제 운항 영향의 구분 |
| [직무 연계](docs/ROLE_ALIGNMENT.md) | 구현 증거·직무 연결·주장 한계 |
| [기여 기록](CONTRIBUTIONS.md) | 사람·AI 협업 역할과 검증 원칙 |

## 현재 한계

- FGSM 결과는 승인된 공식 결과가 아니라 예비 결과입니다.
- 두 모델의 입력 해상도는 CNN 128×128, MobileNetV2 224×224로 다릅니다.
- MobileNetV2의 학습 당시 실제 전처리·분할 비율·random seed는 확정되지 않았습니다.
- BIM·PGD·JSMA·방어기법과 전이 공격은 아직 완료하지 않았습니다.
- 분류 성능 저하가 실제 충돌·항로 이탈 같은 운항 피해를 유발한다는 인과관계는 검증하지 않았습니다.
- VLM/LLM과 안전영향 시뮬레이터는 향후 목표이며 현재 구현 성과로 주장하지 않습니다.

---

<div align="center">

**재현 가능한 실험, 검증 가능한 수치, 과장하지 않는 결론을 우선합니다.**

</div>
