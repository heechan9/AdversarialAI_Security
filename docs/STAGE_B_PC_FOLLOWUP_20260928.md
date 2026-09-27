# PC 현재 환경의 선택 사례 재실행 결과

2026-09-28 KST 수신·검토. 기준 코드: `491b973cd9f4840664044a83c0d62d1ee1bb98e8`.

## 확인 결과

반환 ZIP의 `run-report.json`, `native-trace/report.json`, 실행 로그를 확인하고 ZIP CRC 및 `SHA256.json`에 열거된 12개 파일의 SHA-256을 대조했다. CRC 오류와 해시 불일치는 없었다.

- 실행 상태: `TRACE_COMPLETE_NOT_APPROVED`, 종료 코드 0, 실제 추론 수행 true.
- 실행 시간: 2026-09-28 00:06:23.489–00:07:51.203 KST, 약 87.7초.
- 실행 기록상 모델 2개와 이미지 781개 해시 검증 완료. 실제 추론 진단 대상은 아래 4장·5개 비교 항목이며, 781장 전체 평가가 아니다.
- 모델 가중치 변경 없음. 5개 추적 모두 계측 공격 배열과 기존 생성 함수 출력이 바이트 단위로 일치했다. 이는 계측 충실성 확인이며 공격 로직의 무오류 증명은 아니다.

| 필터 | 경로 | ε | 이미지 | 기준 인덱스 | 이번 PC 인덱스 |
|---|---|---:|---|---:|---:|
| Gaussian | adaptive_defended | 0.03 | DDG/DDG_1056.jpeg | 7 | 7 |
| Gaussian | attacked | 0.03 | Bulkers/Bulkers_1039.jpeg | 1 | 1 |
| Mean | adaptive_defended | 0.05 | Car Carrier/Car Carrier_82.jpeg | 3 | 3 |
| Mean | attacked | 0.03 | Bulkers/Bulkers_1039.jpeg | 1 | 1 |
| Mean | transfer_defended | 0.05 | Recreational/Recreational_1048.jpeg | 1 | 1 |

모두 기존 기준 **예측**과 일치했다. 이는 모두 정답을 맞혔다는 뜻이 아니다. 기존 32장 배치 구성으로 선택 사례를 추적했다.

## 환경과 해석

Windows, Intel Core i5-1335U(10코어·12논리프로세서), Conda, Python 3.11.15, TensorFlow 2.21.0, Keras 3.15.1. oneDNN 환경변수와 스레드·결정성 환경변수는 미설정 상태를 상속했다. 실제 로그에는 oneDNN custom operations가 켜져 있다고 기록되어 있다. 환경변수 미설정을 oneDNN off로 해석하지 않는다.

이전 Linux oneDNN off 진단에서 남았던 5개 항목이 이번 PC 현재 환경에서는 기준과 일치했다. 환경에 따라 예측 차이가 관찰된다는 추가 근거이나 CPU, oneDNN, 스레드, 빌드 중 단일 원인을 확정하지 않는다. `original_environment_identity_proven=false`이며 현재 환경이 과거 기준 결과 생성 당시와 완전히 동일하다는 증명은 없다.

기존 B단계 FAIL 기록, 공식 승인 상태 false, canonical/provisional/experimental 결과와 허용오차는 유지한다. 이번 선택 진단만으로 전체 781장·모든 조건의 독립 검증 PASS를 선언하지 않는다. 기존/현재 텐서 간 정량 비교와 전체 조건 재실행은 이번 수신 감사에서 수행하지 않았다.

## 증거 보존

수신 파일: `return-evidence(1).zip`.
SHA-256: `91ca97a5011f0a75dbf5c1e62e9c645df9c553910848721ee43f5d5ed60bde3f`.

ZIP에는 원본 이미지에서 파생한 배열과 로컬 경로가 포함되어 있어 공개 저장소에 올리지 않는다. 본 문서는 공개 가능한 결과 요약이며, 원본 반환 ZIP은 별도 보존한다. 기존 실험 표와 모델·원자료는 변경하지 않았다.
