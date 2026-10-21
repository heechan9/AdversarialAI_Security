# 저장 근거 검토 방법

## 작업·도움·판정 기록

* 공개 작성자: 이재혁 (GitHub 핸들 미제공)
* 실제 검토일: 2026-10-20 (KST)
* 직접 연 자료와 수행한 확인: 공개 S01~S17 고정 커밋 raw 파일, 최신 팀 발표·논문(비공개, 내용만 대조).
* 직접 고치거나 새로 쓴 부분: 이 문서 전체(환경, 절차 1~9, 기여 기록, 검토 결과 사용).
* AI 도움: 시작 템플릿은 AI가 준비했다. 이번 집계·대조와 이 방법 문서의 작성은 팀 승인 하에 AI 도구(Claude)로 수행했다. 작성자가 직접 다시 확인함.
* 기존 팀 산출물에서 이어받은 부분: 9b64b8e 기준 10개 계산의 참고 기준값과 열 정의 안내.
* 새 모델 실행/학습 여부: 수행하지 않음(이 문서 과제 범위).
* 남은 문제/필요한 자료: '아직 확인하지 못한 것' 참조.
* 팀 검토자/결정: 미정. 실제 검토 후 채움.

## 목적과 범위

저장된 공개 CSV/JSON의 정적 재계산과 주장/시각자료의 정합성을 검토한다. 학습·추론·공격을 새로 실행하지 않는다. 결과는 독립 신경망 재현 또는 실해역 안전성 확인이 아니다. 제출 원고는 수정하지 않고 차이는 별도 제안으로 기록한다. 이 작업은 '저장 CSV 재계산/문서 정합성 검토'이다.

## 실제 사용 환경

* 도구/버전: Python 3.13.16 표준 라이브러리 `csv`·`json`(외부 패키지 없음), poppler `pdftotext`/`pdftoppm` 24.02.0(비공개 발표·논문 PDF의 텍스트 추출과 차트 화면 확인). 스프레드시트로 따라 할 때는 아래 절차의 Excel 식을 쓰면 같은 결과가 나온다.
* CSV 가져오기 문자 인코딩/구분자: UTF-8, 쉼표 구분. 헤더가 한 열에 뭉치지 않음을 확인.
* 자료 기준 커밋: 9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf
* 추가 범위 참조 커밋: 3664831b1325e8cb4139877ba7c9e0b15aec294f
* 실제 연 공개 파일과 다운로드/열기 방식: `https://raw.githubusercontent.com/heechan9/AdversarialAI_Security/<커밋>/<경로>`로 S01~S16과 S17 폴더의 `fgsm_{cnn,mobilenet}_eps_{0.01,0.05}_samples.csv`를 커밋 고정 상태로 내려받음. `main` 같은 움직이는 브랜치 이름은 쓰지 않음.
* 개인정보 없는 계산 작업 파일 처리 방식: 내려받은 CSV와 계산 결과는 로컬에만 보관. 공개 저장소에 원본 사본이나 스크립트를 추가하지 않음.

## 다른 사람이 따라 할 수 있는 실제 절차

1. 파일/커밋 고정: 링크의 `blob/<40자리 커밋>/` 부분을 확인하고 Raw로 받는다. 같은 파일이라도 커밋이 다르면 다른 근거로 취급한다. FGSM·방어 수치는 9b64b8e, BIM·Square는 3664831에서 받는다.
2. 행 수 확인: 각 CSV가 헤더 1행 + 데이터 781행(엑셀 2~782행)인지 센다. `relative_path`가 781개 모두 고유한지 확인한다(중복 제거 후 개수 = 781). 이 확인은 파일 경로 중복이 없다는 뜻이지 이미지 내용 중복 검사가 아니다.
3. 형식 처리: 인덱스 열(`true_index`, `*_pred`, `*_predicted_index`)은 정수로 읽혔는지 본다. `clean_correct`·`attack_success`는 `True`/`False` 텍스트로 저장돼 있어 그대로 더하지 않는다. 기본 집계는 예측 인덱스와 `true_index` 비교로 하고, 플래그는 `="True"` 개수를 세어 대조만 한다.
4. 집계 조건(FGSM CSV, C=`true_index`, E=`clean_predicted_index`, G=`adversarial_predicted_index`):

   * clean 정답 수 `=SUMPRODUCT(--(E2:E782=C2:C782))`
   * 공격 후 정답 수 `=SUMPRODUCT(--(G2:G782=C2:C782))`
   * ASR 성공 수 `=SUMPRODUCT(--(E2:E782=C2:C782),--(G2:G782<>C2:C782))`
   * 방어 CSV(C=`true_index`, E=`defended_clean_pred`, G=`transfer_defended_pred`, H=`adaptive_defended_pred`): 정확도 분자 `=SUMPRODUCT(--(G2:G782=C2:C782))`, `H`도 같은 방식. filtered ASR은 분모 `=SUMPRODUCT(--(E2:E782=C2:C782))`, 분자 `=SUMPRODUCT(--(E2:E782=C2:C782),--(G2:G782<>C2:C782))`.
   * 열 위치는 파일마다 다르므로 열 이름을 먼저 확인한다(예: BIM S14에는 `epsilon` 열이 없어 열 문자가 하나씩 당겨진다).
5. 분모 구분: 정확도 = 정답 수 / 781. ASR = clean 정답 중 공격 후 오답 / clean 정답 수(CNN 504, MobileNetV2 613). filtered ASR = 필터 적용 clean 정답 중 공격 후 오답 / 필터 clean 정답 수(Gaussian CNN 445·MobileNetV2 648, Mean CNN 419·MobileNetV2 622). 방어 정확도 행에 filtered ASR 분모를 쓰지 않는다.
6. 반올림: 정수 분자/분모를 먼저 기록하고, 반올림 전 비율(소수 6자리)을 남긴 뒤 마지막에만 %를 소수 둘째 자리로 표시한다. 예: 314/504×100 = 62.301587 → 62.30%. 표시된 %에서 분자를 역산하지 않는다.
7. 표·차트 비교: 항목마다 (a) 표시값과 단위, (b) 모델·공격·ε·필터, (c) 지표가 정확도인지 ASR인지와 분모, (d) 범례 색과 막대/선의 대응, (e) 축 종류(ε 축이 수치형인지)를 확인한다. 같은 숫자를 다섯 번 보지 않고, 지표·분모·범례가 다른 다섯 항목을 고른다. 막대형 분모 설명은 길이가 표본 수에 비례하는지도 본다. Square는 seed별 범위와 seed union을 구분한다.
8. 불일치·실패 처리: 원자료와 원고를 고치지 않고 위치·표시값·계산값·차이를 기록한다. 식 오류가 나면 0으로 두지 말고 필터로 직접 센다. 함수 구분자가 세미콜론인 지역 설정도 있다. 파일을 열지 못하면 '확인 불가: 이유/필요한 자료'로 남긴다. 결측값은 이번 파일들에서 발견하지 않았다.
9. 다시 확인할 공개 근거: 아래 링크 S01~S17. 계산 결과는 [재계산 문서](evidence_calculation_review.md), 주장 연결은 [주장 대조 문서](evidence_claim_review.md).

## 실제 기여와 이전 기록

* 이전 고정 기록에서 보존한 값과 범위: 9b64b8e 기준 10개 계산의 기존값(R01~R10 참고 기준). 날짜·커밋·수치를 바꾸지 않았다.
* 이번에 새로 확인한 것: R01~R10을 원 CSV에서 다시 셈(10/10 일치), 플래그 열 대조, CNN filtered ASR 4개, 발표 5개 항목(V1~V5)과 같은 차트의 나머지 값, 논문 ε별 표·클래스별 S/D 표·전달/방어 인지 표, BIM CNN .03 두 조건(S14 행별), Square seed별 3개 값과 union 구분.
* 이번에 수정 제안한 설명과 이유: (1) S01(9b64b8e)의 "BIM은 논문 범위 아님" 문장은 현재 보충 범위와 다르므로 현재 범위 설명에 재사용하지 않도록 표시, (2) 775 고유 이미지·5개 중복 그룹과 BIM 시작점·최선 후보 유지 방식의 공개 근거 위치 보완 요청.
* AI가 도운 설명/계산식/초안: 시작 템플릿, 집계 식 안내, 이번 집계·대조 수행과 세 문서 작성(팀 승인 하에 AI 도구 사용).
* 아직 확인하지 못한 것: 775 고유 이미지·5개 중복 그룹의 공개 근거, BIM 시작점·최선 후보 유지 방식의 공개 근거, 전체 학습·검증·테스트 간 중복·유사 이미지 검사(미완료로 기록됨), 모델 재실행에 의한 독립 재현(범위 밖).

## 검토 결과 사용

* 채택 제안: 발표·논문의 FGSM·방어·BIM·Square 수치는 공개 저장 자료와 일치하므로 현재 표시값 유지.
* 보류/추가 확인 요청: 위 '아직 확인하지 못한 것'의 근거 2건 위치, 평가 계약 문서에 현재 보충 범위 반영 여부.
* 팀 검토 결과/실제 PR 링크: 실제 생긴 뒤 채움

## 공개 출처

* **S01 평가 계약**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/docs/EXPERIMENT_CONTRACT.md
* **S02 CNN clean CSV**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/results/attacks/provisional/fgsm_cnn_eps_0_samples.csv
* **S03 MobileNetV2 clean CSV**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/results/attacks/provisional/fgsm_mobilenet_eps_0_samples.csv
* **S04 CNN FGSM .03 CSV**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/results/attacks/provisional/fgsm_cnn_eps_0.03_samples.csv
* **S05 MobileNetV2 FGSM .03 CSV**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/results/attacks/provisional/fgsm_mobilenet_eps_0.03_samples.csv
* **S06 Gaussian CNN .03 CSV**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/results/defenses/experimental/gaussian_run_01/cnn_eps_0.03_samples.csv
* **S07 Mean CNN .03 CSV**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/results/defenses/experimental/mean_run_01/cnn_eps_0.03_samples.csv
* **S08 Gaussian 요약**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/results/defenses/experimental/gaussian_run_01/summary.json
* **S09 Mean 요약**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/results/defenses/experimental/mean_run_01/summary.json
* **S10 연구 PC 재검증 범위**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/docs/STAGE_B_PC_FULL_20260928.md
* **S11 외부 검증 차이와 미해결 범위**: https://github.com/heechan9/AdversarialAI_Security/blob/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/docs/STAGE_B_HYEONSU_01_REVIEW.md
* **S12 BIM 보존 체크포인트 요약**: https://github.com/heechan9/AdversarialAI_Security/blob/3664831b1325e8cb4139877ba7c9e0b15aec294f/results/extensions/checkpoints/20261002-evening/bim/SUMMARY.md
* **S13 BIM 설정·조건별 분모**: https://github.com/heechan9/AdversarialAI_Security/blob/3664831b1325e8cb4139877ba7c9e0b15aec294f/results/extensions/checkpoints/20261002-evening/bim/run.json
* **S14 BIM CNN Gaussian .03 행별 자료**: https://github.com/heechan9/AdversarialAI_Security/blob/3664831b1325e8cb4139877ba7c9e0b15aec294f/results/extensions/checkpoints/20261002-evening/bim/cnn_gaussian_eps_0.03.csv
* **S15 Square 등 공개 확장 설명**: https://github.com/heechan9/AdversarialAI_Security/blob/3664831b1325e8cb4139877ba7c9e0b15aec294f/results/extensions/blackbox/README_20261003.md
* **S16 Square seed별 정수·요약**: https://github.com/heechan9/AdversarialAI_Security/blob/3664831b1325e8cb4139877ba7c9e0b15aec294f/results/extensions/blackbox/summary_20261003.json
* **S17 CNN FGSM epsilon별 공개 자료 폴더**: https://github.com/heechan9/AdversarialAI_Security/tree/9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf/results/attacks/provisional

## Codex 후속 정리·근거 보완 — 2026-10-21

이 절은 원작성자의 2026-10-20 검토 이후 Codex가 추가한 기록이다. 위 본문에서 공개 근거를 찾지 못했다고 적은 것은 당시 검토 기록으로 보존한다. 원작성자가 당시부터 아래 근거를 확인했던 것으로 소급하지 않는다.

- 고유 RGB 775개·동일 RGB 중복 5그룹: [공개 감사 JSON](https://github.com/heechan9/AdversarialAI_Security/blob/3664831b1325e8cb4139877ba7c9e0b15aec294f/results/extensions/checkpoints/20261002-mobile/available-data-audit.json)의 `splits.test`에서 파일 수 781, 고유 `pixel_sha256` 775개, `duplicate_groups.pixel_sha256` 5그룹을 재집계했다. 공개 기록의 정적 재집계이며 원 이미지에 대한 새로운 해시 검사가 아니다. [공개 설명](https://github.com/heechan9/AdversarialAI_Security/blob/3664831b1325e8cb4139877ba7c9e0b15aec294f/docs/MOBILE_FOLLOWUP_20261002.md)도 함께 참조한다.
- BIM 정상 입력 시작·최선 후보 유지: [실행 source_commit의 코드](https://github.com/heechan9/AdversarialAI_Security/blob/9f2f7836fa0fe2bf4c121b7b7c9c8fef18871edb/src/adversarial_ai/attacks/iterative.py#L21-L72)를 확인했다. L58에서 정상 입력으로 시작하고 L59의 무작위 시작은 PGD에만 적용된다. L50, L53–56, L62, L71에서 정상 입력과 각 반복 후보 중 오분류를 우선하며, 성공 여부가 같으면 손실이 큰 후보를 유지한다. [보존 run.json](https://github.com/heechan9/AdversarialAI_Security/blob/3664831b1325e8cb4139877ba7c9e0b15aec294f/results/extensions/checkpoints/20261002-evening/bim/run.json)의 `source_commit`은 위 SHA이고 `source_dirty=false`이다. 코드 확인은 모델 재실행 또는 독립 실험 승인이 아니다.
- 위 두 항목은 공개 근거 위치를 보완한 것이며, 전체 공격·방어 행렬이나 외부 재현의 미해결 상태를 바꾸지 않는다.
- Codex의 변경 범위: Markdown 표기 정리, 미확인 GitHub 핸들 표시, 이 후속 근거 절 추가. 원작성자의 수치·판정과 Claude 도움 기재를 보존했다.
- 공개 작성자 이재혁의 GitHub 핸들은 제공되지 않아 연결하지 않았다. 자료 작성 기여와 실제 Git 커밋 계정은 별개다. 이 자료 정리로 본인 계정 커밋·PR 생성·병합 완료를 주장하지 않는다.
