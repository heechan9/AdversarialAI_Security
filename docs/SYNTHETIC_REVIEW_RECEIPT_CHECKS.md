# PaulGuard | Autoware식 오프라인 검토 기록 점검 5개

검토 기준: [PaulGuard main 44ae3d9](https://github.com/heechan9/AdversarialAI_Security/tree/44ae3d9f3f83bb422c56ce12bd72e7e9d6f39a1a). 기존 [수신 보고서 검증](https://github.com/heechan9/AdversarialAI_Security/blob/44ae3d9f3f83bb422c56ce12bd72e7e9d6f39a1a/web/maris/lib/fgsm-audit.ts)에는 이미 스냅샷 스키마, SHA, 범위 검사가 있다. 기존 경로에 아래 결함이 재현됐다는 뜻이 아니다. 별도의 가상 검토 기록을 대상으로, 다시 시작한 배치와 중복 수신을 구분할 필요가 있을 때 적용할 수 있는 독립 후보 5개다. 이전 증거원 단절 실습이나 MARIS 판정 설명 카드를 재구현하지 않는다.

1. **스키마와 값 검증.** 버전, 필드, ID, 순서 번호, 완료 여부를 엄격히 확인한다. 문자로 된 `"false"`나 숫자 대신 들어온 불리언은 거절한다.
2. **세션·개정 번호 일치.** 정상 형식이더라도 현재 세션·개정 번호가 아니면 과거 기록으로 남긴다. 출처 선택은 검토자가 고정한 세션·개정 번호를 따른다.
3. **재전송 중복과 충돌 분리.** 같은 기록의 재전송은 한 번만 세고, 같은 ID의 내용이 서로 다르면 해당 ID의 모든 수신본을 제외한다. 단독 엄격 중복 함수는 충돌 시 중단한다.
4. **보류에서 복귀.** 완료된 검토 가능 체크포인트가 두 번 연속 확인돼야 복귀한다. 번호 누락·미완료는 연속 확인을 끊는다. 두 번은 가상 실습값이고 운영 임계값이 아니다.
5. **분모와 이유 보존.** 정상 수신·잘못된 형식·과거 개정·반복·충돌을 같은 원본 줄 번호로 남긴다. 원본 7행 모두 이유가 있고, 현재 검토 후보 2행·충돌 3행·과거 1행·형식 오류 1행이다. 개별 테스트에서 같은 기록의 반복을 한 건만 세는 것도 검증했다.

공식 출처: [Autoware 진단 그래프 병합기](https://autowarefoundation.github.io/autoware_universe/pr-13577/system/autoware_diagnostic_graph_merger/)의 상태와 구조 ID 대조, [Autoware 토픽 상태 모니터](https://autowarefoundation.github.io/autoware_universe/pr-10075/system/autoware_topic_state_monitor/)의 도착 여부·갱신 저하·시간 초과 상태 구분, [Autoware 오류 모니터](https://autowarefoundation.github.io/autoware_universe/refs-tags-v1.0/system/system_error_monitor/)의 복귀 개념. 직접 옮긴 코드는 없고, 각 규칙은 위 원칙을 검토 기록에 맞게 바꾼 독립 설계다. wj 개인의 작업이라고 주장하지 않는다.

현재는 로컬 합성 검증이다. 네트워크, 모델, 공격, 실제 항해·운영 경보와 연결하지 않는다. `reviewable`은 합성 검토 가능 상태이고 실제 모델 검증 통과나 운영 승인이 아니다. 합성 복귀 경로는 수신 분모 집계와 별도의 고정 시퀀스다. 아직 두 API를 실서비스 흐름으로 결합하거나 실데이터에 적용하지 않았다.

## 재현

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_review_receipt_checks.py -v
PYTHONDONTWRITEBYTECODE=1 python -m verification.review_receipt_checks
```

이 테스트들은 합성 자료와 표준 라이브러리만 사용한다. 저장소의 기존 실행기, 모델, 웹, CI 설정은 바꾸지 않는다.
