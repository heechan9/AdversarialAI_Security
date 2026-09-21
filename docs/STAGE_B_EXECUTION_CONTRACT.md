# Stage B 독립 재실행 계약

Stage B는 저장된 결과를 다시 계산하는 A단계와 달리, 원본 `.h5` 모델과 테스트 이미지
781장으로 Clean 예측과 FGSM을 독립적으로 다시 실행하는 작업이다. 이 문서는 실행 완료
보고서가 아니라, 현수에게 자산을 전달하기 전에 입력·허용오차·출력을 고정하는 준비 계약이다.

## 현재 상태

- 논문 실험 범위와 FGSM ε=`0, 0.01, 0.03, 0.05`는 확정됐다.
- 모델·이미지는 GitHub에 없고 Stage B 실행 기록도 없다.
- 비교 허용오차는 계약 파일에 제안값으로 기록했으며 검토자 확인 전에는 판정 기준으로
  사용하지 않는다.
- 준비 계약: `configs/stage_b_verification_contract.json`
- 읽기 전용 점검기: `verification/stage_b_readiness.py`

## 잠긴 입력

| 입력 | 기대값 |
|---|---|
| CNN | `models/cnn_baseline.h5`, SHA-256 `cb256b…8701` |
| MobileNetV2 | `models/mobilenet_finetuned.h5`, SHA-256 `58c487…29ae` |
| 테스트셋 | `data/test`, 781장 |
| 이미지 목록 | `configs/test_manifest.json`의 경로·순서·SHA-256 |
| 전처리 | 두 모델 모두 `rescale=1./255` |
| 공격 | untargeted 1-step FGSM, L∞, 입력·clip 범위 [0,1] |

점검기는 모델을 역직렬화하지 않는다. 경로 안전성, symlink, 파일 누락·추가, 781장 전체
해시, 모델 해시, source commit, 승인 기록, 출력 경로의 신규성만 fail-closed로 검사한다.

## 실행 전 채울 값

1. 현수와 비교 허용오차를 합의한 뒤 `comparison.status`를 `confirmed`로 바꾼다.
2. 검증할 checkout의 40자 commit SHA를 `source.commit_sha`에 기록한다.
3. 검토자와 시간을 `review`에 기록한다. 없는 승인 기록을 만들지 않는다.
4. 고유한 `outputs.run_id`를 정하고 `status`를 `ready`로 바꾼다.
5. 아래 명령이 `ready: true`일 때만 별도 재실행을 시작한다.

```bash
python verification/stage_b_readiness.py
```

커밋된 계약과 manifest의 구조만 확인하는 CI 명령은 다음과 같다.

```bash
python verification/stage_b_readiness.py --contract-only
```

`--contract-only` PASS는 모델·이미지가 준비됐거나 Stage B가 실행됐다는 뜻이 아니다.

## 출력 원칙

- 출력은 `results/verification/stage_b/<run_id>/`에 새로 생성한다.
- 기존 Clean·FGSM·방어 결과를 덮어쓰지 않는다.
- 표본별 라벨·확률·L∞, 요약 정확도·ASR, 실행 환경과 입력 해시를 함께 보존한다.
- 일치하지 않으면 기존 결과나 허용오차를 수정하지 않고 FAIL로 보고한다.
