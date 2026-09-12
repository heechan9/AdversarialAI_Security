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
