# Project Contributions & Provenance

## Issue #2 / PR #3: Research Evidence Audit Framework

- **Issue**: [#2 - feat(audit): independently verify Clean and provisional FGSM evidence](https://github.com/heechan9/AdversarialAI_Security/issues/2)
- **Pull Request**: [#3 - feat(audit): independently verify Clean and provisional FGSM evidence](https://github.com/heechan9/AdversarialAI_Security/pull/3)
- **Merge Commit**: `455ae36946fcc0461148b1ced501718aa5f5c321`

### Contribution Breakdown

- **google-labs-jules[bot]**:
  - Implemented the independent research evidence audit framework package (`src/adversarial_ai/audit/`).
  - Added CLI tool (`scripts/audit_research_evidence.py`) and module entrypoint (`python -m adversarial_ai.audit`).
  - Generated audit report artifact (`results/audit/evidence_audit_report.json`).
  - Authored documentation (`docs/RESEARCH_EVIDENCE_AUDIT.md`).
  - Added unit test suite (`tests/test_audit.py`) and mutation test suite (`tests/test_audit_mutations.py`) proving tampered evidence causes non-zero exit codes.

- **heechan9**:
  - Defined audit scope and specifications in Issue #2.
  - Performed local environment validation on Windows using the full raw 781-image dataset and local `.h5` model binaries.
  - Verified cross-platform UTF-8 encoding compliance and test results.
  - Reviewed execution artifacts and approved integration into `main`.

## PR #11: Claim-Level Paper Evidence Audit

- **Pull Request**: [#11 - feat(audit): add claim-level paper evidence verification](https://github.com/heechan9/AdversarialAI_Security/pull/11)

### Contribution Breakdown

- **Codex**:
  - Designed and implemented the claim-level paper evidence audit module and CLI.
  - Added dynamic comparison of paper-facing FGSM summary rows against canonical Clean and sample-level FGSM evidence.
  - Added mutation tests for numeric tampering and premature `official` status changes.
  - Authored the Claim audit contract documentation.

- **heechan9**:
  - Selected the integration scope and preserved the provisional/official decision boundary.
  - Ran Windows validation with the full 781-image dataset and both local `.h5` model binaries.
  - Confirmed `47 passed, 2 skipped`, research evidence audit PASS, and paper Claim audit 7/7 PASS.

## PR #17: Strict Visual-Review Audit Extension

- **Pull Request**: [#17 - feat(audit): implement strict visual-review evidence audit extension](https://github.com/heechan9/AdversarialAI_Security/pull/17)

### Contribution Breakdown

- **Google Jules**:
  - Implemented the strict visual-review evidence audit extension (`src/adversarial_ai/audit/visual_review.py`).
  - Integrated visual-review verification into the audit runner (`runner.py`) and paper claim audit (`paper_claims.py`, `CLAIM-008`).
  - Added unit tests (`tests/test_visual_review_audit.py`) and mutation tests (`tests/test_audit_mutations.py`).
  - Authored visual review audit documentation (`docs/VISUAL_REVIEW_AUDIT.md`).

- **Codex**:
  - Independently reviewed PR #17 and reproduced audit-bypass cases involving BOM removal, review dates, schema drift, strict-criterion changes, and overly broad confidence tolerance.
  - Hardened the audit with exact schema/BOM/date validation, canonical three-decimal confidence comparison, evidence SHA-256 verification, and expanded mutation tests.
  - Preserved the supplied CSV bytes through an explicit Git text-normalization rule and removed unsupported fixed test-count reporting.

- **김태희**:
  - Performed assigned partitioned visual review for 31 candidate images (`review_taehee_visual_strict_final.csv`).

- **이재혁**:
  - Performed assigned partitioned visual review for 32 candidate images (`review_jaehyuk_visual_strict_final.csv`).

- **최희찬 (heechan9)**:
  - Defined the audit extension scope and supplied the authoritative evidence CSV artifacts.
  - Authorized conservative code review and repository integration after all automated checks pass.

## Codex Security Audit

- **Codex**:
  - Independently reviewed the evidence-audit implementation for path handling,
    malformed CSV/JSON input, unsafe execution and deserialization, secret
    exposure, dependency and GitHub Actions risk, audit bypasses, and fail-open
    behavior.
  - Implemented fail-closed path, boolean, numeric, provenance, Git identity,
    canonical FGSM-row, classification-report, confusion-matrix, and summary
    validation.
  - Added mutation tests for the reproduced bypass cases and documented the
    remaining supply-chain and environment limitations.

- **최희찬 (heechan9)**:
  - Authorized the independent security-audit scope and requested review through
    a separate Draft pull request before integration.

## Experimental Gaussian defense (PR #25)

- Codex: implemented differentiable preprocessing and defense-aware FGSM evaluation, tests, and independently recalculated uploaded sample evidence and summaries.
- 최희찬 (heechan9): ran component tests and the full two-model evaluation on the local Windows PC and supplied the original result ZIP.
- No team or mentor approval of official adoption is implied.

## 검토용 통합 브랜치 (2026-09-12, 미병합)

- **이현수 (HyeonSuuuuu)**: PR #20의 독립 Clean 재계산 하네스, 관련 문서·mutation
  tests와 당시 실행 보고서. 원본 커밋 `3622891`, `b1a9b18`의 저자·메시지를 유지했다.
  해당 커밋에 기록된 Claude 사용은 작성자가 남긴 보조 도구 사용 기록이며,
  이 문서는 Claude를 별도 GitHub 계정 Contributor나 논문 저자로 인증하지 않는다.
- **Codex <codex@openai.com>**: PR #20의 독립 검토, 파서/출력 보완 및 회귀 테스트,
  PR #21/#22/#23 통합, PR #19의 후보 감사·실행 문맥 기록 코드 재사용과 계약 연결,
  클래스별 감사 결과 재사용, 통합 검증·문서 정리. 새 로컬 통합·보완 커밋의 저자를 Codex로 기록했다.
- **최희찬 (heechan9)**: 검토·통합 작업 요청과 병합 전 중단 범위 결정.
  이 작업은 새로운 로컬 모델 추론이나 실기기 검증 기여를 추가로 주장하지 않는다.

기존 기여 기록과 커밋 저자는 변경하지 않았다. 이 통합안은 Draft 검토 대상이며,
원본 PR의 실제 병합 여부나 공식 FGSM 결과 확정을 의미하지 않는다.

게시 경로 참고: 이 환경의 터미널에는 GitHub push 인증이 없어 GitHub 연결 도구로
동일한 검증 tree를 게시한다. 해당 도구는 author 필드 지정을 제공하지 않으므로
원격 통합 커밋은 인증된 heechan9 계정으로 생성되고, 실제 보완 구현자인 Codex는
커밋의 `Co-authored-by: Codex <codex@openai.com>`와 이 문서로 구분한다.
이는 heechan9가 보완 코드를 독립 구현했다는 뜻이 아니다. 현수 및 기존 PR의 원본
커밋들은 원격 통합 커밋의 부모 이력으로 보존한다.

## 평균 필터 비교 실험 (2026-09-16, experimental)

- 최희찬 (heechan9): Windows에서 구성요소 테스트(사용자 로그 19 passed)와 전체 선박 이미지 실험을 실행하고 원본 ZIP 제공.
- Codex: 고정 평균 필터와 실행 연결 구현, 제공된 CSV/JSON의 독립 재계산, 근거 감사·mutation tests 및 Git 통합. 실제 모델 재추론이나 팀/멘토의 공식 채택을 대신하지 않음.

## CPU CI·교차 검수 체계 보강 (2026-10-07)

- 최희찬: 범위·수용 기준 지정, 기존 결과와 현수 독립 재현 보존 요구.
- Codex: 기존 CPU workflow 확장, 필수 실행 게이트·합성 로더 회귀 검사 및 문서 구현, 자체 검사.
- GitHub Actions: PR의 정확한 head에 연결된 기계 검사. 결과는 PR 실행 링크 참조.
- Claude: 사용자가 전달한 병합 SHA b4b1274 감사에서 537 passed/0 skipped와 낮음 3건 보고. Codex 직접 실행과 구분. Jules: PR #79 감사에서 Python 3.12.13의 537 passed/0 skipped 보고. 전달 공격 표기 오류와 검사 한계는 그대로 승인 근거로 사용하지 않음.
- 병합: 사용자 후속 요청에 따라 Codex가 PR #79 병합 실행, main b4b1274 및 CI 성공 확인. 구현자 자체 검사를 외부 독립 승인으로 간주하지 않음.

## Iterative 저장 근거 파싱 보강 (2026-10-14)

- 최희찬: PC 없이 가능한 저장소 개선 작업 요청.
- Codex: 중복 JSON 키·모호한 CSV 파싱 반례 재현, 감사 파서와 합성 회귀 검사 보강,
  공개 checkpoint 재계산. 원본 모델 추론·GPU 실험·외부 독립 승인은 수행하지 않음.
- GitHub 연결 도구의 원격 커밋 계정과 구현자를 구분하며, Codex 기여는 커밋 trailer로 기록한다.

## MARIS bilingual readability update (2026-10-18 KST)

- 최희찬 (heechan9): requested improved readability/design, English support, collaboration with Claude/Jules, and publication to the existing site after verification.
- Codex: implemented the bilingual interface, evidence-led navigation/layout, historical-status labeling, regression tests, and source review fixes. Existing evidence JSON, images, scientific metrics and original contributors remain unchanged.
- Claude: reviewed actual public baseline screenshots and suggested spacing, hierarchy and mobile-oriented layout improvements. Claude did not inspect the rendered candidate; this is design feedback, not independent experimental validation.
- Browser QA of the updated site and external head-specific review remain pending at this commit. No new model inference or full reproduction is claimed.
- GitHub connector publication uses the authenticated heechan9 account; actual implementation credit is recorded by the Codex commit trailer and this entry. This does not claim independent human implementation.

## MARIS recorded-evidence mission flow (2026-10-18 KST)

- 최희찬 (heechan9): requested a game-like opening interaction, approved the static design direction, and required preservation of the research content.
- Codex: implemented the case/condition/prediction/reveal loop, bilingual interaction feedback, replay/reset, separate aggregate-only filter comparison, regression coverage and source review fixes. A second Codex source-only review is not Claude/Jules review or independent experimental validation.
- Original evidence files, model predictions, scientific metrics and lower research sections are preserved. No new model inference, defended outcome for an individual case, navigation/collision simulation or hardware test is claimed.
- The two design previews are explicitly static layouts, not browser captures. Candidate browser QA was blocked by the available preview environment and remains a separate release check.
- GitHub connector publication uses the authenticated heechan9 account; the implementation is credited to Codex in the commit trailer. Existing contributors and history remain unchanged.

## 김태희 고정 baseline CPU 재실행 인계 (2026-10-23 KST)

- 김태희: 고정 baseline `9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf`의 CPU 회귀·공개 저장 증거 검사 자료를 제출했다. r2 인계요약에서 반환 ZIP을 직접 열어 로그·종료코드를 확인했다고 보고했다. PR81 웹·기존 CI 원문·CI 아티팩트 비교는 본인이 직접 하지 않았다고 구분했다.
- Claude/Cowork: 제출 자료에 따르면 클라우드 Linux에서 prepare/run 실행, Git 기록 비교와 양식 초안 작성에 사용됐다. 태희 PC에서의 직접 실행이나 새 781장 모델 추론으로 기록하지 않는다.
- Codex: 수신 ZIP의 경로·CRC·22개 내부 해시, 요약 변경, JUnit 541개 및 기존 CI 552개·수신 당시 main CI 780개 원본 아티팩트를 읽기 전용으로 대조했다. 새 모델·CPU 실험은 실행하지 않았다.
- 최희찬 (heechan9): 수정본의 Git·공유 Drive 반영 범위를 지정하고 r2 완료 자료를 전달했다. 기여는 ‘고정 버전 CPU 재실행 자료 제출·확인’이며 2차 작업 전체 완료나 독립 모델 재현 성공을 뜻하지 않는다.
- [수신 검산 및 검증 경계](docs/reviews/20261023/taehee_cpu_handoff_review.md)를 함께 보존한다. 원본 ZIP·개인 작업경로·비공개 자료는 Git에 추가하지 않는다. 원격 게시 계정과 실제 문서 작성자를 구분하며 Codex의 문서 정리는 커밋 trailer로 기록한다.

## Matched CNN follow-up result package (2026-10-24 KST)

- 최희찬 (heechan9): authorized the separate Colab experiment, completion check and publication of reviewable results; required review before merge and preservation of historical failures.
- Codex assistance: prepared and operated the authorized Colab workflow, implemented the separately pinned evaluator, recalculated saved CSVs, documented protocol deviations and limitations, and prepared the review PR with a standard-library auditor and mutation checks.
- The retained batch records one training seed and three model evaluations of 781 images each. This publication review does not run models again or confer independent experimental approval. Existing teammate credits, paper results and external Stage B FAIL remain unchanged.
- Source and evidence: [one-seed matched CNN follow-up](results/extensions/matched_cnn_20261024/README.md). GitHub connector commits use the authenticated account; the Codex trailer identifies implementation/documentation assistance rather than independent human authorship.

