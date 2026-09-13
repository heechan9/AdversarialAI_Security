# Research + defense integration review

Integrated into main through PR #25 at 324a53566760f47d707ab5ca8e6fa91cb6d84c16. No official result promotion.

## What is reconciled

PR #24 (`2b5256f`) research-readiness work and PR #25 (`af96a1f`) defense
code/evidence were combined in the review branch and subsequently merged. The only merge conflict was
CONTRIBUTIONS.md; both original contribution sections were retained. Parent
history preserves the existing implementation authors. Original result files
and uploaded ZIP/member hashes are unchanged.

## Initial verification (historical; latest verification below)

- Linux Python 3.12 with TensorFlow 2.21.0/Keras 3.15.1: 239 passed,
  2 dependency deprecation warnings, 13.16 seconds.
- Research Evidence Audit: PASSED; raw local image/model content unavailable here.
- Paper Claim Audit: PASSED (9/9; existing ACK v1.5 snapshot).
- Independent Gaussian Evidence Audit: PASSED, 6248 rows, 8 conditions,
  80 class summaries. Standard-library-only; no evaluator/model execution.
- Independent Stage A clean artifact recomputation: PASS.
- No timestamp-only changes to committed research audit reports are included.

These checks do not establish general defense robustness or official adoption.
Windows full combined suite has not been executed; the user supplied 28 passing
Windows defense component tests and a completed experimental evaluation.

## Completed without another PC experiment

- Standalone archived-defense audit and hash-refreshed mutation tests.
- Research-readiness and defense branch conflict reconciliation.
- Paper defense supplement v2.5, with source-derived table and claim limits.
- Original experimental results preserved; no kernel tuning or rerun.

## Still requires external input or a separate decision

- Taehee/Jaehyuk image-review responses, including human versus AI confirmation.
- Giho's independent artifact review response; do not fabricate sign-off.
- Team decision on manuscript scope, author/affiliation details and data-use basis.
- Final ACK document/PDF layout and claim-snapshot update after scope decision;
  the supplement is not a replacement submission-ready PDF.
- Official result promotion remains a separate decision; PR #25 merge was authorized and completed.
- MARIS defense imagery needs actual verified visual artifacts; aggregate CSV
  does not justify generating a defense image or heatmap. No site changes here.

No additional attack or defense execution is needed merely to wait for these
reviews. Stronger attacks or defense retraining remain separate experiments.

## Jules 감사 후 소스 검증 보완

Jules 세션 https://jules.google.com/session/11380383362183201753 은
2be4e9b19f81a7de62401e92a7466b492bdb9d52에서 source_files 미검증을 지적했다.
Codex가 고정된 세 소스 경로의 정확한 목록, SHA-256 형식, 파일 내용 및
심볼릭 링크 거부를 추가했다. LF/CRLF 변환만 허용하며 원본 ZIP 바이트는 그대로다.
이 검사는 현재 체크아웃과 실행 당시 기록 소스의 호환성을 검증하며 Git 이력 인증을
대체하지 않는다. 향후 실행 소스가 변경되면 해당 과거 체크아웃에서 감사해야 한다.

직접 재실행: Linux Python 3.12 / TensorFlow 2.21, 전체 247 passed,
Keras 의존성 경고 2개 (9.72초). Research Evidence Audit PASS,
Paper Claim Audit 9/9 PASS, Stage A PASS, Gaussian 감사 6248행/8조건 PASS.
원본 이미지·H5 독립 추론 및 실제 Windows 통합 재실행은 하지 않았다.
8개 추가 테스트는 재해시한 계약 변조, 누락/추가 소스, 잘못된 타입,
LF/CRLF 호환성과 실제 코드 변경 및 파일 누락을 검증한다.
Jules 후속 감사에서 MEDIUM-01 해결 및 잔여 차단요소 0개를 보고했다.
감사 대상은 1d8ff3582b61b466a7a740b745facd41c8adf1a6이며,
247 passed / 경고 2개 (42.62초)와 네 감사를 별도 재실행했다고 보고했다.
소유자 조건부 승인에 따라 PR #25를 병합했다. 기존 결과·공격 계약은 변경하지 않았다.

해석상 주의: 이번 결과만으로 gradient masking을 확정하지 않는다.
보고 가능한 결론은 방어 인지 FGSM에 대한 고정 전처리 방어의 한계다.
