# 현수 고정 배열 지원: 입력 보완과 반환 조건

2026-10-26 KST. 원래 `Hyunsu_AdversarialAI_optional_support_20261021.zip`을
기준으로 이어가는 보완 안내다. 자산 점검과 저장된 PC/Linux 공격 배열의
cross-only 분류만 다룬다. 실행자는 현수이며, 이 문서 작성 과정에서 새 모델
추론·공격 생성·학습을 수행하지 않았다.

## 확인된 입력 문제와 수정 범위

원본 패킷 SHA-256은
`d6fd80b6419f0aaf59081e1a9245cc967fca04798ca379939da1bdf1ee1527b4`이며
CRC와 내부 체크섬 8개가 일치했다. 다만 패킷에 실린 다음 세 파일은 출처의
바이트 그대로인 사본이 아니다. 각각 끝에 LF 한 개가 추가돼 있다.

| 파일 | 원본 패킷 SHA-256 | 고정 출처의 SHA-256 |
|---|---|---|
| `selection.json` | `1d9baa4ffd36b716a952fd49f4a98cadfca95db983549ec479ebe8ad8bbba917` | `8fc81a4408d6e43d5321bf9df2d416401a5b30df0af96a095d348496fcf6d52b` |
| `verified_trace_reference.py` | `87db30c6f87d271f90c6b0077b2ff375da0e4cb901f8be15c5e4dac7dac0689d` | `78ad7acb5289a2890ffe3365e27039c054c599d0f1c818252ecd28523a3c162b` |
| `expected_manifest.json` | `11711e9c13b8184e55fdbe8b2ae7d7644e0ce1adbb107a208f7f7da2bcef60b6` | `36059fea372334509404aca0e66155bf99a8df270beb1cc3bf4865b361ae70a6` |

JSON 두 파일의 해석값과 Python AST는 출처와 같지만, 저장 PC/Linux 보고서의
`selection_sha256`은 표의 **고정 출처 해시**다. 기존 도구는 이 값을 정확하게
대조하므로 동봉 selection을 그대로 넘기면 `Cross-input identity mismatch:
selection_sha256`에서 중단된다. 이는 모델 성능이나 환경 차이의 관측 결과가
아니라 입력 포장 문제다.

[입력 준비 도구](../verification/prepare_hyunsu_cross_inputs.py)는 알려진 원본
패킷 전체/내부 해시를 검사하고 고정 Git 객체의 바이트를 새 폴더로 준비한다.
원본 패킷·저장 보고서·선택 내용·기존 진단 도구의 로직·해시 대조 규칙을 바꾸지
않는다. 원래 패킷의 `asset_check.py`는 그대로 복사하며 manifest는 고정 원본을
사용한다. 준비 결과는 `PREPARED_NOT_EXECUTED`이고 지원 판정은 아직
`INCOMPLETE`다. 준비 도구 자체가 입력 자산을 검사하거나 모델을 실행하지 않는다.

## 고정 코드와 비공개 입력

- 평가 checkout: `491b973cd9f4840664044a83c0d62d1ee1bb98e8`, 추적 파일 변경 없음.
- 진단 도구/selection 출처: `b92ba8f450020479198a8bb03dbfa510044d6c19`.
  준비 도구의 새 커밋과 이 두 SHA를 구분해 실행 기록에 남긴다.
- 모델: `cnn_baseline.h5` 해시
  `cb256b1a5d6f605d355334e4e8667257a2bfbd29e08836cc4114869bd7068701`,
  `mobilenet_finetuned.h5` 해시
  `58c4878fa1480035d0bd5a63f8c3e22beac3a03f27f1aada6690b27f167129ae`.
  평가 checkout의 `models/`와 원본 `data/test/` 781장이 필요하다.
- PC 배열: `return-evidence(1).zip`, SHA-256
  `91ca97a5011f0a75dbf5c1e62e9c645df9c553910848721ee43f5d5ed60bde3f`.
  실제 `--other` 폴더는 압축 해제된 `native-trace`다.
- Linux 배열: `StageB_tensor_trace_evidence_20260927.zip`, SHA-256
  `a7d9fd77de08bbd2d3774572ed8acb2581120f4c2f8e6ba6f17c98cd6ac8a4ee`.
  실제 생성 배열 폴더는 `trace-on` 또는 `trace-off-02`다. `trace-off-cross`는
  이미 수행한 교차 분류 결과이며 새 입력 배열 폴더로 대신 쓰지 않는다.

위 두 배열 원본은 수신 측에서 확보해 CRC, 보고서의 모델/manifest/selection
해시, 3개 생성 실행 × 5항목의 NPZ 해시를 정적으로 대조했다. 항목별 입력 배치
해시가 PC/Linux에서 같았다. NPZ의 전체 배치 attack은 float32
`(32,224,224,3)`, 유한값·[0,1] 범위였고 선택 image/gradient는
`(1,224,224,3)`였다. 이는 저장 배열 점검이며 새 분류 결과가 아니다.
같은 행 99의 원래 공격은 두 필터 항목에 중복 기록된다.

**수신 측 보존본 확보와 현수의 접근권한/로컬 자산 확보는 별개다.** 기존 승인된
비공개 전달 경로를 확인하며 공개 Git에 NPZ·모델·원본 이미지를 올리지 않는다.
현재 현수 환경의 자산 점검 JSON과 이번 cross-only 반환 결과는 확인되지 않았다.

## 준비와 최소 실행 명령

아래는 **Windows Anaconda Prompt/CMD** 예시다. 경로는 예시이며 새 폴더를 쓴다.
기존 개발 폴더에서 checkout/reset하거나 패키지를 업그레이드하지 않는다.
준비 도구는 이 보완 PR의 검토된 checkout에서 실행하고, `--repo`는 별도의
고정 평가 checkout을 가리킨다. Git 이력이 없는 복사본이나 shallow clone에
고정 객체가 없으면 준비를 중단하고 보고한다.

`adversarial-integration-review`는 평가 checkout과 다른 **도구 보관 폴더**다.
#98의 도구가 검토·승인된 뒤 아래처럼 확보하고 HEAD를 기록한다. 이 명령은
이번 제출 전 사용 점검에서 추가한 누락 단계이며, 기존 패킷·#98 head는 바꾸지 않는다.

```bat
git -c core.autocrlf=false clone https://github.com/heechan9/AdversarialAI_Security.git C:\Project\adversarial-integration-review
git -C C:\Project\adversarial-integration-review fetch origin 76849fcf69731676f869e7054fa12c9ef0d1a1a7
git -C C:\Project\adversarial-integration-review checkout --detach 76849fcf69731676f869e7054fa12c9ef0d1a1a7
git -C C:\Project\adversarial-integration-review rev-parse HEAD
```

브랜치 이름에 의존하지 않고 고정 SHA를 가져온다. fetch 또는 checkout이 실패하거나
출력 HEAD가 아래 SHA와 다르면 중단하고 보고하며 최신 브랜치로 임의 대체하지 않는다.
위 SHA는 #98에서 검사한 준비 도구 버전이다. 평가 SHA `491b973`이나 실제 진단
도구 출처 `b92ba8`을 대신하지 않는다. 원본 지원 ZIP과 PC/Linux 배열은 기존
비공개 전달 경로에서 별도로 확보한다. 이 clone 명령으로 배열 접근권한이 생기는
것은 아니며, 접근이 막히면 소유자에게 필요한 파일명·해시를 알려 확인받는다.

```bat
git -c core.autocrlf=false clone https://github.com/heechan9/AdversarialAI_Security.git C:\Project\adversarial-hyunsu-baseline-20261026
git -C C:\Project\adversarial-hyunsu-baseline-20261026 checkout --detach 491b973cd9f4840664044a83c0d62d1ee1bb98e8

python C:\Project\adversarial-integration-review\verification\prepare_hyunsu_cross_inputs.py --repo C:\Project\adversarial-hyunsu-baseline-20261026 --packet C:\Project\Hyunsu_AdversarialAI_optional_support_20261021.zip --output C:\Project\hyunsu-inputs-20261026-01
```

준비 폴더에 `selection.json`, `stage_b_trace_b92ba8.py`, `expected_manifest.json`,
`asset_check.py`, `preparation.json`이 생긴다. 원본 패킷의 동봉 selection 대신
**준비 폴더 selection**을 아래 두 단계에 사용한다. 저장 보고서의 해시를
동봉 파일에 맞춰 고치거나 비교 검사를 건너뛰지 않는다.

1. 기존 보존본에서 모델·이미지를 새 평가 checkout에 복사한 뒤 자산만 점검한다.

```bat
python C:\Project\hyunsu-inputs-20261026-01\asset_check.py --repo C:\Project\adversarial-hyunsu-baseline-20261026 --output C:\Project\hyunsu-assets-20261026-01.json
```

`ASSETS_MATCH`는 모델 2개·이미지 781개 및 추가 파일/checkout 상태의 입력
점검이다. 모델 추론이나 전체 재현 통과가 아니다. 누락·해시 차이·패키지
미설치/버전 차이가 있으면 그 목록을 반환하고 중단한다. 이 보완 도구의 준비
성공을 현수의 자산 점검 성공으로 대체하지 않는다.

2. 자산과 각 원본 배열 보고서/해시가 확인됐을 때만 행 99부터 분류한다.

```bat
python C:\Project\hyunsu-inputs-20261026-01\stage_b_trace_b92ba8.py --repo-root C:\Project\adversarial-hyunsu-baseline-20261026 --selection C:\Project\hyunsu-inputs-20261026-01\selection.json --other C:\Project\evidence\pc\native-trace --cross-only --control-row 99 --native-settings --output C:\Project\hyunsu-cross-pc-row99-01 > C:\Project\hyunsu-cross-pc-row99-01.log 2>&1
echo %ERRORLEVEL%
```

명령 직후 다른 명령을 실행하기 전에 종료코드를 반환 파일로 남기려면 위
`echo` 대신 다음 두 줄을 쓴다. 실행별로 새 파일명을 사용한다.

```bat
set "HYUNSU_CROSS_EXIT=%ERRORLEVEL%"
> C:\Project\hyunsu-cross-pc-row99-01.exit-code.txt echo %HYUNSU_CROSS_EXIT%
```

사전 검사에서 중단돼 `report.json`이 없더라도 실행 명령·로그·종료코드와
중단 단계를 반환한다. 보고서 부재를 선택 표본 불일치로 기록하지 않는다.

같은 설정으로 `--other`만 Linux `trace-on`/`trace-off-02`의 실제 해제 위치로
바꾸고 출력·로그에는 각각 새 이름을 쓴다. 원래 32장 배치를 유지한다.
기본 범위는 새 공격·재학습·C++ 개발·781장 전체 재분류가 아니다.

확대할 경우 `--control-row 99`만 제거해 원 패킷의 4장·5항목을 분류한다.
행 99(Gaussian/Mean attacked .03), 439(Gaussian adaptive .03),
241(Mean adaptive .05), 533(Mean transfer .05)이다. 행은 CSV 0-based다.
먼저 원래 환경 설정을 보존하며, 미설정은 `unset/native-default`로 적는다.
oneDNN·스레드 대조는 필요한 경우에만 별도 프로세스·새 출력으로 수행하고
라벨이 기준에 맞는 설정만 골라 보고하지 않는다.

## 반환·판정

원 패킷의 결과 양식과 차이표에 자산 점검 JSON, 준비 기록, 실제 명령,
시작/종료 시각·종료코드·로그, cross-only `report.json`, OS/CPU/Python/TF/Keras,
oneDNN/intra/inter/OMP/deterministic 값 또는 unset을 연결한다. 공개용 기록에서는
개인 경로와 식별정보를 제거하되 원본은 승인된 비공개 영역에 보존한다.

| 상태 | 적용 조건 | 확대하면 안 되는 해석 |
|---|---|---|
| `INCOMPLETE` | 자산/배열/보고서 없음, 입력 해시 불일치, 미실행·중단 또는 반환 근거 미확보 | 실행 실패 원인이나 사람의 미수행을 자료 부재만으로 단정하지 않음 |
| `SELECTED_MATCH` | 입력 무결성·명령·환경·완료 로그가 확인되고 완료한 선택 항목이 비교 대상과 일치 | 전체 781장/모든 조건 재현 PASS 아님 |
| `SELECTED_DIFFERENT` | 동일 입력 검증 후 선택 항목의 라벨 또는 확률 차이가 확인됨 | 원인 확정 또는 전체 실패로 일반화하지 않음 |

라벨 차이 개수와 최대 확률 절대차를 따로 적는다. 라벨 일치만 확인했으면
확률까지 일치했다고 표시하지 않으며 확률 허용 기준/비교 범위를 명시한다.
선택 일치 여부는 비교 대상 저장 실행의 예측과의 관계이고, 선종 정답률이 아니다.
이번 패킷으로 공식 Stage B PASS를 부여하지 않는다. 기존 연구 PC
`LOCAL_PASS`와 외부 환경 `FAIL`·원인 미확정은 함께 유지한다.

현재 반환이 필요한 항목: 현수 자산 점검, PC/Linux 접근 확인, cross-only
report/log/명령/환경/차이표. 두 원본 배열 ZIP은 수신 측에 확보됐으므로
‘원본이 존재하지 않는다’고 적지 않는다. 현수의 로컬 접근이 막히면 해당
자산 이름·예상 해시·접근 문제를 구체적으로 누락 목록에 적는다.
