# Stage B 재실행 보고서 — `hyeonsu-01`

원본 모델 2개와 테스트 이미지 781장으로 기존 Clean·FGSM·필터 방어 결과를 별도 환경에서
다시 실행해 커밋된 결과와 대조한 기록이다. 실행 절차는
[STAGE_B_EXECUTION_CONTRACT.md](STAGE_B_EXECUTION_CONTRACT.md)를 따랐다.

> **판정: FAIL.** 합의한 기준(표본별 라벨 100% 일치)을 MobileNetV2의 FGSM 이후 조건에서
> 충족하지 못했다. Clean은 두 모델 모두 781장 전부 일치했고, CNN은 모든 조건이 일치했다.
> 기준을 사후에 완화하지 않았고 기존 결과·코드·계약은 수정하지 않았다.

이 보고서는 기존 평가기를 **다른 실행자·환경에서 재사용한 재실행**이다. 알고리즘을 따로
구현한 독립 검증이 아니다(`rerun-report.json`의 `independence` 필드와 동일).

## 1. 기준

| 항목 | 값 |
| --- | --- |
| 기준 커밋 | `491b973cd9f4840664044a83c0d62d1ee1bb98e8` (`main`) |
| 외부 계약 | `hyeonsu-stage-b.json`, SHA-256 `f7b850eaf38e223ffab338876d987e5aea6715e8228b3ba8da7587b9b8448b1d` |
| 비교 기준 | 라벨 100% 일치, 요약 지표 절대차 ≤ 1e-6, L∞ ≤ ε + 1e-6, 확률 비교 미수행 |
| 기준 확정 | 최희찬, 이현수 — `2026-09-25T02:25:29+09:00` |
| 비교 대상 | `results/defenses/experimental/{gaussian,mean}_run_01/` |

### 입력 자산 확인

| 자산 | 결과 |
| --- | --- |
| `models/cnn_baseline.h5` | SHA-256 `cb256b1a…7068701` — 계약값과 일치 |
| `models/mobilenet_finetuned.h5` | SHA-256 `58c4878f…67129ae` — 계약값과 일치 |
| `data/test` | 781장 전부 `configs/test_manifest.json` 해시와 일치, 누락·추가 0 |

전달받은 `test_manifest.json` 사본은 줄바꿈만 CRLF였고, CRLF를 제거하면 커밋된 파일과
같은 해시(`36059fea…`)다. 판정에는 저장소의 커밋된 manifest를 사용했다.

## 2. 실행 환경

| 항목 | 값 |
| --- | --- |
| OS | Windows 11 Pro 10.0.26200 (`platform`: `Windows-10-10.0.26200-SP0`) |
| CPU | AMD Ryzen 9 9950X3D 16-Core — GPU 미사용 (네이티브 Windows TF ≥ 2.11은 GPU 미지원) |
| Python | 3.11.9 (`python -m venv`로 만든 별도 환경) |
| 패키지 | tensorflow 2.21.0, keras 3.15.1, numpy 2.4.6, pillow 12.3.0, scipy 1.17.1 |
| oneDNN | 기본값(켜짐). `TF_ENABLE_ONEDNN_OPTS`를 설정하지 않았다 |
| git | 이 checkout은 `core.autocrlf=false` (아래 4.1 참고) |

전체 패키지 목록은 결과 묶음의 `environment.txt`에 있다.

## 3. 실행 명령

```bash
# 준비
python verification/stage_b_run.py --prepare --contract ../hyeonsu-stage-b.json --run-id hyeonsu-01
python verification/stage_b_readiness.py --contract ../hyeonsu-stage-b.json   # ready: true
python -m verification.stage_b_preflight --contract ../hyeonsu-stage-b.json   # PASS, 추론 없음

# 공식 실행 (2026-09-24T18:17:57Z ~ 18:24:54Z)
python verification/stage_b_run.py --contract ../hyeonsu-stage-b.json

# 보조 진단: 평균 필터 평가기 단독 실행 (4.2 참고)
PYTHONPATH=src python -m adversarial_ai.evaluation.mean_defense_evaluation \
  --output C:\Project\stage-b-hyeonsu-01-mean-diag   # 완료 2026-09-24T18:35:46Z

# 결과 묶음 무결성
python -m verification.stage_b_bundle --bundle C:\Project\stage-b-hyeonsu-01 \
  --expected-report-sha256 314d30e089ee3179137772e0dbc84e8570884b5a14b64e38c6db2397fadb94a5
```

## 4. 결과

### 4.1 공식 실행 (`stage_b_run.py`)

- 가우시안 평가기는 8개 모델·ε 조합을 끝까지 실행했다(`EXPERIMENT COMPLETE`).
- 비교기가 첫 불일치 `gaussian/mobilenet_eps_0.01_samples.csv/25/adaptive_defended_pred`에서
  `ValueError`로 중단해 `rerun-report.json`에 `status: FAIL`로 기록됐다.
- 이 중단 때문에 **평균 필터 평가기는 공식 실행 안에서 실행되지 않았다.**
- 결과 묶음 무결성 검사: `integrity_status: PASS`, `recorded_execution_status: FAIL`,
  16개 파일 추가·삭제·변경 없음. 보고서 기준 해시는 실행 직후 실행자가 계산한 값이라
  독립적인 기준은 아니다.

### 4.2 평균 필터 (보조 진단)

공식 실행이 가우시안에서 멈췄기 때문에 평균 필터 평가기를 같은 venv·같은 `PYTHONPATH`로
단독 실행했다. `stage_b_run.py`의 비교·보고서 생성을 거치지 않았으므로 **공식 판정이 아닌
보조 진단**이다.

### 4.3 조건별 불일치 표본 수

커밋된 표본 CSV와 재실행 CSV를 표본 단위로 전부 비교했다(각 칸의 분모는 781).
`relative_path`·`true_index`는 모든 파일에서 행 순서까지 일치했다.

전달 조건 = 기존 공격 이미지에 필터만 적용, 방어 인지 조건 = 필터까지 미분해 공격.

| 필터 | 모델 · ε | Clean | 필터 Clean | 공격 | 전달 조건 | 방어 인지 조건 |
| --- | --- | --- | --- | --- | --- | --- |
| 가우시안 | CNN · 0 / 0.01 / 0.03 / 0.05 | 0 | 0 | 0 | 0 | 0 |
| 가우시안 | MobileNet · 0 | 0 | 0 | 0 | 0 | 0 |
| 가우시안 | MobileNet · 0.01 | 0 | 0 | 0 | 1 | 1 |
| 가우시안 | MobileNet · 0.03 | 0 | 0 | 1 | 1 | 1 |
| 가우시안 | MobileNet · 0.05 | 0 | 0 | 1 | 3 | 1 |
| 평균 | CNN · 0 / 0.01 / 0.03 / 0.05 | 0 | 0 | 0 | 0 | 0 |
| 평균 | MobileNet · 0 / 0.01 | 0 | 0 | 0 | 0 | 0 |
| 평균 | MobileNet · 0.03 | 0 | 0 | 1 | 0 | 2 |
| 평균 | MobileNet · 0.05 | 0 | 0 | 1 | 1 | 1 |

모든 표본의 `original_linf`·`adaptive_linf`는 `≤ ε + 1e-6`을 만족했다.

### 4.4 불일치 표본 목록

클래스 이름은 `true_index`/예측 인덱스를 클래스 맵으로 변환한 것이다.

| 필터 | ε | 이미지 | 조건 | 기존 → 재실행 |
| --- | --- | --- | --- | --- |
| 가우시안 | 0.01 | `Aircraft Carrier/Aircraft Carrier_19.jpeg` | 방어 인지 | Sailboat → DDG |
| 가우시안 | 0.01 | `Bulkers/Bulkers_1011.jpeg` | 전달 | Bulkers → Recreational |
| 가우시안 | 0.03 | `Bulkers/Bulkers_1039.jpeg` | 공격 | Bulkers → Recreational |
| 가우시안 | 0.03 | `Car Carrier/Car Carrier_15.jpeg` | 전달 | Car Carrier → Recreational |
| 가우시안 | 0.03 | `DDG/DDG_1056.jpeg` | 방어 인지 | Sailboat → Recreational |
| 가우시안 | 0.05 | `Bulkers/Bulkers_6.jpeg` | 공격 | Bulkers → Submarine |
| 가우시안 | 0.05 | `Car Carrier/Car Carrier_76.jpeg` | 전달 | Tug → Bulkers |
| 가우시안 | 0.05 | `Container Ship/Container Ship_1013.jpeg` | 전달 | Sailboat → Bulkers |
| 가우시안 | 0.05 | `Sailboat/Sailboat_1007.jpeg` | 방어 인지 | Aircraft Carrier → DDG |
| 가우시안 | 0.05 | `Submarine/Submarine_1005.jpeg` | 전달 | Recreational → Sailboat |
| 평균 | 0.03 | `Bulkers/Bulkers_1039.jpeg` | 공격 | Bulkers → Recreational |
| 평균 | 0.03 | `DDG/DDG_18.jpeg` | 방어 인지 | Tug → Recreational |
| 평균 | 0.03 | `Submarine/Submarine_13.jpeg` | 방어 인지 | Sailboat → Submarine |
| 평균 | 0.05 | `Bulkers/Bulkers_6.jpeg` | 공격 | Bulkers → Submarine |
| 평균 | 0.05 | `Car Carrier/Car Carrier_82.jpeg` | 방어 인지 | Container Ship → Sailboat |
| 평균 | 0.05 | `Recreational/Recreational_1048.jpeg` | 전달 | Bulkers → Recreational |

### 4.5 요약 지표 차이 (전체 기준, 절대차 > 1e-6인 항목)

클래스별 지표 차이는 같은 표본에서 비롯되므로 생략한다.

**가우시안**

| 모델 · ε | 지표 | 기존 | 재실행 | 차이 |
| --- | --- | --- | --- | --- |
| MobileNet · 0.01 | accuracy.transfer_defended | 0.4366 | 0.4353 | -0.0013 |
| MobileNet · 0.01 | asr_transfer_defended | 307/648 (0.4738) | 308/648 (0.4753) | +0.0015 |
| MobileNet · 0.03 | accuracy.attacked | 0.1319 | 0.1306 | -0.0013 |
| MobileNet · 0.03 | accuracy.transfer_defended | 0.2663 | 0.2650 | -0.0013 |
| MobileNet · 0.03 | asr_original | 510/613 (0.8320) | 511/613 (0.8336) | +0.0016 |
| MobileNet · 0.03 | asr_transfer_defended | 440/648 (0.6790) | 441/648 (0.6806) | +0.0015 |
| MobileNet · 0.05 | accuracy.attacked | 0.1613 | 0.1601 | -0.0013 |
| MobileNet · 0.05 | asr_original | 487/613 (0.7945) | 488/613 (0.7961) | +0.0016 |

**평균 (보조 진단)**

| 모델 · ε | 지표 | 기존 | 재실행 | 차이 |
| --- | --- | --- | --- | --- |
| MobileNet · 0.03 | accuracy.attacked | 0.1319 | 0.1306 | -0.0013 |
| MobileNet · 0.03 | accuracy.adaptive_defended | 0.0883 | 0.0896 | +0.0013 |
| MobileNet · 0.03 | asr_original | 510/613 (0.8320) | 511/613 (0.8336) | +0.0016 |
| MobileNet · 0.03 | asr_adaptive_defended | 553/622 (0.8891) | 552/622 (0.8875) | -0.0016 |
| MobileNet · 0.05 | accuracy.attacked | 0.1613 | 0.1601 | -0.0013 |
| MobileNet · 0.05 | accuracy.transfer_defended | 0.3022 | 0.3035 | +0.0013 |
| MobileNet · 0.05 | asr_original | 487/613 (0.7945) | 488/613 (0.7961) | +0.0016 |
| MobileNet · 0.05 | asr_transfer_defended | 387/622 (0.6222) | 386/622 (0.6206) | -0.0016 |

ASR 분모는 기존과 재실행이 모두 같다. 정상 정답 표본(Clean·필터 Clean)이 완전히 일치하기 때문이다.

## 5. 해석과 한계

- **확인된 것:** 원본 모델·이미지로 Clean 예측이 781장 전부 재현된다. 필터 Clean과 ε=0
  조건도 재현된다. CNN은 FGSM·전달·방어 인지 조건까지 전부 재현된다.
- **재현되지 않은 것:** MobileNetV2의 FGSM 이후 조건에서 조건당 0~3장(781장 중)의 예측이
  달라졌다. 요약 지표 차이는 표본 1장에 해당하는 약 0.0013~0.0016이다.
- **재실행 환경 안에서는 결정적이다:** 두 평가기의 "공격" 열은 같은 FGSM 이미지를 쓰는데,
  두 쪽에서 뒤집힌 표본이 같다(`Bulkers_1039` @0.03, `Bulkers_6` @0.05).
- **원인 (추정, 미확인):** Clean은 일치하고 기울기를 쓰는 조건에서만, 더 깊은 MobileNetV2에서만
  차이가 나므로 실행 환경 간 부동소수점 연산 차이(예: oneDNN, CPU/GPU)로 FGSM 기울기 부호가
  일부 픽셀에서 달라졌을 가능성이 높다. 기존 결과를 만든 환경 정보가 없어 확정하지 못했다.
  `TF_ENABLE_ONEDNN_OPTS=0` 재실행은 하지 않았다.
- 확률값은 기존 방어 평가기가 내보내지 않아 비교하지 않았다. 따라서 뒤집힌 표본이 결정
  경계 근처였는지는 이 결과만으로 보일 수 없다.

## 6. 발견한 운영상 문제 (수정하지 않음)

1. **Windows 줄바꿈 변환:** `core.autocrlf=true`(Git for Windows 기본값)로 checkout하면
   `configs/test_manifest.json`이 CRLF로 바뀌어 `stage_b_readiness.py --contract-only`가
   `dataset manifest SHA-256 mismatch`로 실패한다. `.gitattributes`에
   `configs/*.json -text` 같은 규칙을 추가하면 해결될 것으로 보인다.
2. **첫 불일치에서 전체 중단:** `compare_outputs`가 첫 불일치에서 예외를 던져 이후 표본의 차이
   목록이 남지 않고, 다음 평가기(평균 필터)도 실행되지 않는다. FAIL을 유지하면서 모든 차이를
   기록하고 나머지 평가기까지 실행하도록 바꾸는 것을 검토할 수 있다.

## 7. 결과 파일

결과 묶음은 checkout 밖에 있다(기존 평가기의 출력 보호 규칙). 저장소에는 커밋하지 않았다.

| 파일 | SHA-256 |
| --- | --- |
| `stage-b-hyeonsu-01/rerun-report.json` | `314d30e089ee3179137772e0dbc84e8570884b5a14b64e38c6db2397fadb94a5` |
| `stage-b-hyeonsu-01/*` (그 외 15개) | `rerun-report.json`의 `artifact_sha256`에 기록 |
| `stage-b-hyeonsu-01-mean-diag/summary.json` | `0ead1ff925bb2d81a6fe57c463879d27881cc09b0f344789332598f64278f479` |
| `stage-b-hyeonsu-01-mean-diag/SHA256.json` | `b8f49f2a63d2aa9b3d410ee3d44f8008d3db469088543d2fb6e9f3fc075ec4da` |
| `stage-b-hyeonsu-01-mean-diag/COMPLETE.json` | `49b939e39497733b9409b1460a10c0b4de8a5e0d1a03d514a3ac87b8d6be5b8b` |
| `stage-b-hyeonsu-01-mean-diag.log` | `00d5226c2939304faf3b4e87aa6ed702a423e56baf2d4c5ea2c41c7abd6a581b` |

평균 필터 표본 CSV 8개의 해시는 `stage-b-hyeonsu-01-mean-diag/SHA256.json`에 기록돼 있다.
