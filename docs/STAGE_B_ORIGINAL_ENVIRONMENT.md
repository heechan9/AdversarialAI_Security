# 최초 환경 후보에서 한 번 실행하기

남은 5개 예측(4장)은 최초 기준과 불일치한다. [배열 추적](STAGE_B_TENSOR_TRACE.md)에서 확인했듯 최초 공격 배열은 보존돼 있지 않다. 다른 환경에서 설정을 바꿔 기준 라벨을 맞추는 대신, 최초 결과를 만든 PC의 보존 환경에서 새 배열을 채취한다.

## 실행 방법 — 희찬 PC의 기존 경로 기준

제공된 `AdversarialAI_original_environment_runner.zip`의 압축 해제 대상 폴더를 `C:\Users\hc247\AdversarialAI_original_environment_runner`로 지정한다. Anaconda Prompt에서 실행:

```bat
"%USERPROFILE%\AdversarialAI_original_environment_runner\verification\run_original_environment.cmd"
```

기존 `adversarial_ai` 환경을 사용하며 패키지를 설치·업그레이드하지 않는다. `TRACE_COMPLETE_NOT_APPROVED` 상태와 함께 `return-evidence.zip` 경로가 출력되면 **그 ZIP 하나**를 반환한다. 파일은 `%USERPROFILE%\AdversarialAI_original_trace_날짜_시각\return-evidence.zip`에 생성된다. 실패한 경우도 표시된 ZIP과 오류 메시지를 보존한다.

기본 입력은 앞서 실제 확인한 경로다:

- Git 객체 제공 저장소: `%USERPROFILE%\AdversarialAI_Security`
- 모델: 위 저장소의 `models` 폴더
- 테스트 이미지: `%USERPROFILE%\adversarial-fgsm-candidate-01\checkout\data\test`

입력 저장소에 고정 커밋 `491b973cd9f4840664044a83c0d62d1ee1bb98e8` 객체가 없으면 준비가 중단된다. 그 경우 `git -C "%USERPROFILE%\AdversarialAI_Security" fetch origin main`으로 객체를 받은 뒤 새 출력 폴더로 재실행한다. 기존 작업 브랜치를 바꾸거나 로컬 수정을 버릴 필요는 없다. 경로가 달라졌다면 Python 도구의 `--source-repo`, `--models-dir`, `--data-dir` 인수로 실제 경로를 지정한다.

## 수집과 보호 범위

1. Windows, Python 3.11.15, TensorFlow 2.21.0, Keras 3.15.1 확인. 버전 불일치는 추론 전에 중단한다. **버전 일치만으로 과거 환경과 동일하다고 증명하지 않는다.**
2. CPU·운영체제·패키지 이름/버전 및 계산 관련 환경변수만 기록한다. 전체 환경변수나 인증 토큰은 수집하지 않는다.
3. 로컬 Git 객체를 읽어 새 실행 폴더에 별도 checkout을 만들고 고정 커밋을 사용한다. 원본 checkout, 모델, 데이터는 읽기만 한다. 원본 모델 2개·이미지 781개를 확인하고 복사한 바이트도 다시 대조한다.
4. 기존 oneDNN·스레드 설정을 **그대로 상속**한 새 프로세스에서 5개 예측을 원래 32장 배치로 추적한다. oneDNN 변수가 없으면 `unset/native-default`로 기록하며 임의로 on/off였다고 판단하지 않는다.
5. 환경·버전, 실행 도구·선택 근거, 확률·경사·배치 공격 배열, 해시·로그를 ZIP으로 묶는다. 모델 파일과 781장 원본 전체 및 Git 저장소는 반환 ZIP에서 제외한다. 단, 공격 배열은 데이터에서 파생된 이미지이므로 ZIP은 공개 저장소에 올리지 않는다.

## 직접 시험한 범위와 미확인 범위

2026-09-27 Linux/Python 3.12 환경에서 자동화 도구를 `--execute`로 시험했다. 원본 2개 모델·781개 이미지 검증, 별도 코드 복사본, 실제 5개 추적, 해시와 반환 ZIP 생성까지 완료했다. 환경 일치 표시와 공식 검증 승인은 false로 유지됐고, 기존 5개 비기준 예측도 그대로 재현됐다.

이 시험은 **Windows CMD·Conda 실행 확인이 아니며**, 사용자의 `adversarial_ai` 환경을 여기서 원격 실행한 것도 아니다. 현재 시스템에서는 그 PC에 접근할 수 없으므로 위 명령 실행은 해당 PC에서 한 번 필요하다.

반환 결과가 기준 예측과 같더라도 먼저 기존/현재 경사·공격 배열과 계산 환경을 대조한다. 선택 사례 실행만으로 전체 781장·모든 조건의 B단계 PASS를 선언하지 않는다. 논문 표·확정 ε·공식 계약은 변경하지 않는다.

반환 ZIP은 임시 파일로 만든 뒤 CRC 검사를 통과하면 완성 파일로 교체한다. 9월 27일 이전 추적 증거 ZIP의 저장본 잘림을 확인해, 원래 해시가 보존된 개별 배열로 재구성했다. 복구 ZIP은 기존 문서의 SHA256과 정확히 같으며 수치 변경은 없다.
