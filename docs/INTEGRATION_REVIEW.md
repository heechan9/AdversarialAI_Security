# 검토용 연구 통합 기록 — 2026-09-12

## 상태와 범위

`codex/research-integration-readiness`는 **병합 전 검토용**이다. 기준 main은
`ecce270eafabc5753888dfc5aeddec44a335d999`이다. 공식 FGSM을 실행하거나 결과를
승격하지 않았으며 기존 논문 DOCX/PDF, 모델·데이터·정본 결과를 다시 만들지 않았다.

| 원본 PR | 검토한 head | 통합 방식 |
| --- | --- | --- |
| #20 현수 독립 Stage A | `b1a9b18fdccad9075ad2e4e75edc0afd4e98b798` | 원본 커밋을 부모로 보존, 후속 보완 별도 |
| #21 위협모델·클래스 ASR | `3e5a77fea53e3aeae6bd3410020e6887f364a818` | 원본 커밋 보존, 새 classwise helper 입력 검사 추가 |
| #22 논문 v1.5·준비 점검 | `5a186098be32b048f7f8f58731a254816dbcaf87` | 원본 커밋 보존, 계약·집계 연결 보완 |
| #23 Plymouth 대조 문서 | `94ca0386bf975dafc2962a093343d6842f4dc47b` | 문서 그대로 재사용 |
| #19 공식 후보 준비 | `1115bee99fc4550387769d9aa84a1a9b306628f2` | 후보 감사/문맥 기록/관련 테스트만 선택 재사용 |

#19의 승인 완료 서술, 구형 논문 v1.0, 실험 설정·기존 계약 변경은 가져오지 않았다.
#9/#19/#20/#21/#22/#23은 이 기록만으로 병합되거나 닫히지 않는다. 향후 통합 PR을
채택하면 원본 PR과의 관계를 확인한 뒤 정리한다.

## 현수 PR 독립 검토

원본 #20 head에서 직접 실행: **132 passed, 4 skipped**. Stage A는 모델별 781행을
읽고 총 28개 계산 검사를 통과했다. 원본 모델 추론을 실행한 것은 아니다.

별도의 임시 사본에서 다음을 재현했다.

| 발견 | 원본 동작 | 통합 보완 |
| --- | --- | --- |
| 중복 JSON 키 | 뒤의 정상값으로 덮이면 PASS | 중복 키 거부 |
| 중복 CSV 열 | 마지막 값을 선택해 PASS | 중복 및 예상 밖 열 거부 |
| CLI 출력이 근거 파일을 지칭 | class map을 보고서로 덮어쓰고 exit 0 | 기본 read-only, 명시적 신규 JSON만 허용 |
| `.git`이 파일인 worktree | `verified_commit=null` | git HEAD 조회로 정상 SHA 기록 |

잘못된 UTF-8, 중복 모델 블록·클래스명, 모델명 경로 이탈, 지표 배열 길이 불일치,
출력 심볼릭 링크·기존 파일 덮어쓰기도 회귀 테스트로 검사했다. 현수의 당시 보고서는
timestamp/SHA를 갱신하지 않고 그대로 보존했다.

## 공식 실행 준비 계약의 정리

- 승인 주체를 임의로 멘토 개인으로 제한하지 않는다. 팀의 실제 결정을 기록하되
  현재 템플릿은 `pending_team_confirmation`, 승인 관련 값은 비어 있다.
- 실행 계약은 검토된 코드 SHA를 가리키는 저장소 밖 JSON으로 작성한다. 계약 자체를
  커밋하면서 그 커밋 SHA를 같은 파일에 쓰는 자기참조를 피한다.
- 생성 경로는 `results/attacks/official_candidate/<run_id>/` 하나로 통일한다.
- 준비기가 실제 이미지·모델 해시와 tracked checkout의 무변경 상태를 먼저 검사한다.
  승인 계약 원본과 SHA-256을 새 후보 폴더에 저장하며, 기존 run ID는 재사용하지 않는다.
- 후보 감사는 계약·실행 ID·source SHA·실행 환경·기존 근거와의 수치 일관성을 대조한다.
  기존 평가 CLI 내부에 승인 gate를 넣지는 않았으며 실제 실행은 별도 수동 단계다.
- 준비/후보 감사의 신규 테스트는 synthetic fixture다. 가짜 모델 파일로 실제 추론을
  실행하거나 테스트용 승인 기록을 연구 승인으로 사용하지 않는다.

## 재사용과 주장 경계

논문 snapshot 감사는 #21이 canonical CSV로부터 검증한 `class_asr`과 시각 검토
감사 집계를 재사용한다. clean 오답은 ASR 분모에서 제외하고, 분모가 0이면 정의
불가로 표시한다. 클래스 맵 밖 라벨·중복 클래스명·다차원 배열은 새 helper에서 거부한다.

- Clean/FGSM 모델·공격 코드의 기존 실행 함수와 전처리는 보존했다. evaluation 파일의
  변경은 새 classwise 집계 helper에 한정한다.
- #23 문서는 Paper Claim Audit의 자동 검사 대상이 아니다. 논문 snapshot PASS도
  DOCX/PDF의 모든 문장이나 실제 Plymouth 프레임워크 준수를 검증하지 않는다.
- 육안 검토는 분할 검토이며 독립 이중 검토가 아니다. 기록의 정합성과 선종 판정의
  객관적 정확성은 구분한다. 미해결 판정은 원본 이미지를 별도로 확인해야 한다.
- MASS 제어·충돌·항로 이탈·센서융합·방어 성공을 검증했다고 주장하지 않는다.

## 통합 검증

격리된 Linux/Python 3.12 환경에서 직접 실행:

- 전체 pytest: **197 passed, 4 skipped**.
- Research Evidence Audit: **PASSED** (출력은 저장소 밖 임시 경로).
- Paper Claim Audit: **PASSED (9/9)**.
- 정상 Stage A 재계산 및 출력/파서 변조 회귀 검증 통과.
- 후보 준비·계약/환경 바인딩·후보 수치 변조 회귀 검증 통과.
- `git diff --check` 통과.

이 환경에는 TensorFlow와 원본 이미지·모델이 없다. TensorFlow 관련 테스트와 원본
바이너리 검사는 미실행이며 사용자 Windows의 과거 `96 passed, 2 skipped`와 합산하지
않는다. 의존성은 임시 검증 환경에 설치했으며 requirements를 바꾸지 않았다.

보호 파일 대조 대상: 모델·weights, `configs/test_manifest.json`, `configs/experiment.yaml`,
`results/clean/`, `results/attacks/provisional/`, 공격 생성 코드, 기존 evaluator 함수,
`results/audit/evidence_audit_report.json` 및 시각 검토 CSV 원본 세 개.

## 남은 작업

1. 최종 통합 코드의 Windows 전체 테스트·이미지 781장/모델 바이너리 해시 검사.
2. 팀의 실제 실행 조건 기록, 공식 후보 실행과 독립 모델 재실행 검증.
3. 후보 결과 검토 후에만 별도의 공식 결과 고정·논문 수정 제안.
4. 육안 검토 미해결 표본 확인, DOCX/PDF 편집 검토, 휴대폰 실기기 확인.
5. 사용자 최종 확인 후 병합 판단. 이 작업에서 자동 병합하지 않는다.
