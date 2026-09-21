# Stage B 별도 환경 재실행 안내

논문 범위의 기능·기록 실험은 완료됐다. 원본 모델·781장으로 기존 결과가 별도 환경에서
재현되는지 확인한다. 기존 평가·공격 구현을 재사용하는 **독립 실행자·환경의 재실행**이며,
알고리즘을 별도로 구현한 검증은 아니다. 실제 실행 완료 기록은 아직 없다.

## 준비물

- Python 3.11, Git. 저장소 루트에서 실행한다.
- `models/cnn_baseline.h5`, `models/mobilenet_finetuned.h5`, `data/test/` 781장은 별도 전달한다.
- `python -m venv ../stage-b-venv`로 별도 환경을 만든다.
  Linux/macOS: `source ../stage-b-venv/bin/activate`
  Windows PowerShell: `../stage-b-venv/Scripts/Activate.ps1`
- `python -m pip install -r requirements.txt`로 저장소의 TensorFlow/Keras 버전을 설치한다.
  이 변경에서는 실제 H5 로딩·추론을 확인하지 못했다.

## 1. 외부 계약 사본

```bash
python verification/stage_b_run.py --prepare --contract ../hyeonsu-stage-b.json --run-id hyeonsu-01
```

현재 checkout의 전체 commit SHA와 실행 ID가 외부 **초안**에 기록된다.
승인이나 모델 실행 기록을 생성하지 않으며 기존 파일을 덮어쓰지 않는다.
저장소의 `configs/stage_b_verification_contract.json`은 수정하지 않는다.

현수와 희찬이 비교 기준을 실제 확인한 뒤 외부 사본에서만 다음을 채운다.

- `comparison.status`: `confirmed`
- `review.approved_by`: 실제 확인한 사람
- `review.approved_at`: 실제 확인 시각(시간대 포함 ISO-8601)
- `status`: `ready`

제안 기준: 라벨 100% 일치, 요약 지표 절대차 ≤ 1e-6, L∞ ≤ ε+1e-6.
합의하지 못하면 실행하지 않고 기준을 논의한다. 결과에 맞춰 사후 완화하지 않는다.
확률 허용오차는 참고 항목이다. 기존 방어 평가기는 확률을 내보내지 않아 **확률 비교는 수행하지 않는다**.

## 2. 실행 전 검사

```bash
python verification/stage_b_readiness.py --contract ../hyeonsu-stage-b.json
```

`ready: true`여야 진행한다. 781장 목록·해시, 모델 해시와 기존 Clean 메타데이터,
수정되지 않은 코드와 source SHA, 실제 확인 기록, 출력 경로 신규성을 검사한다.
오류가 나면 기존 결과나 해시를 고치지 말고 메시지를 공유한다.

## 3. 실행 및 비교

```bash
python verification/stage_b_run.py --contract ../hyeonsu-stage-b.json
```

- CNN·MobileNetV2, 전체 781장, ε=`0, 0.01, 0.03, 0.05`
- Clean, FGSM, 필터 적용 Clean
- 고정 3×3 Gaussian(binomial /16)·평균(/9), REFLECT padding
- 기존 공격에 필터를 적용한 전달 조건, 필터까지 미분한 방어 인지 조건

두 기존 평가기를 순서대로 실행하며 각 평가기에서 Clean 일치를 먼저 검사한다.
긴 평가에 앞서 Python 3.11·TensorFlow 2.21.0·Keras 3.15.1과 두 H5 모델의
해시·로딩·입출력 형태를 검사한다. 실패 이유는 `preflight.log`에 남고 추론은 시작하지 않는다.
16개 모델·ε·필터 조합의 표본별 예측 12,496행과 전체/클래스별 요약을 보존 결과와 대조한다.
ASR은 해당 경로의 정상 정답 표본을 분모로 사용한다.

결과는 외부 계약과 같은 디렉터리의 `stage-b-hyeonsu-01/`에 생성한다.
기존 평가기가 저장소 밖 출력을 요구하므로 이전 저장소 내부 출력 규칙을 외부 묶음으로 변경했다.
기존 논문 수치와 원자료는 덮어쓰지 않는다.

## 반환할 파일

- `rerun-report.json`: PASS/FAIL, 기준 SHA, 명령, 환경, 비교 결과, 파일 해시
- `execution-contract.json`, `environment.txt`
- `preflight.log`: 버전과 모델 로딩 사전 검사(추론 검증은 아님)
- `gaussian.log`, `mean.log` 및 두 결과 폴더

실행 실패나 비교 불일치도 FAIL 보고서를 남긴다. 준비 검사 실패는 실행 전이므로 화면에
차단 이유만 출력한다. `Ctrl+C` 중단은 `INTERRUPTED`로 기록한다.
강제 종료·전원 차단 시 보고서가 남는 것은 보장하지 않는다.
실패한 폴더를 재사용하지 말고 새 실행 ID를 사용한다.
Clean 불일치로 조기 중단하면 오류는 로그에 남으며 모든 표본의 차이 파일은 생성되지 않을 수 있다.
중단·자료 누락·FAIL을 완료로 표시하지 않는다.

## 모델 없이 가능한 검사

```bash
python verification/stage_b_readiness.py --contract-only
python verification/maris_source_check.py
python -m pytest tests/test_stage_b_readiness.py tests/test_stage_b_run.py -q
```

준비 구조·비교기·실행 연결 테스트와 원본 결과↔MARIS 대조다.
원본 H5/이미지 추론 성공이나 현수의 B단계 완료를 뜻하지 않는다.
기존 `provisional/experimental` 경로는 보존 이력이다.
