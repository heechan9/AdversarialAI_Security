# 원본 상태판 후속 검증 — 2026-10-07

## 직접 실행
Codex가 별도 깨끗한 worktree에서 원본 main `2e9bf4ac0e4c5506f6b65d1ffad4e10059220d7b`를 검사했다.
Python 3.12.14, TensorFlow 2.21.0, Keras 3.15.1, NumPy 2.5.3, pandas 3.0.6.
원본 requirements.txt로 별도 가상환경에 설치했고 pip check exit 0.
CPU 검사 설정: CUDA_VISIBLE_DEVICES=-1, TF_NUM_INTRAOP_THREADS=2, TF_NUM_INTEROP_THREADS=1.
이는 검사 환경 설정이며 과거 공식 실험 환경의 재현을 의미하지 않는다. oneDNN 설정은 별도로 덮어쓰지 않았다.

- `PYTHONPATH=src:. python -m pytest -q`: exit 0, **444 passed, 0 skipped, 4 warnings, 13 subtests passed** (20.80s).
- `run_full_audit(repo_root=Path("."), output_report_path=<저장소 밖 JSON>)`: PASSED. CLI의 기존 보고서 덮어쓰기를 피하기 위해 동일 runner 함수를 호출했다.
- `PYTHONPATH=src:. python scripts/audit_paper_claims.py`: exit 0, PASSED 9/9.
- `python verification/status_registry.py`: exit 0, 저장 근거·표시 일치.
- 검사 후 원본 worktree git status: 변경 없음.

## 검사 당시 범위와 미완료
공개 CSV/JSON의 내부 정합성과 합성 입력 테스트다. 원본 781장 이미지 내용 및 모델 바이너리 해시 재계산은 **NOT_RUN / UNAVAILABLE**.
외부 MobileNetV2 14장·16개 예측 차이와 FAIL/open을 그대로 유지한다. 교차 환경 공격 배열 재분류는 수행하지 않았다.
공식 실행계약의 승인자·승인시각·실행 SHA·run ID를 임의로 채우지 않았다. 팀 확인 및 실제 공식 실행 증거가 필요하다.
논문 접수증·채택 여부는 미확인이다. 외부 인간 승인이나 현수 독립 재현 완료를 주장하지 않는다.

## 문서 수정
PAPER_CLAIM_AUDIT.md 및 ROLE_ALIGNMENT.md의 ε 범위 승인 대기 표현을 CURRENT_RESEARCH_STATUS의 2026-09-20 사용자 확인 기록과 구분했다.
범위 확정, provisional 원자료 보존, 별도 공식 실행 승인·재실행 기록 미연결을 각각 명시한다.
문서 수정 커밋: `8e0e805f4599730a929bb79125c6b0f2b38ed743`.
팀 검토 상태: 수정완료, 별도 검토자의 재확인 대기. 새 승인 사실을 추가하지 않았다.

## 원본과 포크
원본 기준을 개인 포크의 CPU CI 통과로 대체하지 않는다. 포크 PR #80의 회귀 검증은 별도 SHA의 결과다.
원본 대상 PR 생성은 연결의 쓰기 권한 부족(HTTP 403 Resource not accessible by integration)으로 실패했다.
수정은 개인 포크의 `docs/upstream-epsilon-status` 브랜치에만 보존했다. 원본 main 병합은 수행하지 않았다.
원본/포크 전체 동기화, #78 GPU 실험, 재학습은 수행하지 않았다.

## 사용자 후속 확인 — 2026-10-07 19:24 KST
최희찬이 환경 불일치 후속 재검사, 공식 실행 승인, 논문 접수·채택에 대해 “이미 다 잘 된 부분”이라고 확인하고 완료 처리를 요청했다.
업무 상태는 세 항목 모두 **사용자 확인 완료**로 기록한다. 위 미확인은 이 확인 전 도구로 증빙을 조회한 당시의 상태다.
이는 사용자 전달 보고이며 Codex의 직접 재추론·접수증 열람·채택 통지 열람 결과가 아니다.
기존 FAIL/open 원시 검증 기록, 계약의 승인 필드 및 run ID는 해당 증빙과 연결하기 전까지 덮어쓰지 않는다.
실제 승인 발생시각과 사용자 확인시각을 동일하게 만들지 않으며, 검증 도구의 PASS로 변환하지 않는다.
문서 수정 후 작성자 추가 검사: 444 passed, 4 warnings, 13 subtests passed(24.85s), 논문 감사 9/9. 테스트 대상은 원본 코드와 두 문서 수정이며 이 후속 보고 문구는 별도 문서 변경이다.
