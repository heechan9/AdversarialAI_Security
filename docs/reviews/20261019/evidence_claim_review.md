# 주장·조건·근거 대조

## 작업·도움·판정 기록

* 공개 작성자: 이재혁 (GitHub 핸들 미제공)
* 실제 검토일: 2026-10-20 (KST)
* 직접 연 자료와 수행한 확인: 공개 S01~S17(고정 커밋 raw)과 최신 팀 발표·논문(비공개, 내용만 대조). 핵심 주장 8개마다 조건·분모·공개 근거·한계를 연결했다.
* 직접 고치거나 새로 쓴 부분: C1~C8 표 전체, '최신 범위를 설명하는 문장' 절.
* AI 도움: 시작 템플릿과 점검 출발점은 AI가 준비했다. 이번 주장-근거 대조와 이 문서의 작성은 팀 승인 하에 AI 도구(Claude)로 수행했다. 작성자가 직접 다시 확인함.
* 기존 팀 산출물에서 이어받은 부분: 9b64b8e 기준 이전 주장-근거 대조 기록(범위 참고만, 수정하지 않음).
* 새 모델 실행/학습 여부: 수행하지 않음(이 문서 과제 범위).
* 남은 문제/필요한 자료: C1의 775 고유 이미지·5개 중복 그룹, C8의 BIM 시작점·최선 후보 유지 방식은 공개 근거 위치를 찾지 못했다(아래 표 참조).
* 팀 검토자/결정: 미정. 실제 검토 후 채움.

## 상태 표기

8개 주장 대조 완료. 수치 불일치는 없었다. 공개 근거 위치가 없는 설명 2건은 '공개 근거 미확인'으로 남겼다. 원고는 수정하지 않았다.

기존 수치 기록 기준: 9b64b8e33a2a1ff2cda1d51386cfb9360b09aebf. 범위 보완 참고: 3664831b1325e8cb4139877ba7c9e0b15aec294f. 과거 기록은 수정하지 않고 이번 검토를 별도로 작성한다. 비공개 원고/발표의 파일명·페이지·원문·링크는 공개하지 않는다.

|ID|주제|후보 공개 근거|요약과 확인 결과|모델/공격/epsilon/분모 등 조건|실제 확인한 출처·위치|판정·한계|
|-|-|-|-|-|-|-|
|C1|표본·모델·입력 조건|S01|고정 테스트 781개 파일, 선박 10클래스. CNN 128×128, MobileNetV2 224×224. 입력은 1/255로 [0,1] 정규화. 최신 자료는 고유 RGB 775개·동일 RGB 중복 5개 그룹을 함께 밝힌다|지표 분모는 파일 781개 기준|S01 '현재 확정된 논문 범위'·'공통 조건'. S02~S07 각 781행, 경로 781개 고유, 클래스 10개 확인|781·10클래스·해상도·정규화는 일치. 775/5그룹은 S01~S17에서 공개 근거를 찾지 못함 → 근거 위치 요청. 해상도·학습 이력 차이로 구조 우열 비교 불가, MobileNetV2 학습 당시 전처리·seed 미확인(S01)|
|C2|FGSM 설정과 epsilon|S01, S17|정답 라벨 기울기를 쓰는 비표적 화이트박스 1-step FGSM, `x' = clip(x + ε·sign(∇ₓL), 0, 1)`|ε = 0, .01, .03, .05. 각 표본 L∞ ≤ ε+1e-6|S01 '공격 정의'. S17의 두 모델×4 ε CSV에서 `epsilon` 값과 `linf` 최댓값(.01→0.010000005, .03→0.030000001, .05→0.050000012, 0→0) 확인|일치. ε=.03은 픽셀 범위의 최대 3% 변화라는 크기 조건일 뿐 비가시성 보장이 아님. 반복 공격과 구분|
|C3|ASR 정의와 분모|S04, S05|ASR = clean 정답 중 공격 후 오답 비율. clean 오답은 제외|ε=.03: CNN 314/504 = 62.30%, MobileNetV2 510/613 = 83.20%|S04/S05 예측 인덱스 비교로 직접 셈, `clean_correct`/`attack_success` 플래그와 대조. S01 지표 표|일치. 정확도(분모 781)와 ASR(분모 504/613)을 섞지 않음|
|C4|clean·FGSM .03 정확도|S02~S05|CNN 64.53 → 24.33%, MobileNetV2 78.49 → 13.19%|정확도, 분모 781. CNN 504→190, MobileNetV2 613→103|S02~S05 직접 셈|일치. clean 정확도가 높은 모델도 FGSM에 취약했다는 관찰이며, 해상도·학습 이력이 달라 구조의 인과적 우열로 일반화하지 않음|
|C5|transfer·adaptive 차이|S06~S09|전달 조건 = 원 분류기로 만든 FGSM 입력에 필터를 나중에 적용. 방어 인지 조건 = 필터+분류기 전체 경로의 기울기로 공격 생성. 모델 간 전이 공격이 아님|CNN ε=.03 정확도: Gaussian 271/781 = 34.70% / 98/781 = 12.55%, Mean 288/781 = 36.88% / 86/781 = 11.01%|S01 '방어 조건과 해석'. S06/S07 `transfer_defended_pred`·`adaptive_defended_pred` 직접 셈, S08/S09와 대조. S06·S07 `attacked_pred`가 S04 adversarial 예측과 781행 모두 같아, 전달 조건이 같은 FGSM 입력을 쓴 것 확인|일치. 고정 3×3 필터 두 종류·이번 FGSM 조건에 한정. 필터 회복은 방어 인지 공격에서 유지되지 않으므로 방어 성공으로 일반화하지 않음|
|C6|clean 필터 영향과 집합|S08, S09|필터는 공격 없는 입력의 정확도도 바꿨다. CNN 하락, MobileNetV2 상승|필터 clean 정답: Gaussian CNN 445 / MobileNetV2 648, Mean CNN 419 / MobileNetV2 622 (각 분모 781). 필터 경로 ASR 분모는 이 집합|S08/S09 `accuracy.defended_clean`, `asr_*_defended.denominator`. S06/S07 `defended_clean_pred`로 CNN 445/419 직접 셈|일치. 정확도 분모 781과 filtered ASR 분모(445/648/419/622)를 구분|
|C7|재현성과 외부 미해결|S10, S11|연구 수행 PC 2026-09-28 전체 조건 재실행에서 기준 라벨·요약 지표 재현. 별도 환경에서는 MobileNetV2 공격 관련 예측 16개(서로 다른 이미지 14장)가 달랐고 원인 미확정|16 CSV×781행. 확률 벡터는 비교 대상 아님|S10 '판정과 확인 범위'(LOCAL_PASS, `independent_operator=false`). S11 '판정'(FAIL, Gaussian 10 + Mean 6, 중복 제거 14장)|일치. 연구 PC 재현은 로컬 재현이지 독립 재현이 아님. oneDNN 등 단일 원인 미확정. 외부 불일치를 해결된 것으로 쓰지 않음|
|C8|현재 제한된 BIM/Square 범위|S12~S16|최신 발표·논문은 같은 CNN·781 파일·L∞≤0.03의 제한된 BIM·Square 결과를 보충으로 포함|BIM(steps 10, step 0.005, restart 1): 필터 없음 81/781 = 10.37%, ASR 423/504 = 83.93%; Gaussian 방어 인지 44/781 = 5.63%, ASR 401/445 = 90.11%. Square(필터 없음, 최대 1,000질의, seed 2026·2027·2028): 정확도 49.17–49.68%, ASR 23.02–23.81% (D=504)|S14 행별 CSV 직접 셈, S13 `settings`·`conditions`, S12 표·상태, S15 표, S16 `square.original_q1000.runs`|수치 일치. S12는 13/16 조건 PARTIAL·보존 당시 RUNNING이므로 전체 완료 아님. Square는 seed별 범위이며 seed union(374/781, 130/504)과 다름. BIM "정상 입력 시작·최선 후보 유지"는 공개 S12/S13 필드에서 확인 못 함 → 근거 위치 요청. PGD·MobileNetV2 전체 행렬·외부 검증 미해결은 그대로 남음|

## 최신 범위를 설명하는 문장

* 과거 설명과 달라진 부분: 9b64b8e 시점 평가 계약(S01)은 "BIM·PGD·JSMA는 현재 완료된 논문 실험 범위가 아니다"라고 적는다. 최신 발표·논문은 CNN의 제한된 BIM·Square 결과를 보충으로 포함하므로, 과거의 'BIM은 논문 밖' 설명을 현재 범위의 결론으로 쓰면 안 된다. S01은 고정 커밋 기록이라 그대로 두고, 현재 범위는 3664831 기준 S12~S16으로 설명한다.
* 지금 말할 수 있는 제한된 조건: 같은 CNN·781개 파일·L∞≤0.03에서 BIM 한 설정(필터 없음, Gaussian 방어 인지)과 Square 한 설정(필터 없음, 최대 1,000질의, 3 seed)의 저장 결과가 위 수치로 기록돼 있고 행별·요약 자료와 일치한다. 이 설정에서 Square의 ASR(23.02–23.81%)은 FGSM ε=.03(62.30%)보다 낮았다.
* 여전히 말할 수 없는 것: PGD 등 반복형 방어 인지 공격의 전체 조건, MobileNetV2의 BIM·Square, 전체 공격·방어 행렬 완료, 최악 조건의 강건성, 독립 모델 재현, 외부 환경 불일치의 원인, 실제 운항 안전성.
* 공개 자료와 팀 내부 최신 자료 사이에서 추가 확인이 필요한 점: (1) 775 고유 이미지·5개 중복 그룹의 공개 근거 위치, (2) BIM 시작점·최선 후보 유지 방식의 코드/문서 위치, (3) 평가 계약 문서(S01 계열)에 현재 보충 범위를 반영할지 여부(원고 수정이 아니라 저장소 문서 정합성 제안).

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
