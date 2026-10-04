# 전달된 Stage B 결과 묶음 검사

병커 `heechan9/bunkering-ai`의 커밋 `66ae9dec2f8ea13a8f4e11b656bc0a011f238929`에서
`scripts/source_changes.py`의 전체 파일 추가·삭제·변경 탐지와
`scripts/audit_diagnostic_snapshot.py`의 결과 묶음 해시 검사 방식을 참고해 구현했다.
연구 알고리즘이나 병커의 연료·보상 계산은 가져오지 않았다.

저장소 루트에서 Python 표준 라이브러리만으로 실행한다. Windows Anaconda Prompt에서도
동일하며 경로는 실제 결과 디렉터리로 바꾼다.

```bat
python -m verification.stage_b_bundle --bundle "D:\verification\stage-b-hyeonsu-01"
```

기존 실행기가 기록한 `rerun-report.json`의 `artifact_sha256`과 실제 파일 전체를 비교한다.
파일 추가·삭제·바이트 변경 시 종료 코드 1, 잘못된 JSON·경로·심볼릭 링크는 2,
무결성 통과는 0이다. 결과와 원자료를 수정하거나 새 기준으로 자동 승인하지 않는다.

보고서 자체의 변경도 확인하려면 전달 전에 별도로 보관한 보고서 SHA256을
`--expected-report-sha256`에 전달한다. 같은 묶음에서 뒤늦게 계산한 해시는
이전 상태에 대한 독립적인 기준이 될 수 없다. 해시는 서명이나 실행자 인증이 아니다.

`integrity_status`와 `recorded_execution_status`는 별개다. 실패·중단된 실행도 파일이
그대로면 무결성 PASS가 가능하다. 기록된 PASS의 수학적 정확성이나 원본 모델 재실행을
이 명령이 검증하지 않으며, 현수의 B단계 완료나 논문 최종 승인을 의미하지 않는다.

기존 연구 수치·원고·공식 실행계약은 변경하지 않는다. 이 추가 기능의 테스트는
합성 파일에 대한 무결성 검사이며 원본 이미지 781장 추론 결과가 아니다.
