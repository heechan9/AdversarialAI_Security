# 독립 감사 보고서: Gaussian Defense 및 통합 연구 근거 (PR #25)

**감사 대상 커밋**: `2be4e9b19f81a7de62401e92a7466b492bdb9d52` (`codex/gaussian-defense`)
**기준 Base 커밋**: `ecce270eafabc5753888dfc5aeddec44a335d999` (`main`)
**감사 성격**: 독립적 READ-ONLY 코드 및 학술 연구 근거 감사 (코드 수정/병합/푸시 없음)

---

## 1. 발견 사항 요약 (Order: Critical / High / Medium / Low)

### [MEDIUM-01] `audit_gaussian_defense.py`의 계약 소스 파일 (`source_files`) 미검증 갭
- **위치**: `scripts/audit_gaussian_defense.py`, `audit()` 함수 (약 57행 부근)
- **재현 방법**: `contract.json` 내의 `source_files["src/adversarial_ai/defenses/gaussian.py"]` 해시 값을 임의의 SHA-256 문자열로 변경하거나, 소스 코드 파일을 변경하더라도 `python scripts/audit_gaussian_defense.py` 실행 시 여전히 `PASSED`를 반환함.
- **영향**: 공격자가 방어 수치나 결과를 그대로 두고 `gaussian.py`나 `defense_evaluation.py` 소스 코드를 변조하거나 계약에 기록된 소스 해시를 거짓으로 작성하더라도 독립 감사 스크립트가 이를 감지하지 못함.
- **권장 수정 방안**: `scripts/audit_gaussian_defense.py`에 다음 소스 검증 코드 추가:
  ```python
  for rel_path, expected_sha in contract.get('source_files', {}).items():
      src_file = repo / rel_path
      require(src_file.exists() and digest(src_file.read_bytes()) == expected_sha, f'source file mismatch: {rel_path}')
  ```
- **회귀 테스트**: `/home/jules/self_created_tools/test_fail_closed_tampering.py` 내 `mod_contract_source_files` 테스트.

### [LOW-01] Keras / NumPy 2.0 마이그레이션 관련 DeprecationWarning 발생
- **위치**: `tests/test_defense_evaluation.py::test_full_orchestration_synthetic_assets`
- **영향**: `pytest` 실행 시 경고 2건 발생 (`DeprecationWarning: __array__ implementation doesn't accept a copy keyword...`). 기능적 동작이나 테스트 패스에는 영향 없음.
- **권장 수정 방안**: Keras backend `np.array(x)` 호출 시 copy 파라미터 전달 방식 보완 (상위 라이브러리 업데이트 대응).

---

## 2. 항목별 세부 검증 결과

### 1) 방어 구현 및 수학적/미분 연속성 검증 (`src/adversarial_ai/defenses/gaussian.py`)
- **고정 3×3 가우시안 커널**: `((1,2,1),(2,4,2),(1,2,1))/16` 규격 및 채널별 독립 적용, `mode="REFLECT"` 패딩 정확함.
- **NumPy/TF 일치성**: 동일한 NHWC float32 입력에 대해 `gaussian_numpy`와 `gaussian_tensorflow` 간의 최대 차이가 `0.00000000`으로 완전 일치함.
- **Adaptive FGSM $f(D(x))$ 기울기 미분**: `generate_adaptive_fgsm`에서 `GaussianDefendedModel(model)`을 `generate_fgsm`에 전달하여 `tf.GradientTape` 내에서 `gaussian_tensorflow(images)`를 직접 경과시킴. Detached NumPy나 원본 모델 단독 기울기 우회가 없으며, 방어 전 입력 $x$에 대해 참(True) 미분 기울기 $\nabla_x L(f(D(x)), y)$가 전달됨.
- **입력 검증 및 경계**: [0,1] 클리핑, $x_{adv} - x$에 대한 $L_\infty \le \epsilon + 1e-6$ 예산 적용, $\epsilon=0$ 시 입력 완전 동일($x_{adv} = x$) 보장, float32 규격, 부적절한 boolean/NaN/Inf/범위외 입력 거부 확인됨.

### 2) CSV 증거 기반 수치 및 ASR 재계산
- **재계산 결과**: `results/defenses/experimental/gaussian_run_01/*.csv` 8개 파일 전체(총 6,248행)를 직접 재계산한 결과 `summary.json` 및 `PAPER_DEFENSE_SUPPLEMENT_v2_5.md`의 표 2.5 수치와 정확히 일치함.
  - **CNN**: Clean 분모 $N=504$, Defended Clean 분모 $N=445$, Common Clean 분모 $N=389$.
    - $\epsilon=0.01$: Defended Clean 56.98%, Attacked 41.61%, Transfer-Defended 50.45%, Adaptive-Defended 31.37%, Adaptive ASR 44.94% (200/445).
    - $\epsilon=0.03$: Defended Clean 56.98%, Attacked 24.33%, Transfer-Defended 34.70%, Adaptive-Defended 12.55%, Adaptive ASR 77.98% (347/445).
    - $\epsilon=0.05$: Defended Clean 56.98%, Attacked 20.23%, Transfer-Defended 27.66%, Adaptive-Defended 8.32%, Adaptive ASR 85.39% (380/445).
  - **MobileNetV2**: Clean 분모 $N=613$, Defended Clean 분모 $N=648$, Common Clean 분모 $N=577$.
    - $\epsilon=0.01$: Defended Clean 82.97%, Attacked 12.42%, Transfer-Defended 43.66%, Adaptive-Defended 9.48%, Adaptive ASR 88.58% (574/648).
    - $\epsilon=0.03$: Defended Clean 82.97%, Attacked 13.19%, Transfer-Defended 26.63%, Adaptive-Defended 7.17%, Adaptive ASR 91.36% (592/648).
    - $\epsilon=0.05$: Defended Clean 82.97%, Attacked 16.13%, Transfer-Defended 25.10%, Adaptive-Defended 8.71%, Adaptive ASR 89.66% (581/648).
- **분모 및 집계 원칙 검증**:
  - ASR 분모는 각 평가 파이프라인의 정상 정답(Clean Correct) 표본 집합으로 엄격 제한됨.
  - 모델 내 전후 비교용 Common Clean 집합($N_{common} = N_{clean} \cap N_{defended}$)이 구분되어 있으며, 모델 간(CNN vs MobileNet) 공통 교집합은 분리 관리됨.
  - 정상 오답 표본은 ASR 분모에서 제외됨. 분모가 0인 경우 0%가 아닌 null 처리 확인됨.
  - 모든 $\epsilon$ 구간에서 정상 예측(`clean_pred`, `defended_clean_pred`)이 안정적으로 유지됨.

### 3) 아카이브 무결성 및 바이트 인증 (`original_bundle.zip`)
- **원시 ZIP SHA256**: `dc12787a7ff8a2696ea3b8e182b7e19f7ca6fc812c4a6739cb7f7f1895257df6` (PROVENANCE.json 기록과 정확히 일치).
- **Windows CRLF 바이트 보존**: ZIP 아카이브 내부의 모든 CSV/JSON 멤버 파일이 Windows CRLF(`\r\n`) 바이트를 원본대로 보존함.
- **계약 및 출처 검증**: 실행 커밋 `26324bea8ffdeb3c7b1d100229c49003ec99a587`, `COMPLETE.json` (`status: experimental_completed`, `promoted: false`), `contract.json` (`status: experimental`, `promoted: false`), `SHA256.json` 무결성 검증 완료.

### 4) Fail-Closed 오염/변조 정밀 시뮬레이션 테스트
- **격리 변조 테스트 완료**:
  - 음수/범위외 클래스 인덱스 (-1, 10), 스키마 컬럼 교체, NaN/Inf 변조, $L_\infty$ 예산 초과(0.02 > 0.01), $\epsilon=0$ 불변성 위반, `promoted: true` 승격 시도, `status: official` 변조, JSON 중복 키, 계약 input 해시 오염 등 모든 오염 시도가 감사 스크립트에서 정확히 감지되어 **Fail-Closed** 거부됨.
- **감사 구현 갭 감지**: 상기 1절의 [MEDIUM-01] (`source_files` 미검증) 확인됨.

### 5) 경로 안전성, 파싱 및 보안 위협 모델
- `audit_gaussian_defense.py` 내 ZipFile 검사 시 절대 경로, `..` 상위 디렉터리 참조, `:` 드라이브 문자가 포함된 아카이브 멤버 거부, 심볼릭 링크 거부 로직 확인됨.
- `defense_evaluation.py`의 `prepare_output`이 저장소 외부의 신규 디렉터리만을 허용하며 덮어쓰기를 금지함.
- 시크릿 노출, 디세리얼라이제이션 위험, GitHub Actions 워크플로 변경 없음.

### 6) 전체 자동화 테스트 및 감사 명령어 실행 결과
- `PYTHONPATH=src python -m pytest`: **239 PASSED** (2 warnings, 31.67초)
- `PYTHONPATH=src python scripts/audit_research_evidence.py`: **RESEARCH EVIDENCE AUDIT: PASSED**
- `PYTHONPATH=src python scripts/audit_paper_claims.py`: **PAPER CLAIM AUDIT: PASSED (9/9)**
- `python verification/stage_a_clean_recompute.py --output /tmp/stage_a_check.json`: **OVERALL: PASS**
- `python scripts/audit_gaussian_defense.py`: **PASSED** (6,248 rows, 8 conditions, 80 class summaries)

### 7) Main 대비 보호 대상 자산 불변성 확인
- `main` 브랜치(`ecce270eafabc5753888dfc5aeddec44a335d999`) 대비 모델 가중치(`models/*.h5`), `configs/test_manifest.json`, `configs/classes.json`, `results/clean/*`, `results/attacks/provisional/*`, `src/adversarial_ai/attacks/fgsm.py` 등 기존 보존 자산의 변경이 일체 없음(100% 동일).
- `CONTRIBUTIONS.md`에서 이현수, 최희찬, Codex, google-labs-jules[bot], 김태희, 이재혁의 기여 및 커밋 저작권이 명확히 보존됨.

### 8) 학술 주장 경계 (Research Claim Boundaries)
- **전달 공격 대 방어 인지 공격**: 단순 전달 공격(Transfer attack)에 대한 정확도 상승(예: CNN 0.01에서 41.61% -> 50.45%)만으로 방어의 유효성을 주장할 수 없음. 방어 인지 FGSM(Adaptive FGSM) 공격 시 정확도가 31.37%로 크게 하락하며, MobileNetV2의 경우 9.48%로 방어 적용 전(12.42%)보다 오히려 하락함.
- **물리적/자율운항 안전 검증 부재**: 1-step FGSM 전처리 실험일 뿐이며, 반복 공격(PGD), 물리적 환경 공격, 선박 충돌 회피/MASS 제어 안정성을 검증한 것이 아님.
- **원시 H5/픽셀 배열 미포함**: 아카이브에는 레코드 CSV/JSON만 포함되어 있으며 원시 H5 모델 및 픽셀 배열이 없어, 본 아카이브만으로는 독립적인 모델 추론 및 픽셀 재구성이 불가능함.
- **보충안 상태**: `PAPER_DEFENSE_SUPPLEMENT_v2_5.md`는 미병합 보충안 문안일 뿐 최종 제출 PDF가 아님.

---

## 3. 최종 판정 (Final Judgments)

### 코드 병합 준비도 (Code Merge Readiness): **PENDING (소유자 승인 및 갭 보완 필요)**
- **이유**:
  1. 코드 구현 및 수학적 기울기 처리, 파일 아카이브 무결성은 유효하나, 소유자(heechan9)의 독립 검토 및 명시적 병합 승인이 필요함.
  2. [MEDIUM-01] `audit_gaussian_defense.py`에서 `contract.json`의 `source_files` 해시를 검증하는 최소 보완 코드가 추가되는 것이 바람직함.

### 과학적 주장 지지 가능성 (Supported Scientific Claims): **CONDITIONAL PASS (보충안 범위 한정)**
- **이유**:
  1. 고정 가우시안 전처리가 전달 FGSM 공격에 대해 일부 착시적 개선을 보이지만, 방어 인지 공격(Adaptive FGSM)에 의해 무력화된다는 **보호 조치의 한계(Gradient Masking / False Sense of Security)**를 보여주는 학술적 관점에서의 보고는 완전히 정당함.
  2. 본 결과를 "일반적 선박 AI 보안 강화"나 "공식 방어 기법 채택"으로 확대 해석하지 않고, `PAPER_DEFENSE_SUPPLEMENT_v2_5.md`에 명시된 한계문단과 함께 부록/실험 결과로 한정 기록하는 조건 하에서 학술적 수치 지지가 타당함.
