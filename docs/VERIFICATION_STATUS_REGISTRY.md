# 실행별 검증 상태 등록부와 표시 갱신

2026-10-01 도입. 실험·추론을 추가하지 않고 보존 근거의 상태를 일관되게 표시한다.

## 등록부와 생성물

- `results/verification/status_registry.json`: 실행별 역할, 실행 커밋, 상태, 근거 파일 SHA-256, 근거 문서의 고정 커밋 링크.
- `verification/status_registry.py`: 근거 해시·조건 범위·상태 의미를 검사한 뒤 표시 데이터를 생성한다. 기본 실행은 읽기 전용 검사다.
- `web/maris/public/evidence/verification-status.json`: MARIS 소스가 직접 사용하는 생성 데이터.
- README의 `verification-status:start/end` 사이: 같은 등록부에서 생성한 표. 나머지 서술은 자동 생성 범위 밖이다.

현재 등록된 두 실행을 합산한 전체 PASS는 만들지 않는다. 연구 수행 PC의 `LOCAL_PASS`와 외부 실행의 `FAIL`을 동시에 표시한다. 외부 평균 필터는 보조 진단임을 유지한다. 확률 벡터 비교와 원인 확정은 표시 범위에서 제외한다.

## 사용법

저장소 루트에서:

```bash
python verification/status_registry.py
python -m pytest tests/test_verification_status.py -q
```

근거가 실제로 바뀌었을 때 실행 범위·역할·커밋·새 파일을 검토하고 등록부 해시를 갱신한 다음:

```bash
python verification/status_registry.py --write
python verification/status_registry.py
```

해시만 바꿔도 의미 검사를 통과하지 못하면 생성이 거부된다. 현재 어댑터는 이미 감사한 두 실행 형식만 지원한다. 새 실행·새 판정은 어댑터와 회귀 검사를 함께 검토해야 하며 기존 FAIL을 새 실행으로 덮어쓰지 않는다. 로컬 실행자 역할을 external로 바꾸거나 근거 없이 외부 PASS로 승격할 수 없다.

CI는 근거 파일 변경, 미생성·오래된 MARIS 데이터, README 자동 표의 수동 변경, 범위 누락을 실패로 처리한다. 등록부의 역할은 검토된 메타데이터 선언이며 신원 인증이나 외부 공증이 아니다. 전체 반환 ZIP의 자동 수신·새 추론·원인 분석을 수행하는 도구도 아니다. 기존 수신 감사와 비교기를 대체하지 않는다.

## 다른 프로젝트에서 선별 적용한 방식

- [법률AI 검증 등록부](https://github.com/heechan9/judicial-ai-safety-lab/blob/25d15f93de0f10dbf6698d5f5fecb7a88a3ca64e/src/judicial_ai_safety_lab/external_audit_registry.py): 검토 범위·대상 커밋·근거와 상태를 함께 기록하는 구조를 참고했다. 법률 도메인 코드나 검토자 2명 조건을 복사하지 않았다.
- [FabGuard 근거 생성기](https://github.com/heechan9/fabguard-ai/blob/519654ea2362accf2127f4255a4379132402383c/scripts/build_web_evidence.py): 근거 식별값 검증 뒤 표시 데이터 생성, 읽기 전용 stale 검사를 적용했다. 적대적AI에서는 SHA-256과 기존 감사 JSON을 사용한다.
- TriGuard의 문제 처리 이력 UI, 법률AI의 해시 체인 및 익명 검토 패킷은 이번 변경에 포함하지 않는다. 기존 Git 이력·Stage B 도구와 중복되는 기능을 확대하지 않았다.

기존 평가 코드·모델·원자료 수치·허용오차·제출 원고는 수정하지 않는다. 웹 소스 반영과 운영 사이트 배포는 별도다. 이 변경만으로 배포 사이트 갱신을 주장하지 않는다.
