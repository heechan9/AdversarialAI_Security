# 김태희 CPU 재실행 자료 수신 검산

검토일: 2026-10-23 KST. 고정 baseline의 CPU 소프트웨어 회귀와 공개 저장 증거 검사 자료를 인수한 기록이다. 코드·모델·원자료·논문 수치는 변경하지 않는다.

## 수행·확인 범위

- 김태희가 제출한 r2 요약은 반환 ZIP을 직접 열어 로그·종료코드를 확인했다고 보고한다. PR81 웹, 기존 CI 원문과 아티팩트 비교는 본인이 직접 하지 않았다고 구분한다.
- 제출 자료상 실행·Git 비교·양식 초안은 Claude/Cowork의 클라우드 Linux 지원으로 수행됐다. 태희 PC 실행이나 직접 모델 재추론을 주장하지 않는다.
- Codex는 수신 자료 및 GitHub 아티팩트를 정적으로 대조했다. 이번 수신 검산에서 모델 실행, 학습 또는 CPU suite 재실행은 하지 않았다. 최희찬이 수정본 전달과 Git·공유 Drive 반영 범위를 지정했다.
- 기여는 **고정 버전 CPU 재실행 자료 제출·확인**으로 기록한다. 2차 작업 전체 완료, 외부 독립 실험 승인 또는 최신 원고 검토 완료와 구분한다.

## 첨부 무결성과 r2 변경

원본 인계 ZIP은 23개 일반 파일이며 안전한 내부 경로와 CRC를 확인했다. 내부 목록의 22개 SHA-256이 모두 일치한다. r2는 `인계요약.txt`의 직접 확인 항목과 `파일목록_SHA256.txt`만 수정했고 나머지 21개 파일은 이전본과 바이트 단위로 같다. r2에는 새 실행 결과가 추가되지 않았다.

별도 r2 요약과 ZIP 내부 요약의 문장은 같다. 별도 파일은 UTF-8 BOM·CRLF, 내부 파일은 BOM 없는 UTF-8·LF라서 바이트와 해시는 다르다. 원본을 정규화해 덮어쓰지 않는다.

| 자료 | SHA-256 |
|---|---|
| 최초 인계 ZIP | `2b6ec3fe250af5c497aeb38747c491d20f80e44535dc63520e0bd3641db83d1d` |
| r2 인계 ZIP | `936c1cb8ad4c9a501c2b39d989047f45dbe316ac85a7238aacf11434b1a165b7` |
| r2 별도 요약 | `60cfa9211e03748b5c16f4f58c1a6a45824cc1f3a598790f1f29726053eb7f27` |
| r2 ZIP 내부 요약 | `b17272c5a964f6bfef77b2be641783f08e72dd1416351e3322848006e8ce999f` |

원본 ZIP·전체 로그·비공개 작업경로는 공유 원본 보관 영역에서 관리하며 이 공개 문서에 첨부하지 않는다. ZIP 내부 실행 로그에 배포 스크립트 해시가 기록돼 있으나 스크립트 본체는 포함되지 않아 ‘스크립트 무수정’을 여기서 원본과 독립 대조하지는 못했다.

## 실행 기록과 GitHub 대조

| 구분 | checkout / head | JUnit |
|---|---|---|
| 태희 인계 실행 | `9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf` | 541개, 실패·오류·skip 0 |
| [기존 CI 38600033132](https://github.com/heechan9/AdversarialAI_Security/actions/runs/38600033132) | 실제 checkout `b80adf5084e6ee11a836e9cadb6477dff2a93bfd`, PR head `5d138ea2a237aa4ed89bcccf700c1857b8b3cc8c` | 552개, 실패·오류·skip 0 |
| [수신 당시 main CI 39898637772](https://github.com/heechan9/AdversarialAI_Security/actions/runs/39898637772) | `8353a6d819266ace10262a442a355be3b288ec22` | 780개, 실패·오류·skip 0 |

태희 인계의 prepare/run/ci_cpu 종료코드는 모두 0이고 로그의 보호 입력 `src/configs/results` 상태에는 변경이 없다. JUnit 실제 사례명 대조에서 기존 CI에만 있는 11개는 [PR81](https://github.com/heechan9/AdversarialAI_Security/pull/81)의 JSON/CSV 파서 회귀검사다. 태희 쪽 541개는 기존 CI에 모두 존재한다. PR81은 2026-10-17 22:35 KST 병합됐으며, 인계요약의 웹 상태 재확인 필요 사항과 분리해 수신 측에서 확인했다.

태희 결과의 공개 증거 감사는 PASSED이고 검증 범위 9개·미검증 범위 2개를 명시한다. 감사 JSON의 `summary` 객체는 기존 CI 및 수신 당시 main CI와 동일하지만, `timestamp_utc`와 `source_commit_sha`가 달라 전체 JSON이 같은 것은 아니다. paper claims 9개도 통과했지만 대상은 [ACK2026 v1.5 snapshot](../../../configs/paper_claims/ack2026_v1_5.json)이며 최신 원고 전체 감사가 아니다.

기존 CI의 최종 freeze와 태희 freeze는 각각 50개 패키지다. 직접 고정한 9개 패키지와 Python 3.11.17은 같고 다음 전이 의존성 4개가 다르다.

| 패키지 | 기존 CI | 태희 인계 |
|---|---|---|
| grpcio | 1.84.0 | 1.84.1 |
| pluggy | 1.6.0 | 1.7.0 |
| certifi | 2026.7.22 | 2026.10.19 |
| python-dateutil | 2.9.0.post0 | 3.0.0 |

태희의 패키지 버전 50개는 수신 당시 main CI와 모두 일치한다. 커널과 Python 빌드 등 환경 전체가 동일하다는 뜻은 아니다. 기존 CI 아티팩트 SHA-256은 `d62b8acbdcf79afa81ce3e66249f2a33ce0d66518bdafd0c80c16d797386e3df`, main CI 아티팩트는 `2ff22622c1779c4b89f4286aafe5bb6c5ba1af78b2c6c766f424d68feb74d713`이며 GitHub metadata digest와 일치했다.

## 유지되는 한계

- 태희 실행은 옛 고정 baseline이다. 수신 당시 main은 22 commits 앞서며, 태희의 541개 통과를 최신 코드 검사로 대체하지 않는다.
- 태희 실행에는 CI의 별도 저장 checkpoint 10개 재계산 단계가 포함되지 않았다.
- 원본 이미지 781장과 로컬 모델 바이너리 해시 검사는 NOT_RUN/UNAVAILABLE이다. 저장된 메타데이터·예측의 정합성 확인과 새 추론을 구분한다.
- 기존 연구 PC LOCAL_PASS와 외부 FGSM FAIL, BIM CPU/GPU 차이와 원인 미확정은 유지한다. oneDNN 단일 원인, 독립 재현 성공 또는 전체 공격·방어 행렬 완료의 근거로 사용하지 않는다.
- [CPU 검사 경계](../../CPU_CI_REVIEW.md)와 [검증 상태 등록부](../../VERIFICATION_STATUS_REGISTRY.md)를 변경하지 않는다.

