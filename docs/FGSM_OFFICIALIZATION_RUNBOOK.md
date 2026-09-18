# FGSM 공식 후보 실행 준비 절차

이 통합안은 PR #19의 후보 감사와 PR #22의 준비 점검을 연결한다. 현재 Clean 및
provisional FGSM 결과는 보존한다. 후보 감사 PASS는 공식 결과 승격이나 실제 추론
수행의 인증이 아니다. **사용자가 병합 전까지만 작업하도록 지시했으므로 현재 실행하지 않는다.**

## 단일 계약과 승인 경계

- 저장소 템플릿: `configs/fgsm_official_contract.json`.
- 상태: `pending_team_confirmation`. 승인자·승인시각·실행 SHA·epsilon·run ID는 미기입.
- 멘토가 팀에 결정을 위임한 상황에서는 팀의 실제 결정과 근거를 기록한다. 코드가
  멘토 개인의 승인만 강제하거나, 대화에 없는 승인자·날짜를 만들어 넣지 않는다.
- PR #19의 "팀 확정" 서술만으로 템플릿을 승인 상태로 바꾸지 않는다. 최종 실행
  계약과 근거를 사람이 확인해야 한다. PR #9/#19/#22 원본은 자동 병합·종료하지 않는다.
- 현재 후보 감사는 기존 감사기가 지원하는 sweep만 처리한다. 값을 변경하려면
  별도 계약·감사 검토가 필요하다. 코드에 새 성능 수치를 하드코딩하지 않는다.
- 모든 실행 산출물은 `results/attacks/official_candidate/<run_id>/`에 생성한다.
  `results/attacks/official/`로의 자동 이동·승격은 구현하지 않는다.

## 왜 실행 계약을 저장소 밖에 두나

실행 SHA를 계약에 쓰고 그 계약을 커밋하면 HEAD가 다시 바뀌어 자기참조가 생긴다.
먼저 검토된 코드 커밋을 고정하고, 저장소 밖의 새 JSON에 그 SHA와 팀이 실제로
확정한 조건을 기록한다. 준비기는 승인 계약이 checkout 안에 있거나 tracked 파일이
HEAD와 다르면 실패한다. 사용자의 기존 untracked 파일은 추가·삭제하지 않는다.

계약은 구조·기입 여부를 검사할 뿐 승인자의 신원이나 승인 내용의 진위를 인증하지 않는다.

## 승인 전 확인 (지금 가능한 단계)

아래 명령은 Windows Anaconda Prompt에서 한 줄씩 실행한다. 프롬프트 문자열은 복사하지 않는다.

```bat
conda activate adversarial_ai
cd /d C:\Users\hc247\AdversarialAI_Security
set PYTHONPATH=src
python scripts\check_fgsm_official_readiness.py
```

템플릿으로 실행하면 exit code 2와 차단 이유가 나와야 정상이다. 이미지·모델이 없는
환경에서는 해당 항목도 차단 이유에 포함된다. 모델을 로드하거나 FGSM을 실행하지 않는다.

## 향후 코드 검토·팀 결정 후 실행 순서

1. 검토된 코드 SHA를 checkout하고 전체 테스트·Research Evidence Audit·Paper Claim
   Audit·독립 Stage A 검증을 통과시킨다. 원본 781장과 두 `.h5`의 SHA-256도 확인한다.
2. 저장소 밖에 `fgsm-run-contract.json`을 만들고 템플릿의 모든 빈 값을 실제 결정으로
   채운다. `source_git_commit`은 실행할 HEAD, `status`는 실제 승인 후에만 `approved`로 쓴다.
3. 새 `run_id`를 정한다. 소문자·숫자·밑줄·하이픈만 사용하고 기존 폴더를 재사용하지 않는다.
4. 아래 준비 명령을 실행한다. **non-zero exit면 여기서 중단한다.** 준비기는 이미지·모델
   해시와 계약을 검사한 후 새 폴더에 실행 환경과 계약 원본 및 SHA-256을 고정한다.

```bat
python scripts\check_fgsm_official_readiness.py --contract "%USERPROFILE%\fgsm-run-contract.json"
python scripts\capture_official_fgsm_context.py --contract "%USERPROFILE%\fgsm-run-contract.json"
```

5. 출력된 후보 경로와 승인된 epsilon 목록을 사용해 기존 CNN/MobileNetV2 평가 CLI를
   실행한다. 아래 `<...>`는 설명용 자리표시자이며 그대로 실행할 명령이 아니다.
   실행 시점에 확정 계약에서 구체적인 한 줄 명령 두 개를 생성·대조한다.

```text
python -m adversarial_ai.evaluation.evaluate_fgsm_cnn --output <candidate-path> --epsilons <approved-values>
python -m adversarial_ai.evaluation.evaluate_fgsm_mobilenet --output <candidate-path> --epsilons <approved-values>
```

평가 CLI 자체는 기존과 같으며 준비 점검을 내부에서 강제하지 않는다. `capture`는
추론 실행기가 아니다. 각 모델 실행이 실패하면 다음 단계로 진행하지 않는다. 실행 중
가중치 불변 검사는 기존 evaluator를 그대로 사용한다. 부분 실패 폴더는 보존하고 새 run ID를 쓴다.

6. `audit_official_fgsm_candidate.py --candidate <candidate-path>`로 후보 전체를 감사한다.
   계약 SHA, source commit, runtime 버전, 표본 CSV·보고서·혼동행렬·분모·L∞·epsilon 0을
   대조한다. `images_verified`와 `model_binaries_verified`를 별도로 확인한다. 이미지·모델이
   없는 checkout의 artifact PASS를 바이너리 검증으로 표현하지 않는다.
7. 원본 파일·모델 SHA를 다시 확인하고 전체 테스트·두 감사·독립 Stage A를 재실행한다.
   감사 결과의 timestamp/SHA만 바뀐 파일은 커밋하지 않는다.
8. 현수의 모델 재실행 검증(B단계)과 팀 검토 후에만 공식 결과 고정과 논문 변경을 제안한다.
   Research Evidence/Paper Claim 감사는 아직 기존 provisional 근거를 검사한다. 후보
   감사는 별도이며 공식 결과 전환 시 논문 snapshot의 새 근거 연결도 따로 검토해야 한다.

## 검증 한계

- 후보 PNG는 파일 목록만 검사한다. 픽셀 내용이나 원본 정상/공격 배열을 재검증하지 않는다.
- 실행 기록을 사람이 위조하는 상황을 암호학적으로 방지하지 않는다. 독립 재실행과
  팀 검토가 필요하며, 예비 산출물을 복사해 공식 결과로 부르는 것은 허용하지 않는다.
- Stage A와 새 준비/후보 감사 테스트는 작은 synthetic fixture를 사용할 수 있다.
  테스트 통과를 실제 모델 추론 완료로 보고하지 않는다.
