# 저장 수치 재계산·시각자료 대조

## 작업·도움·판정 기록

* 공개 작성자: 이재혁 (GitHub 핸들 미제공)
* 실제 검토일: 2026-10-20 (KST)
* 직접 연 자료와 수행한 확인: 공개 저장소의 고정 커밋 raw 파일 S02~S09, S12~S17과 최신 팀 발표·논문(비공개, 내용만 대조). 원 CSV 781행에서 정수 분자/분모를 다시 세고, 발표 표·차트 5개 항목과 대조했다.
* 직접 고치거나 새로 쓴 부분: 1절 R01~R10의 계산값·방법·판정 칸, 2절 V1~V5 전체, 3절 확인 결과와 범위 판단.
* AI 도움: 시작 템플릿과 참고 기준값은 AI가 준비했다. 이번 원 CSV 집계, 발표·논문 수치 대조, 이 문서의 작성은 팀 승인 하에 AI 도구(Claude)로 수행했다. 작성자가 직접 다시 확인함.
* 기존 팀 산출물에서 이어받은 부분: 9b64b8e 기준 10개 계산의 참고 기준값(이전 제출 기록). 기존 기록의 날짜·커밋·수치는 바꾸지 않았다.
* 새 모델 실행/학습 여부: 수행하지 않음(이 문서 과제 범위).
* 남은 문제/필요한 자료: 3절 참조(BIM 시작점·최선 후보 유지 방식의 공개 근거 위치).
* 팀 검토자/결정: 미정. 실제 검토 후 채움.

## 상태 표기

필수 범위(기존 계산 10, 시각자료 5셀, 제한된 BIM/Square 확인) 수행 완료. 원자료와 발표·논문 표시값 사이 수치 불일치는 발견하지 않았다. 원자료와 원고는 수정하지 않았다.

## 1. 기존 10개 계산의 직접 확인

기준 커밋: 9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf. 참고 기준은 이전 제출 기록값이며, 아래 '계산값' 칸이 이번 확인 결과다. raw 데이터 파일은 복사해 올리지 않는다.

공통 확인: 6개 CSV 모두 헤더 1행 + 데이터 781행, `relative_path` 781개 모두 고유. S02/S04, S03/S05의 clean 예측은 781행 모두 동일. S06·S07의 `clean_pred`·`attacked_pred`는 S04의 clean·adversarial 예측과 781행 모두 동일.

|ID|항목|공개 원자료|참고 기준(기존값)|계산 분자/분모·값|실제 집계 방법/열|판정·차이|
|-|-|-|-|-|-|-|
|R01|CNN FGSM .03 ASR|S04|314/504 → 62.30%|314/504 = 62.301587% → 62.30%|분모: `clean_predicted_index`=`true_index` 행 수. 분자: 그중 `adversarial_predicted_index`≠`true_index`. 플래그 `clean_correct`=True 504, `attack_success`=True 314와 대조|일치|
|R02|MobileNetV2 FGSM .03 ASR|S05|510/613 → 83.20%|510/613 = 83.197390% → 83.20%|R01과 같은 조건. 플래그 613/510과 대조|일치|
|R03|CNN clean 정확도|S02|504/781 → 64.53%|504/781 = 64.532650% → 64.53%|`clean_predicted_index`=`true_index` 행 수 / 781. ε=0 행에서 adversarial 예측도 504로 동일, ASR 0/504|일치|
|R04|MobileNetV2 clean 정확도|S03|613/781 → 78.49%|613/781 = 78.489117% → 78.49%|R03과 같은 조건. ε=0 ASR 0/613|일치|
|R05|CNN FGSM .03 정확도|S04|190/781 → 24.33%|190/781 = 24.327785% → 24.33%|`adversarial_predicted_index`=`true_index` 행 수 / 781|일치|
|R06|MobileNetV2 FGSM .03 정확도|S05|103/781 → 13.19%|103/781 = 13.188220% → 13.19%|R05와 같은 조건|일치|
|R07|CNN Gaussian transfer .03 정확도|S06|271/781 → 34.70%|271/781 = 34.699104% → 34.70%|`transfer_defended_pred`=`true_index` / 781. S08 `accuracy.transfer_defended`×781=271과 대조|일치|
|R08|CNN Gaussian adaptive .03 정확도|S06|98/781 → 12.55%|98/781 = 12.548015% → 12.55%|`adaptive_defended_pred`=`true_index` / 781. S08과 대조|일치|
|R09|CNN Mean transfer .03 정확도|S07|288/781 → 36.88%|288/781 = 36.875800% → 36.88%|`transfer_defended_pred`=`true_index` / 781. S09와 대조|일치|
|R10|CNN Mean adaptive .03 정확도|S07|86/781 → 11.01%|86/781 = 11.011524% → 11.01%|`adaptive_defended_pred`=`true_index` / 781. S09와 대조|일치|

R01~02는 ASR, R03~10은 정확도이다. 방어 정확도 4행에는 filtered-clean ASR 분모를 넣지 않았다. 반올림은 정수 비율×100의 마지막 단계에서 소수 둘째 자리로 했다.

참고로 따로 계산한 filtered ASR(필수 10개에 포함하지 않음, 분모 = 필터 적용 clean 정답 집합):

|조건(CNN, ε=.03)|분모(`defended_clean_pred`=`true_index`)|transfer ASR|adaptive ASR|S08/S09 값|
|-|-:|-:|-:|-|
|Gaussian|445|175/445 = 39.33%|347/445 = 77.98%|일치|
|Mean|419|131/419 = 31.26%|333/419 = 79.47%|일치|

## 2. 실제 표·차트 5셀 대조

비공개 화면/파일명/페이지는 게시하지 않는다. 항목은 최신 팀 발표에서 서로 다른 지표·분모·범례를 갖는 것으로 골랐다.

|ID|고른 항목|실제 표시값·단위|원자료 계산값·분자/분모|모델/공격/epsilon/범례 조건|출처|일치/차이·제안|
|-|-|-|-|-|-|-|
|V1|ASR 분모 설명 막대(CNN)|"ASR 314/504 = 62.30%", 막대 끝 781|314/504 = 62.30%; 정확도 분모 781|CNN, FGSM, ε=.03. 범례: 전체 781 / clean 정답 504 / 그중 공격 후 오답 314|S04|일치. 막대 길이도 표본 수에 비례(314/781≈0.40, 504/781≈0.65)함을 눈으로 확인|
|V2|clean 대 FGSM 막대(MobileNetV2)|78.49% → 13.19%|613/781 = 78.49%, 103/781 = 13.19%|MobileNetV2, FGSM ε=.03, 정확도(분모 781). 범례 색: 정상 입력/FGSM|S03, S05|일치|
|V3|ε별 정확도 곡선 점(CNN, ε=.01)|41.61%|325/781 = 41.61%|CNN, FGSM ε=.01, 정확도. 가로축은 수치형 ε, 관측점 4개(0·.01·.03·.05)|S17(fgsm_cnn_eps_0.01_samples.csv)|일치. 같은 곡선의 MobileNetV2 .01/.03/.05 = 97/781 12.42%, 103/781 13.19%, 126/781 16.13%도 일치(비단조 그대로 표시)|
|V4|transfer/adaptive 막대(MobileNetV2·평균 필터)|전달 32.65%, 방어 인지 8.83%|255/781 = 32.65%, 69/781 = 8.83%|MobileNetV2, Mean 3×3, FGSM ε=.03, 정확도. 범례: 전달 조건/방어 인지 조건|S09|일치. 같은 차트의 CNN Gaussian 34.70/12.55, CNN Mean 36.88/11.01, MobileNetV2 Gaussian 26.63/7.17도 일치|
|V5|필터 적용 clean 정확도 막대(CNN·가우시안)|56.98%|445/781 = 56.98%|CNN, 공격 없음, Gaussian 3×3, 정확도. 범례: 필터 없음/가우시안/평균|S06(`defended_clean_pred`), S08|일치. 같은 차트의 CNN Mean 419/781 = 53.65%, MobileNetV2 648/781 = 82.97%, 622/781 = 79.64%도 일치|

추가로 논문의 ε별 표(정확도·S/D·ASR 8행), 클래스별 S/D 표(ε=.03, 10클래스×2모델), 전달·방어 인지 정확도 표(6행×4열)를 S02~S05, S17, S08/S09와 대조했고 모두 일치했다.

## 3. 제한된 추가 공격 범위 확인

* BIM CNN .03 (S12~S14): S14 행별 CSV 781행에서 직접 셈. 필터 없음 attacked 정답 81/781 = 10.37%, ASR 423/504 = 83.93%. Gaussian adaptive 정답 44/781 = 5.63%, ASR 401/445 = 90.11%. S13 설정 steps 10, step_size 0.005, restarts 1, seed 0. 발표 보충 표·논문 보충 문단 수치와 일치.
* Square original q1000 (S16): seed 2026/2027/2028 정답 388/384/387 (각 781 분모) = 49.68/49.17/49.55%, 성공 116/120/117 (각 504 분모) = 23.02/23.81/23.21%. 발표·논문의 "49.17–49.68%, 23.02–23.81% (D=504)"는 seed별 범위로 일치. seed union 374/781 = 47.89%, 130/504 = 25.79%는 seed당 1,000질의 결과가 아니며(최대 3,000질의 조합) 발표 범위에 쓰이지 않았음을 확인.
* 최신 설명과의 대조: 발표·논문은 BIM을 CNN 필터 없음과 Gaussian 방어 인지 두 조건만 제시. snapshot에 있는 CNN Mean BIM(adaptive 35/781 = 4.48%, 384/419)과 MobileNetV2 BIM 조건은 최신 발표 범위에 포함하지 않았고 이 문서도 포함하지 않는다.
* 전체 공격/모델 조합 완료 또는 독립 재현이라고 할 수 없는 이유: S12 snapshot은 13/16 조건, 감사 PARTIAL_OUTPUTS_ONLY, 보존 당시 상태 RUNNING이다(현재 실행 상태 아님). S13은 `independent_verification_approval: false`, 12개 조건이 상위 보고서에서 상속됐다고 명시한다. PGD와 MobileNetV2 전체 공격·방어 행렬은 공개 자료에 없다. 이번 작업은 저장 CSV/JSON 재계산이며 모델 재실행이 아니다.
* 확인 요청: 발표·논문의 BIM "정상 입력 시작, 최선 후보 유지"는 S12/S13 공개 필드(steps·step_size·restarts·seed)에서 직접 확인하지 못했다. 해당 동작이 기록된 코드 또는 문서 위치 링크를 요청한다.

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
