# 현수 B단계 재실행 검토 — 2026-09-27

## 판정

2026-09-25 현수의 별도 Windows 환경에서 실제 원본 재실행 산출물이 생성됐다.
수신 파일 `stage-b-hyeonsu-01-results-2.zip`을 직접 읽고 기준 커밋
`491b973cd9f4840664044a83c0d62d1ee1bb98e8`의 CSV 16개와 대조했다.
**재실행 수행 확인, 완전 일치 검증 미통과(FAIL)**다. 원본 결과와 논문 표는 유지한다.

- 주 실행은 가우시안 평가를 끝낸 뒤 첫 라벨 불일치에서 비교가 중단됐다.
- 평균 필터는 별도 `mean-diag` 실행으로 8조건이 완료됐다. 주 실행의 PASS가 아니다.
- 양쪽 총 16조건 × 781행 = 12,496행. 경로·순서·정답 인덱스 일치.
- CNN의 모든 예측과 두 모델의 Clean/필터 Clean 예측은 기준과 일치한다.
- MobileNetV2 공격 관련 예측에서 Gaussian 10개, Mean 6개 차이.
  두 방법을 합쳐 중복 제거한 이미지 수는 14장이다.
- MobileNetV2 ε=.03: 기존 정답 103/781 → 재실행 102/781,
  ASR 510/613 → 511/613. 정확도 13.19% → 13.06%.
- 주 보고서의 artifact SHA256, 두 평가 결과의 SHA256 목록 및 ZIP CRC 확인 통과.
- 16조건의 전체·클래스별 summary를 표본 CSV에서 표준 라이브러리로 재계산해 모두 일치 확인.
- 모든 표본의 L∞가 ε+1e-6 이내다. 확률·원본 공격 픽셀·기울기는 묶음에 없어 비교하지 못했다.

[가우시안 전체 차이](../results/verification/stage_b/hyeonsu_01_review/gaussian_differences.json)
/ [평균 전체 차이](../results/verification/stage_b/hyeonsu_01_review/mean_differences.json)

수신 계약에 `approved_by`와 시각이 기재되어 있지만, 이는 제출 파일의 기록이다.
이번 감사가 별도 승인 사실을 증명하거나 공식 FGSM 실행계약을 승인한 것은 아니다.
독립성은 별도 실행자·환경이며 기존 평가 알고리즘을 재사용했다.

## 원인 확인 범위

현수 환경은 Python 3.11.9, TF 2.21.0, Keras 3.15.1, Windows CPU다.
기존 평가 기록은 Python 3.11.15, TF 2.21.0, Keras 3.15.1이다.
로그에서 oneDNN 활성화를 확인했다. **oneDNN이 원인이라는 인과관계는 아직 미검증**이다.

두 실행의 contract에 기록된 평가·공격·필터 소스 해시는 기준 checkout과 일치한다.
옛 contract의 소스·manifest·클래스 목록·Clean CSV 해시는 기준 파일을 CRLF로
직렬화한 해시와 일치한다. 현수 것은 LF 해시와 일치한다.
따라서 확인한 텍스트 파일의 해시 차이는 줄바꿈으로 설명되며 알고리즘 변경 근거가 아니다.
모델 두 개의 바이너리 해시는 기존 기록과 같다. 실제 이미지 바이너리는 이번 결과 ZIP에
없으며, 재실행 평가기의 manifest 검사와 앞선 전달 전 781장 검사 기록이 근거다.

## 다음 진단: 동일 코드·환경에서 oneDNN만 변경

`verification/stage_b_onednn_diagnostic.py`는 원본 기준 커밋의 기존 평가기를
새 프로세스로 호출하여 oneDNN=1/0 각각 두 필터를 실행한다.
코드·모델·배치 크기·ε·비교 허용오차를 변경하지 않는다. 출력은 새 외부 폴더다.
첫 비교 불일치로 Mean이 생략되는 것을 피하기 위해 이 진단에서는 두 평가기를 각각
실행하고 이후 `stage_b_differences.py`로 비교한다. 최종 B단계 승인 도구가 아니다.

원본 자산이 배치된 현수의 기존 `C:\Project\AdversarialAI_Security`를 사용한다.
그 checkout은 기준 SHA여야 하고 추적 파일 변경이 없어야 한다.
새 진단 코드만 별도 폴더로 받는다(Windows Anaconda Prompt/CMD):

```bat
git clone --branch codex/stage-b-hyeonsu-diagnostics https://github.com/heechan9/AdversarialAI_Security.git C:\Project\stage-b-diagnostic-tools
C:\Project\stage-b-venv\Scripts\python.exe C:\Project\stage-b-diagnostic-tools\verification\stage_b_onednn_diagnostic.py --repo-root C:\Project\AdversarialAI_Security --output C:\Project\stage-b-hyeonsu-onednn-01
```

기존 출력 폴더가 있으면 새 이름을 사용한다. 덮어쓰기하지 않는다.
완료 시 `stage-b-hyeonsu-onednn-01` 폴더 전체를 반환한다. 총 4회 전체 평가이며
원본 `.h5` 두 개와 781장 이미지가 필요하다. 이번 감사 환경에서는 이 진단 추론을 실행하지 않았다.

읽기 전용 비교 예시(각 on/off·필터 조합에 반복):

```bat
C:\Project\stage-b-venv\Scripts\python.exe C:\Project\stage-b-diagnostic-tools\verification\stage_b_differences.py --reference C:\Project\AdversarialAI_Security\results\defenses\experimental\gaussian_run_01 --actual C:\Project\stage-b-hyeonsu-onednn-01\onednn-0-gaussian
```

종료 코드 1은 예측 차이 발견이며 전체 차이를 JSON으로 출력한다. MATCH도 라벨 진단
일치만 뜻한다. 공식 B단계 PASS에는 기존 요약·무결성·계약 검사를 모두 충족해야 한다.
oneDNN off가 더 가깝게 나와도 단일 관측만으로 원인을 확정하지 않고 반복 실행과 원래
환경 비교로 확인한다. 실패 결과를 지우거나 결과에 맞춰 허용오차를 넓히지 않는다.
