# CPU 회귀검사와 SHA별 교차 검수

## 범위와 기준

도입 base: `c62ac82c47eaf524b5efef78ee817fe2bdc65baf` (main).
기존 `iterative-attacks.yml`을 확장하며 별도 중복 CPU 워크플로를 만들지 않는다.
PR(Draft 포함), main push, workflow_dispatch에서 실행한다. 기존 Evidence integrity도
수동 실행·시간 제한·동일 PR 이전 실행 취소를 지원한다. 권한은 contents: read다.
저장소에 AGENTS.md/CONTRIBUTING 지침은 없으며 기존 연구 계약과 기여 기록을 따른다.
현수의 #47 보고서, #78 GPU 복구, 기존 결과·공격·평가 구현은 이 변경의 대상이 아니다.

CI는 Ubuntu / Python 3.11 / TensorFlow CPU 2.21.0 / Keras 3.15.1을 사용한다.
직접 의존성은 requirements-ci.txt에 고정하고 전이 의존성은 실행별 pip freeze로 남긴다.
로컬 Python 3.12 검사는 CI의 Python 3.11 실행과 별도로 보고한다.
CI 자원 사용을 위해 intra-op=2/inter-op=1, CUDA_VISIBLE_DEVICES=-1을 사용한다.
oneDNN과 결정론 옵션은 변경하지 않고 unset/native-default 여부를 기록한다.
이 설정은 역사적 실험 환경의 복원이나 변경이 아니다.

## 실행

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-ci.txt
python -m pip check
PYTHONPATH=src:. CUDA_VISIBLE_DEVICES=-1 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1 python verification/ci_cpu.py
```

전체 tests를 실행하되 torch 전용 test_surfree_adapter.py는 기존 blackbox-series.yml에서
검사한다. 해당 워크플로가 실행되지 않은 PR에서는 SurFree 검증도 수행됐다고 주장하지 않는다.
기본 CPU CI는 TensorFlow 필수 import, 빈 suite/skip 거부, JUnit, 공개 저장 증거 감사,
9개 기존 논문 주장 집계 감사를 실행한다. 기존 부분 iterative checkpoint 재감사도 유지한다.
실패 시 install/regression 로그, JUnit(생성된 경우), 실제 checkout SHA, PR head SHA,
환경 JSON, pip freeze를 ci-artifacts에 14일 보관한다. 설치 실패 전 JUnit은 존재할 수 없다.
감사 보고서는 ci-artifacts에 기록하며 canonical 결과를 덮어쓰지 않는다.

| 요구 | 재사용/추가 검사 |
|---|---|
| RGB, 정규화, 10클래스 순서, 크기 | test_ci_cpu_contract, test_clean_baseline, test_manifest_validation |
| FGSM ε=0, [0,1], L∞ 예산, 모델 불변 | test_fgsm |
| 3×3 커널, 경계, 채널, clean 비교 | test_gaussian_defense, test_mean_defense |
| 전달 f(D(A(f;x))) / 적응 f(D(A(f∘D;x))) | test_defense_evaluation, test_mean_defense_evaluation 및 필터 경사 검사 |
| 정확도·ASR 분모, 클래스 개수, 저장 수치·논문 집계 | test_classwise_integration, test_audit*, test_paper_claims, test_*evidence_audit |
| 잘못된 파일·설정·모델 계약 | test_manifest_validation, test_stage_b_readiness, test_official_candidate_audit |
| 필수 의존성/실행 누락 | ci_cpu import 점검, JUnit skip/빈 suite 거부 및 반례 테스트 |

## 재현성 경계

[현수 보고 검토](STAGE_B_HYEONSU_01_REVIEW.md)의 16셀·14장 불일치를 보존한다.
[Linux 진단](STAGE_B_LOCAL_FOLLOWUP.md)은 oneDNN on에서 16개 현수 예측 일치,
off에서 11개 기준으로 변경·5개 잔존을 기록한다.
[후속 PC 전체 결과](STAGE_B_PC_FULL_20260928.md)는 기준 라벨과 일치했지만
독립 실행자의 PASS를 새로 부여하지 않으며 단일 원인은 미확정이다.
라벨 100%, 지표 1e-6, L∞ ε+1e-6 계약은 완화하지 않는다.
CPU CI PASS는 공개 CSV의 일관성과 합성 회귀 검사의 통과만 뜻한다.
비공개 모델·781장 재추론, GPU 전체 실험, 외부 독립 승인은 별도 검증이다.

## 교차 검수 절차

1. 작성자는 정확한 base/head SHA, 변경 파일, 명령, 직접 실행 결과와 미검증 범위를 PR에 기록한다.
2. 기계 CI는 해당 head에 연결된 run URL/결론과 PR merge checkout SHA를 남긴다.
3. 별도 검수자는 같은 head의 diff를 읽고 반례를 실행한다. 직접 실행 / 작성자 보고 / 미검증을 나눠 보고한다.
4. 결함은 파일·재현 명령·입력·기대/실제 결과를 포함한다. 새 커밋 뒤 이전 승인으로 대체하지 않는다.
5. 새 head CI와 별도 검토를 확인한다. 일반 CI는 AI 리뷰나 인간 독립 승인과 동일하지 않다.

Claude/Jules 전달문 (실제 SHA를 채운 PR 본문의 검수 패킷 사용):

> 이 PR의 base/head를 checkout하고 base...head diff를 읽기 전용으로 검수하세요.
> 위 설치/실행 명령으로 검사하되 비공개 입력, GPU 실험, 재학습, 원시 결과 변경은 하지 마세요.
> 수용 기준: Draft PR/main/manual 트리거, timeout/concurrency/read-only 권한,
> 실패 로그/JUnit/환경 기록, 필수 검사 skip 거부, 기존 검사 재사용,
> 결과·허용오차·현수 작업 보존, 공개 입력만으로 실행, 문서의 검증 범위 정확성.
> 보고서에 검토 SHA, 직접 실행/작성자 보고/미검증, 재현 가능한 결함을 분리하세요.
> 수정되면 새 head를 다시 확인하고 이전 head 통과를 새 코드 승인으로 쓰지 마세요.

자동 Claude/Jules 리뷰의 인증·비용·권한 설정은 이번 CI에 포함하지 않는다.
비밀값이나 Drive 직접 링크를 workflow·로그·검수 패킷에 넣지 않는다.
PR #79는 사용자 후속 요청에 따라 2026-10-07 병합되었다. 병합 SHA는
`b4b127427082c672f252f127bb7e7ef98e0ec43b`이며 PR/main CI가 성공했다.
이 완료는 미완료 GPU 실험 PR #78이나 공식 781장 재추론 완료를 뜻하지 않는다.
사용자가 전달한 Claude 감사는 이 SHA에서 537 passed/0 skipped 및 낮음 3건을 보고했다.
이는 Claude 전달 보고이며 Codex 직접 실행과 구분한다. 후속 수정 SHA는 별도 재검토한다.
