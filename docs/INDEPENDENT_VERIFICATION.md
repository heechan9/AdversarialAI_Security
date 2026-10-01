# 독립 검증 (Independent Verification)

## 2026-10-01 검증·제출 상태 갱신

- **연구 수행 PC 전체 재실행: LOCAL_PASS.** 9월 28일 17:21 KST 완료, 10월 1일 반환 ZIP 수신·감사. CNN·MobileNetV2 × ε=0, 0.01, 0.03, 0.05 × Gaussian·Mean의 CSV 16개, 각각 781행을 실행 커밋 `b86f725`의 기준과 다시 비교했다. 다섯 경로의 예측 라벨 62,480개 및 요약 지표 비교에서 차이 0건이다. 고유 이미지 수는 781장이며 확률 벡터는 비교하지 않았다.
- **외부 독립 검증: 기존 FAIL 유지.** 외부 실행의 MobileNetV2 14장·16개 예측 차이는 이번 PC에서 모두 기준과 일치했으나, 환경 간 차이의 단일 원인은 미확정이다. 같은 공격 배열의 환경 간 교차 분류는 추가 작업이다. 로컬 재현을 외부 독립 검증 승인으로 쓰지 않는다.
- **논문 제출 완료(사용자 확인).** 실제 제출본은 `KIPS 학술벌표대회_김태희팀_0930_멘토검토본.doc`이다. v7.5는 이전 로컬 검토본이다. 제출 파일은 수정하지 않으며 접수증·학회 채택은 별도로 확인한다.
- 이번 갱신은 상태 문서 동기화다. 개인 저장소의 진단 도구·비교기 개선이 팀 코드에 모두 병합됐다는 뜻은 아니다. 기존 실험 수치·모델·승인 필드·허용오차는 유지한다.

[전체 PC 수신 감사·환경 비교](https://github.com/heechan9/AdversarialAI_Security/blob/e6e575fa3df1247f8e43ac9749a573329f62a910/docs/STAGE_B_PC_FULL_20260928.md) · [파생 감사 JSON](https://github.com/heechan9/AdversarialAI_Security/blob/e6e575fa3df1247f8e43ac9749a573329f62a910/results/verification/stage_b/pc_full_20260928/received_audit.json) · [제출본 보존 기록](https://github.com/heechan9/AdversarialAI_Security/blob/e6e575fa3df1247f8e43ac9749a573329f62a910/docs/PAPER_RELEASE_STATUS.md)

Clean·FGSM 결과를 저장소의 기존 평가·감사 파이프라인 **바깥에서** 다시 계산해,
커밋된 수치와 일치하는지 확인하는 별도 검증 작업이다.

> **A단계 완료. 외부 B단계 재실행은 수행됐으나 결과 일치 판정 FAIL이며, 연구 수행 PC의 전체 재실행은 LOCAL_PASS다.**
> 실행별 범위·환경과 근거는 상단 갱신 링크를 따른다.

## 0. 불변 조건 (작업 전체에 적용)

이 작업은 다음을 **한 바이트도 수정하지 않는다.**

- `src/adversarial_ai/` 의 모델·공격·평가·감사 코드
- `results/clean/` 의 canonical Clean 결과
- `results/attacks/provisional/` 의 FGSM 예비 결과
- `results/audit/` 의 기존 감사 산출물
- `configs/` 의 실험 설정과 manifest

A단계 산출물은 신규 `results/verification/` 경로에 쓴다. B단계는 기존 평가기의 출력 보호 규칙에 따라 checkout 밖의 고유 실행 묶음에 저장한다. [실행 안내](STAGE_B_EXECUTION_CONTRACT.md)를 따른다.

**불일치는 fail-closed로 처리한다.** 재계산값이 커밋된 값과 다르면 기존 파일을
고치거나 허용오차를 넓히지 않고, 해당 검사를 FAIL로 보고하고 종료 코드 1로 끝낸다.
읽을 수 없거나 파싱되지 않는 증거도 "건너뜀"이 아니라 실패다.

## 1. 왜 "독립"인가

| 항목 | 저장소 기존 감사 | 이 독립 검증 |
| --- | --- | --- |
| 실행 주체 | `scripts/audit_research_evidence.py` (`adversarial_ai.audit`) | `verification/stage_a_clean_recompute.py` |
| 코드 재사용 | 저장소 감사 모듈 | `adversarial_ai.*` 를 **임포트하지 않음** |
| 의존성 | pandas, scikit-learn | Python 표준 라이브러리만 |
| 산출물 | `results/audit/` | `results/verification/` |

기존 감사는 `sklearn.metrics` 의 `classification_report` · `confusion_matrix` 를
정답으로 삼아 대조한다. 이 하네스는 같은 라이브러리를 쓰지 않고 precision·recall·F1·
macro/weighted 평균·혼동행렬을 정의부터 다시 구현한다. 같은 코드를 다시 돌리면 같은
가정을 다시 통과시킬 뿐이기 때문이다.

독립성은 주장에 그치지 않고 테스트로 강제된다 —
`tests/test_independent_stage_a.py::test_harness_imports_no_repository_code` 가
하네스의 import 문에 `adversarial_ai`·pandas·numpy·sklearn·tensorflow·keras 가
없음을 검사한다.

## 2. A단계 — 산출물 기반 독립 재계산 (완료)

커밋된 표본별 CSV에서 요약 지표를 처음부터 재도출해 커밋된 값과 대조한다.
모델 `.h5` 와 781장 원본 이미지 없이 clean checkout에서 실행된다.

### 2.1 검증 범위

초안(PR #20 최초 리비전)은 기준 커밋 `3c07c1b` 를 대상으로 작성돼 현재 감사 범위를
일부 잘못 기술했다. 최신 `main` 기준으로 다시 확인한 결과, 아래 항목은 기존 감사가
이미 동적으로 재계산한다.

| 기존 감사가 이미 검증하는 항목 | 위치 |
| --- | --- |
| Clean 정답 수 · 정확도 | `audit/clean.py` |
| FGSM robust accuracy · ASR · ASR 분모 | `audit/fgsm.py` |
| L∞ 계약 (`L∞ ≤ ε + 1e-6`) · ε=0 대조조건 | `audit/fgsm.py` |
| FGSM classification report · 혼동행렬 CSV | `audit/fgsm.py` |
| FGSM `linf_mean` · `fgsm_<model>.csv` 요약행 | `audit/fgsm.py` |
| Clean CSV ↔ FGSM 표본 CSV 경로·행 순서 정합 | `audit/fgsm.py` |

따라서 A단계의 실질적 추가 범위는 **Clean 쪽에 남아 있던 공백**으로 좁혔다.
기존 감사는 Clean CSV의 확률 컬럼을 한 번도 읽지 않고, Clean classification report와
Clean 혼동행렬을 재계산하지 않는다.

| A단계가 새로 검증하는 항목 | 검사 이름 |
| --- | --- |
| 확률값 유한성 (NaN·inf 없음) | `clean.probabilities.finite` |
| 확률값 범위 `[0, 1]` | `clean.probabilities.range` |
| 행 합 ≈ 1 | `clean.probabilities.row_sum` |
| argmax 유일성 (동점 시 판정 불가로 실패) | `clean.probabilities.argmax_unique` |
| argmax ↔ `predicted_index` 일치 | `clean.probabilities.argmax_matches_predicted_index` |
| `predicted_index` ↔ `predicted_label` ↔ 클래스 맵 | `clean.predicted_index_matches_predicted_label` |
| `true_index` ↔ `true_label` ↔ 클래스 맵 | `clean.true_index_matches_true_label` |
| Clean 혼동행렬 CSV 독립 재계산 | `clean.confusion_matrix.shape` · `.cells` |
| Clean classification report JSON 독립 재계산 | `clean.report_json.keys` · `.values` |
| Clean classification report CSV 독립 재계산 | `clean.report_csv.sections` · `.values` |
| summary JSON 헤드라인 지표 대조 | `clean.summary_json.headline_metrics` |

### 2.2 허용오차

| 대상 | 허용오차 | 근거 |
| --- | --- | --- |
| 확률 행 합 | `1e-5` | float32 텐서에서 직렬화된 값 |
| 확률 범위 | `1e-6` | 위와 동일 |
| report·혼동행렬 값 | `1e-9` | 커밋된 라벨의 float64 함수 — 사실상 정확히 일치해야 함 |
| `summary.test_accuracy` | `1e-6` | Keras `evaluate()` 의 float32 반환값 |

`test_accuracy` 만 느슨한 기준을 쓰는 이유는 이 값이 표본별 라벨에서 재계산된 값이
아니라 float32 경로로 따로 기록된 값이기 때문이다(CNN 기준 실측 차이 약 `9.3e-9`).
`macro_f1` · `weighted_f1` · `correct_predictions` 는 느슨한 기준을 쓰지 않는다.

### 2.3 검증 대상 집합을 숨길 수 없게 하는 장치

검증 대상 모델은 `results/clean/` 에 남아 있는 파일이 아니라
`configs/experiment.yaml` 의 `models:` 로스터에서 읽는다. 결과 파일을 지워서
검증 범위를 조용히 줄이는 일을 막기 위해서다. 로스터와 실제 산출물이 어긋나면
(`declared_but_missing` / `present_but_undeclared`) 실행 자체가 실패한다.

ε 목록도 하드코딩하지 않고 설정에서 읽는다. 현재 논문 조건은
`0, 0.01, 0.03, 0.05`로 확정됐으며, 검증 하네스는 설정과 실제 산출물의 조건 집합이
어긋나면 실패해야 한다.

### 2.4 실행 방법

```bash
python verification/stage_a_clean_recompute.py
```

종료 코드 0 = 전 항목 일치, 1 = 불일치 또는 증거 판독 실패.
기본 실행은 화면 출력만 하며 파일을 쓰지 않는다. 새 보고서가 필요하면
`--output results/verification/stage_a/new-review.json`을 지정한다. 기존 파일을
덮어쓰거나 configs·Clean·공격 결과·코드 경로에 쓰는 요청은 실패한다.
원래 커밋된 `clean_recompute_report.json`은 현수의 당시 기록으로 보존한다.
저장소 코드를 임포트하지 않으므로 `PYTHONPATH` 설정이 필요 없다.

### 2.5 현수 PR 원본의 A단계 실행 기록

`main` @ `ecce270` 기준 (보고서의 `verified_commit` 필드에 실행 시점 커밋이 기록된다):

| 모델 | 표본 수 | 검사 | 결과 |
| --- | --- | --- | --- |
| `cnn_baseline` | 781 | 14 | **PASS** (불일치 0) |
| `mobilenet` | 781 | 14 | **PASS** (불일치 0) |

즉 커밋된 Clean classification report·혼동행렬·summary 지표는 표본별 CSV로부터
표준 라이브러리만으로 독립 재계산했을 때 `1e-9` 이내로 재현되며, 확률 컬럼의 argmax는
781장 전부에서 `predicted_index` 와 일치한다. 확률 행 합의 최대 오차는
CNN `1.559e-07`, MobileNet `2.209e-07` 로 float32 직렬화 오차 범위 안이다.

**이 결과가 말하지 않는 것:** A단계는 커밋된 산출물이 *내부적으로 정합적*임을 보인다.
표본별 예측 자체가 모델과 이미지로부터 실제로 나왔는지는 B단계에서만 확인할 수 있다.

### 2.6 하네스가 실제로 실패하는지 (mutation test)

항상 통과하는 하네스는 아무것도 증명하지 않는다. `tests/test_independent_stage_a.py`
의 테스트 46건이 증거를 조작한 사본에 대해 각 검사가 실제로 FAIL을 내는지 확인한다 —
확률값 변조(NaN·범위 이탈·합 불일치·argmax 동점·argmax 불일치), 라벨 변조, 혼동행렬
셀·형태 변조, report JSON·CSV 값·섹션 변조, summary 지표 변조, 파일 삭제, 파싱 불가
값, 로스터 불일치를 각각 다룬다. 여기에 미변조 사본이 PASS하는지(positive control)와
실행 후 입력 파일이 바이트 단위로 그대로인지도 포함된다.

```bash
python -m pytest tests/test_independent_stage_a.py -q
```

## 3. B단계 — 새 실행 환경의 준비 조건

`.h5` 모델을 직접 로드해 781장에 대한 예측과 FGSM 공격을 재실행하고, 커밋된 표본별
예측 자체를 재생성해 대조한다.

실행 전 자산·해시·비교 규약을 고정하는 계약과 fail-closed 점검기를 추가했다.

- 계약: [STAGE_B_EXECUTION_CONTRACT.md](STAGE_B_EXECUTION_CONTRACT.md)
- 설정: `configs/stage_b_verification_contract.json`
- 외부 계약 생성·점검·실행: [STAGE_B_EXECUTION_CONTRACT.md](STAGE_B_EXECUTION_CONTRACT.md)
- 실행 진입점: `verification/stage_b_run.py` — 기존 평가기를 별도 환경에서 재실행하고 두 필터의 전달/방어 인지 조건까지 비교한다. 독립 알고리즘 구현은 아니다.
- 확률 비교는 수행하지 않으며 라벨·요약 지표·L∞를 확인한다.
- CI의 `--contract-only` 검사는 계약·manifest 구조만 확인하며 실제 재실행 완료를 의미하지 않는다.

**새 실행 환경에 필요한 선행 조건:** 이미 완료된 실행의 미수행을 뜻하지 않는다.

- `models/cnn_baseline.h5`, `models/mobilenet_finetuned.h5` (및 필요 시
  `mobilenet_stage1.h5`) — `.gitignore` 로 제외돼 저장소에 없다. 전달돼야 한다.
- `data/test` 781장 — 동일하게 미커밋.
- 전달된 바이너리의 SHA-256이 `results/*/**_metadata.json` 기록값과 일치해야 한다
  (예: CNN `cb256b1a5d6f605d355334e4e8667257a2bfbd29e08836cc4114869bd7068701`).
- FGSM ε는 `0, 0.01, 0.03, 0.05`로 확정됐다. B단계는 동일 이미지·모델,
  고정된 전처리와 비교 규약을 확보한 뒤 진행한다.
- 기존 canonical/provisional 산출물은 사라지거나 덮어써지지 않는다.
  독립 재실행 결과는 별도 run ID 경로에 저장하고 비교 대상의 source SHA를 기록한다.

**허용오차 규약 (실행별 계약 확인):**

TensorFlow/Keras forward pass는 하드웨어·연산 순서에 따라 비트 단위로 재현되지 않는다.
따라서 B단계는 "완전 일치"가 아니라 명시된 허용오차로 판정한다. 제안 규약:

| 대상 | 제안 기준 |
| --- | --- |
| 표본별 예측 라벨 | 100% 일치 |
| 정확도 · ASR | 절대차 ≤ 1e-6 |
| 표본별 확률값 | 절대차 ≤ 1e-5 (참고 기록, 판정 미사용) |
| L∞ | `≤ ε + 1e-6` (기존 계약과 동일) |

이 표의 라벨·지표·L∞ 기준은 이번 PC 로컬 실행에서 확인·적용했다. 확률값은 판정에 사용하지 않았다. 새 외부 실행의 계약 확인은 별도로 기록하며, 로컬 실행자 확인을 팀 또는 외부 검증자의 승인으로 대체하지 않는다.

## 4. 현재 상태

| 단계 | 상태 |
| --- | --- |
| A단계 하네스 | 구현·실행 완료 — 2개 모델 28개 검사 전부 PASS |
| A단계 테스트 | 46건 통과 (mutation test 중심) |
| B단계 준비 게이트 | 구현·테스트 완료 — 모델·781장·승인·source commit이 없으면 fail-closed |
| 외부 B단계 재실행 | 수행 확인, 기준 예측과 일부 불일치하여 기존 FAIL 유지 |
| 연구 수행 PC 전체 재실행 | LOCAL_PASS; 전체 781장·모든 조건 라벨 및 요약 지표 비교 완료, 외부 독립 승인 아님 |

## 5. 검증 대상 커밋

| 항목 | 값 |
| --- | --- |
| 저장소 | https://github.com/heechan9/AdversarialAI_Security |
| 검증 시점 `main` 커밋 | `ecce270` |

## 6. 통합 검토 후 보완

Codex는 중복 JSON 키·CSV 열, 잘못된 UTF-8, 중복 모델 블록, 안전하지 않은 모델명,
출력 덮어쓰기와 Git worktree SHA 누락을 검토하고 회귀 테스트를 추가했다.
기존 메트릭 공식·수치·허용오차 및 현수의 원본 커밋·보고서는 보존했다.
A단계는 기존 Research Evidence Audit의 manifest/경로 검증과 함께 실행한다.
A단계 PASS만으로 표본의 출처나 실제 모델 추론을 입증하지 않는다.
최신 통합 검증 기록은 `docs/INTEGRATION_REVIEW.md`를 따른다.
