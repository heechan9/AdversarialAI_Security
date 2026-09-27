# 남은 B단계 차이의 경사·공격 배열 추적

2026-09-27, [로컬 후속 진단](STAGE_B_LOCAL_FOLLOWUP.md)에 이어 실제 모델로 수행했다.
**남은 5개 예측(4장)은 아직 기준과 불일치한다. 공식 B단계 FAIL을 PASS로 바꾸지 않는다.**

## 수행 방식과 검증

- 변경 없는 `491b973cd9f4840664044a83c0d62d1ee1bb98e8` 평가 코드, 기존 모델·781장 manifest를 사용했다.
- Linux, Python 3.12.14, TensorFlow 2.21.0, Keras 3.15.1, CPU(AMD EPYC 9V74), intra/inter-op 및 OMP 스레드 2개다. 최초 Windows/Conda 환경을 복원한 것이 아니다.
- 남은 5개와, 앞서 on/off에 따라 예측이 바뀐 대조 사례 1개를 각각 원래 32장 배치에서 추적했다. 의도적으로 선택한 사례이며 전체 정확도 추정에 사용할 수 없다.
- on/off 별 입력 경사와 공격 배열을 저장했다. **계측한 공격 배열은 매번 기존 `generate_fgsm` 출력과 바이트 단위로 같았으며**, 공격 크기 제한·유한값·모델 가중치 불변성을 확인했다.
- 저장한 전체 배치 공격 배열을 반대 설정에 그대로 넣어 교차 분류했다. 입력 전처리 배열의 동일성과 저장 배열 SHA256도 확인했다.
- 4개 캡처 실행 및 2개 교차 분류 실행이 완료됐다. 초기 1회는 manifest 모델 키에 절대경로를 넘겨 사전 검사에서 중단됐고, 상대 키로 수정한 뒤 완료된 실행만 분석했다.

## 남은 5개 결과

| 조건 / CSV 0-based 행 | 경사 부호가 다른 성분 수 | 공격 채널 값이 다른 성분 수 | on/off·교차 분류 예측 | 기준 예측 |
|---|---:|---:|---:|---:|
| 가우시안 방어 인지 ε=.03 / 439 | 20 | 20 | 6 | 7 |
| 가우시안 원래 공격 ε=.03 / 99 | 53 | 53 | 6 | 1 |
| 평균 방어 인지 ε=.05 / 241 | 110 | 110 | 7 | 3 |
| 평균 원래 공격 ε=.03 / 99 | 53 | 53 | 6 | 1 |
| 평균 전달 ε=.05 / 533 | 14 | 14 | 6 | 1 |

성분 수의 분모는 이미지당 224×224×3=150,528개다. 행 99는 같은 이미지의 같은 원래 공격이 두 필터 평가에 중복 기록된 것이다.

같은 공격 배열을 분류할 때 on/off 간 최대 확률 차이는 약 `4.77e-6` 이하였고, 남은 5개에서는 예측이 바뀌지 않았다. 반면 공격을 각각 생성하면 경사 부호 차이로 14~110개 채널 값이 달라졌다. 서로 다른 두 공격의 픽셀 차이는 최대 약 `2ε`일 수 있지만, 각 공격과 원본의 차이는 `ε` 이내임을 별도로 검사했다.

**이 시험은 남은 5개가 최초 기준과 달라진 원인을 확정하지 않는다.** 현재 on/off 두 경로 모두 같은 비기준 예측을 유지했다. 기준 실행은 공격 배열·경사를 보존하지 않았으므로 그 최초 배열과 직접 대조할 수 없다. 같은 이유로 CPU, 라이브러리, 전처리 중 하나를 원인으로 단정하지 않는다.

## 예측이 바뀐 대조 사례의 원인 분리

대조군은 `Aircraft Carrier/Aircraft Carrier_19.jpeg`, 가우시안 방어 인지 ε=.01, 행 25다. 입력은 같고, 두 공격 사이에서 경사 부호와 공격 채널 값이 각각 10개 달랐다.

| 고정한 공격 배열 | off에서 분류 | on에서 분류 |
|---|---:|---:|
| off에서 생성 | 7 | 7 |
| on에서 생성 | 5 | 5 |

**이 사례에서는 예측 변경이 최종 분류 설정보다 공격 생성 과정의 수치 차이를 따라간다.** FGSM의 부호 연산이 미세한 경사 차이를 서로 다른 공격 픽셀로 바꾼 사례다. 이를 나머지 5개의 원인이 확인된 것처럼 일반화하지 않는다.

## 증거와 다음 판정 조건

- [수치·확률·해시 JSON](../results/verification/stage_b/hyeonsu_01_review/tensor_trace.json)
- [재실행 도구](../verification/stage_b_trace.py): 새 출력 폴더만 사용하며 원본 코드·계약·canonical 결과를 수정하지 않는다.
- 비공개 보존 파일: `StageB_tensor_trace_evidence_20260927.zip` (약 69 MiB). 전체 배치 공격 배열, 선택 이미지 경사, 확률, 스크립트, 완료·실패 로그 포함.
- ZIP SHA256: `a7d9fd77de08bbd2d3774572ed8acb2581120f4c2f8e6ba6f17c98cd6ac8a4ee`.

남은 5개의 최초 차이를 더 좁히려면 **최초 결과를 만든 환경에서 동일한 추적 도구로 배열을 새로 채취해 비교**해야 한다. 옛 배열이 없으므로 이 실행이 가능하더라도 과거 배열 자체를 복원했다고 부를 수는 없다. 해당 환경을 확보할 수 없으면 원인 미확정 한계를 유지한다. 이번 로컬 환경의 기준 실행 조건은 기록했지만 연구 전체의 최종 재검증 환경 승인이나 결과 일치 승인으로 취급하지 않는다.

실행 예시(아래 입력 checkout은 위 고정 커밋이고 원본 모델·데이터가 있어야 함):

```bash
TF_ENABLE_ONEDNN_OPTS=0 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=2 OMP_NUM_THREADS=2 python verification/stage_b_trace.py --repo-root /path/to/pinned-source --selection results/verification/stage_b/hyeonsu_01_review/local_followup.json --output /path/to/new-off
TF_ENABLE_ONEDNN_OPTS=1 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=2 OMP_NUM_THREADS=2 python verification/stage_b_trace.py --repo-root /path/to/pinned-source --selection results/verification/stage_b/hyeonsu_01_review/local_followup.json --output /path/to/new-on --other /path/to/new-off
TF_ENABLE_ONEDNN_OPTS=0 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=2 OMP_NUM_THREADS=2 python verification/stage_b_trace.py --repo-root /path/to/pinned-source --selection results/verification/stage_b/hyeonsu_01_review/local_followup.json --output /path/to/new-off-cross --other /path/to/new-on --cross-only
```

대조 사례만 실행하려면 세 명령에 각각 `--control-row 25`를 추가하고 별도 출력 폴더를 쓴다. Windows Anaconda Prompt에서는 해당 환경변수를 `set NAME=value`로 설정한 뒤 같은 Python 인수를 사용한다. 설정을 기준 라벨에 맞춰 선택하거나 허용오차를 확대하지 않는다. 논문 표와 기존 연구 결론은 이번 진단으로 수정하지 않았다.
