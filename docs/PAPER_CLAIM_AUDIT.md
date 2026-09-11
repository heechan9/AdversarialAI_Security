# 논문 Claim 근거감사

이 감사기는 논문에 들어갈 Clean·FGSM 주장을 고정 숫자에서 가져오지 않고 저장소의
canonical CSV·JSON·manifest에서 다시 계산한다. 기존 모델, 공격 코드, 전처리와 결과
산출물은 수정하지 않는다.

## 실행

```bash
PYTHONPATH=src python scripts/audit_paper_claims.py
```

Windows CMD에서는 먼저 다음을 실행한다.

```bat
set PYTHONPATH=src
python scripts\audit_paper_claims.py
```

모든 Claim이 통과하면 exit code 0, 누락·변조·스키마 또는 계약 불일치가 있으면
exit code 1을 반환한다.

## Claim 목록

| Claim | 검증 내용 | canonical 근거 |
|---|---|---|
| CLAIM-001 | 781장 manifest 구조·순서·SHA 형식 | `configs/test_manifest.json` |
| CLAIM-002 | 모델별 Clean correct count·accuracy | Clean 표본 CSV와 summary JSON |
| CLAIM-003 | FGSM ASR의 clean-correct 분모 | Clean·FGSM 표본 CSV |
| CLAIM-004 | ε=0 대조조건 | FGSM 표본 CSV |
| CLAIM-005 | 모든 모델·ε의 L∞ 상한 | FGSM 표본 CSV |
| CLAIM-006 | 논문용 FGSM 비교표의 수치 일치 | 표본 CSV·report JSON·comparison summary |
| CLAIM-007 | README·결과문서·provenance 일치 | 관련 문서와 `PROVENANCE.json` |
| CLAIM-008 | 엄격한 시각 검토 근거·SHA·canonical 일치 | `results/audit/evidence/*.csv`, `manifest.json` |
| CLAIM-009 | ACK 2026 논문 초안 v1.5 표시값·주장 경계 일치 | `configs/paper_claims/ack2026_v1_5.json`과 canonical 근거 |

`ack2026_v1_5.json`은 독립적인 정답 파일이 아니라 논문 초안에 실제로 표시한 값을
기계 판독 가능하게 전사한 스냅샷이다. 감사기는 Clean·FGSM·시각검토 canonical
근거를 다시 계산해 6자리 정확도, 2자리 백분율, 성공 수/분모, 분할·판정 집계와
과장 방지 경계를 대조한다.

## 상태 경계

현재 FGSM 수치는 멘토의 ε 범위 승인 전이므로 `provisional`이어야 한다. 감사기는
provisional 비교표를 임의로 `official`로 바꾸면 실패한다. 승인 후 공식 재실행을
구현할 때는 기존 provisional 경로를 덮어쓰지 않고 별도 official 산출물과 Claim을
추가한다.

공식 실행 준비 절차는 `docs/FGSM_OFFICIALIZATION_RUNBOOK.md`에 정의한다. 기본 계약은
승인 전 상태이므로 준비 점검이 실패해야 정상이며, 이 실패를 현재 감사 실패로 보지 않는다.

공공 AIS 데이터 격리 Claim은 해당 데이터 브랜치가 공식 저장소에 통합되고 canonical
요약 스키마가 확정된 뒤 별도 Claim으로 추가한다. 그전에는 데이터가 모델 학습,
Clean 또는 FGSM 성능 근거로 사용됐다고 주장하지 않는다.
