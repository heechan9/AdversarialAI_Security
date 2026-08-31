# FGSM Provisional Results

> **상태: Provisional / Preliminary**
>
> 아래 수치는 멘토의 최종 ε 범위 승인 전 예비 실험 결과다. 공식 결과로 인용하거나 유리한 ε만 선택하지 않으며, 승인 후 `results/attacks/`에 다시 실행해 확정한다.

## 실행·검증 조건

- 환경: Python 3.11.15, TensorFlow 2.21.0, Conda `adversarial_ai`
- 데이터: `configs/test_manifest.json`과 일치하는 10클래스 테스트 이미지 781장
- 모델: CNN·MobileNetV2 SHA-256이 manifest 기록값과 일치
- 공격: Untargeted FGSM, true-label categorical cross-entropy, 정확히 1-step
- 입력 범위: `[0,1]`, `L∞` 제한, `[0,1]` clipping
- ε 후보: `0, 0.01, 0.03, 0.05`
- ASR 분모: clean-correct 표본만 사용(CNN 504장, MobileNetV2 613장)
- 전체 테스트: Linux 34 passed; Windows 일반 사용자 환경 32 passed, 2 skipped (symlink 생성 권한 제한에 따른 정상 skip)

## 전체 결과

| ε | CNN Robust Acc. | CNN ASR | CNN 성공/분모 | MobileNet Robust Acc. | MobileNet ASR | MobileNet 성공/분모 |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 0.645327 | 0.000000 | 0/504 | 0.784891 | 0.000000 | 0/613 |
| 0.01 | 0.416133 | 0.355159 | 179/504 | 0.124200 | 0.841762 | 516/613 |
| 0.03 | 0.243278 | 0.623016 | 314/504 | 0.131882 | 0.831974 | 510/613 |
| 0.05 | 0.202305 | 0.688492 | 347/504 | 0.161332 | 0.794454 | 487/613 |

원자료에서 전사한 모델별 상세값은 `results/attacks/provisional/fgsm_comparison_summary.csv`에 기록한다. 이 요약은 로컬에서 생성된 raw CSV·JSON·confusion matrix를 대체하지 않는다.

## ε=0 검증

- 두 모델 모두 clean accuracy를 완전히 재현했다.
- `accuracy_drop=0`, `ASR=0`, `linf_max=0`을 확인했다.
- 전체 ε에서 `linf_max ≤ ε + 1e-6`을 확인했다.
- NaN/Inf와 실행 오류가 없었고 모델별 결과 파일은 분리 저장됐다.

## 예비 관찰

1. MobileNetV2는 clean accuracy가 CNN보다 높았지만 FGSM ε=0.01에서 robust accuracy가 0.124200까지 하락했다. 이번 비교에서는 높은 clean accuracy가 공격 강건성을 보장하지 않았다.
2. ε=0.03에서 DDG와 Sailboat는 두 모델 모두 precision·recall·F1이 0이었다. `0/0/0`은 표본 수가 아니라 세 지표가 모두 0이라는 뜻이다.
3. DDG와 Sailboat는 clean 단계에서 precision은 높았지만 recall은 상대적으로 낮았다. 기존 recall 한계가 공격에서 precision·recall·F1의 완전 붕괴로 증폭된 양상이다.
4. MobileNetV2 ASR은 ε=0.01 이후 감소하는 비단조 패턴을 보였다. FGSM overshoot 가능성은 가설일 뿐이며 추가 ε 또는 BIM·PGD 결과 없이 원인으로 확정하지 않는다.

## DDG·Sailboat class-level comparison (ε=0.03)

| Model | Class | Condition | Precision | Recall | F1 |
|---|---|---|---:|---:|---:|
| CNN | DDG | Clean | 0.9268 | 0.3725 | 0.5315 |
| CNN | DDG | FGSM ε=0.03 | 0.0000 | 0.0000 | 0.0000 |
| MobileNetV2 | DDG | Clean | 0.9808 | 0.5000 | 0.6623 |
| MobileNetV2 | DDG | FGSM ε=0.03 | 0.0000 | 0.0000 | 0.0000 |
| CNN | Sailboat | Clean | 0.9000 | 0.1216 | 0.2143 |
| CNN | Sailboat | FGSM ε=0.03 | 0.0000 | 0.0000 | 0.0000 |
| MobileNetV2 | Sailboat | Clean | 0.9583 | 0.3108 | 0.4694 |
| MobileNetV2 | Sailboat | FGSM ε=0.03 | 0.0000 | 0.0000 | 0.0000 |

## Artifact inventory verification

- 로컬 실행에서는 CNN·MobileNetV2의 ε=0.01/0.03/0.05 success·failure 샘플이 생성됐지만, 저장소에는 검토용 최소 증거로 ε=0.03의 모델별 success·failure 대표 이미지 4개만 추적한다.
- ε=0은 공격 성공·실패 시각화 대상에서 제외됐다.
- 파일명은 `{model}_eps_{epsilon}_{success|failure}_{index}.png` 규칙을 따른다.
- 저장소 추적본 4개의 파일 존재와 명명 규칙만 확인했으며 이미지 내용에 대한 시각적 검토는 아직 완료되지 않았다.
- CNN metadata: 실행시각 `2026-08-07T17:22:06Z`, input size `[128,128,3]`, 모델 SHA-256은 manifest와 일치한다.
- MobileNetV2 metadata: 실행시각 `2026-08-08T12:43:23Z`, input size `[224,224,3]`, 모델 SHA-256은 manifest와 일치한다.
- 두 metadata 모두 `untargeted FGSM, exactly one step`, `clean-correct samples only`, `from_logits=false`를 기록한다.
- CNN·MobileNetV2 산출물은 모델별 파일명으로 분리됐으며 덮어쓰기가 없다.

## 해석 제한

- 두 모델의 입력 해상도는 CNN 128×128, MobileNetV2 224×224로 다르다.
- 본 결과만으로 “정확도가 높은 모델일수록 더 취약하다”는 일반적 인과관계를 주장하지 않는다.
- 클래스별 비교는 raw report와 대표 성공·실패 이미지를 함께 검토한 뒤 확정한다.

## 공식화 전 남은 작업

1. ε=0.03의 모델별 성공·실패 대표 이미지 시각 검토
2. 로컬 raw CSV·JSON·confusion matrix·metadata 중 버전 관리 대상 선별
3. 멘토 ε 범위 승인 후 공식 결과 경로에 재실행
4. 필요 시 별도 사전등록 후 보조 ε 실험 수행

공식 재실행 전에는 `results/attacks/` 루트에 수치 산출물을 두지 않고, 예비 결과는 `results/attacks/provisional/`에만 유지한다.
