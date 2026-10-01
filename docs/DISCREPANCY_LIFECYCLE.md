# 불일치 처리 이력

TriGuard의 문제 처리 방식을 적대적AI의 환경 간 예측 불일치에 맞게 적용했다. 참고 기준은 `heechan9/triguard-ai`의 `d0db55a5c0cbbad6c70970fbf7f3228430843a17`이다. 도메인 판정 코드 전체를 가져온 것은 아니다.

`results/verification/discrepancy_log.json`은 근거 해시, 대상 코드·모델·manifest, 범위와 순서 있는 사건을 보존한다. 사건 시각은 이 등록부에 기록한 시각이며 원 실험 실행 시각을 대체하지 않는다. 현재 상태는 **open(미해결)**이다. 로컬 PC 일치는 observation으로만 기록했다.

| 현재 상태 | 사건 | 다음 상태 |
| --- | --- | --- |
| open | action_recorded | awaiting_retest |
| open / awaiting_retest | observation | 유지 |
| awaiting_retest | retest_fail | open |
| awaiting_retest | retest_pass | closed |
| closed | reopen | open |

`verification/issue_lifecycle.py`는 순서·전이·해시를 검사한다. `transition()`은 기존 객체를 수정하지 않고 새 사건을 붙인 사본을 반환한다. 파일 변경은 Git 검토를 거친다. Git 밖에서 과거 이력을 다시 작성하는 행위를 암호학적으로 차단하는 기능은 아니다.

종료에는 별도로 검토한 `cross_environment_retest` 보고서가 필요하다. 보고서에는 대상 issue/commit, 원 모델·manifest 해시, 두 모델·781장·네 epsilon·두 필터·다섯 경로의 범위, 외부 실행자 선언, 완료 여부, 판정과 차이 개수를 기록한다. 기존 label 100%, metric/linf 1e-6 기준을 유지한다. 로컬 감사 JSON으로는 종료할 수 없다. FAIL은 재개방한다.

이 보고서 형식은 **수신 감사 후 기록하는 요약 형식**이다. 선언된 신원·범위를 인증하거나 원 CSV 전체를 자동 감사하는 기능은 아니다. 실제 외부 재검사 자료가 들어오면 원 산출물의 범위와 비교 결과를 기존 Stage B 도구로 검토하고 요약 근거를 작성해야 한다. 현재 실제 PASS 재검사 보고서는 없으며 테스트의 PASS 자료는 임시 디렉터리의 합성 fixture다. 처리 종료도 수치 차이의 원인 확정을 의미하지 않는다. 실행별 LOCAL_PASS/FAIL 등록부는 독립적으로 보존한다.

README와 MARIS 검증 영역은 같은 이력에서 상태를 생성한다. 웹에는 역할·설명만 표시하며 기여자 실명을 새로 추가하지 않는다.

```bash
python verification/issue_lifecycle.py
python verification/status_registry.py --write
python verification/status_registry.py
python -m pytest tests/test_issue_lifecycle.py tests/test_verification_status.py -q
```

CI는 이력 검사와 생성물 최신 여부를 확인한다. 새 추론·공식 판정 변경·제출 원고 변경·운영 웹 배포는 수행하지 않는다.
