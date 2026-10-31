# Project Scope

프로젝트 공식명: 자율운항선박 VLM·LLM 기반 AI 보안 프레임워크 구현
2026 스마트해운물류 × ICT 멘토링

## 2026-11-01 협업용 현재 상태

아래 초기 로드맵·이력은 보존합니다. [영문 조건별 상태](INTERNATIONAL_COLLABORATION.md#condition-status-historical-fgsm-and-separate-follow-ups)를 우선 읽습니다.
기존 FGSM·필터의 실험/기록 감사 완료와 공식 실행계약의 미연결 승인, 외부 FAIL을 구분합니다.
10/24 matched CNN은 seed2026만 완료했고2027/2028은 미실행입니다. 최초 외부 과제는
[공개 저장 결과 감사 한 건](INTERNATIONAL_COLLABORATION.md#first-external-review-one-saved-result-audit-no-private-assets)이며
새 학습·연구자 연락·자료 공유 승인이 아닙니다. 데이터 권한·원천 ID 계보·선박/장면 그룹이 후속 연구의 우선 전제입니다.

## 3단계 연구 구조

1. **Clean Baseline** — CNN·MobileNet 선박 10클래스 분류 모델의 공격 없는 기준 성능 확보
2. **Adversarial Attack** — FGSM·BIM·PGD·JSMA를 CNN/MobileNet에 White-box로 적용, 취약성 정량 분석
3. **Safety Simulation** — 인식 오류가 항로판단에 미치는 영향을 검증하는 **연구용 안전영향 시뮬레이터** (실제 자율운항 제어시스템이 아님)

위 구조는 전체 프로젝트 로드맵이다. **현재 논문 실험 범위는 CNN·MobileNetV2, 781장, Clean·FGSM(ε=0, 0.01, 0.03, 0.05), 고정 3×3 가우시안·평균 필터의 전달/방어 인지 비교로 확정되어 있다.**
2026-09-20 사용자 확인을 반영했다. 범위 확정과 기존 산출물의 상태·별도 실행 승인 기록을 구분한다.

| 근거 상태 | 현재 범위 |
| --- | --- |
| 구현·검증됨 | CNN·MobileNetV2 Clean baseline |
| 실험·기록 감사 완료 | one-step untargeted FGSM; 확정 ε=0, 0.01, 0.03, 0.05 (`provisional` 원자료 보존) |
| 코드 지원과 결과 주장을 분리해야 함 | targeted FGSM 등 canonical 결과가 고정되지 않은 기능 |
| 실험·기록 감사 완료 | 고정 3×3 가우시안·평균 필터 전처리, 기존 FGSM 입력·방어 인지 FGSM 비교 및 근거 감사 |
| 구현됨 (기록 재생) | MARIS 설명용 3D·회색 CAD 보기·저장 이미지 및 방어 결과 비교; 실시간 추론·운항 제어 아님 |
| 계획 | BIM·PGD·JSMA, 모델 간 transfer evaluation, VLM·LLM 연동, 적대적 학습, 안전영향 시뮬레이션 |
| 장기 확장 | physical patch, camera/AIS/GNSS/radar fusion, navigation decision robustness, MASS cyber-physical red teaming |

현재 실증 범위와 해양 운영 영향의 경계는 `docs/THREAT_MODEL.md`를 따른다.

## 전체 프로젝트 확장 로드맵

아래 단계는 초기 로드맵이다. 현재 논문의 범위 확정을 다시 대기 상태로 돌리는 단계표가 아니다.

| 구분 | 범위 | 상태 |
|---|---|---|
| 최소 필수범위 | CNN Clean Baseline + CNN FGSM + 공통 평가체계 | 구현·기록 감사 완료; 확정된 논문 실험 범위 |
| 1차 확장 | CNN BIM·PGD | 최소범위 완료 후 |
| 2차 확장 | MobileNet Clean 평가 + MobileNet FGSM·BIM·PGD | Clean·FGSM은 확정된 논문 실험 범위이며 기록 감사 완료; BIM·PGD는 후속 계획 |
| 전처리 비교 | 가우시안·평균 필터 + 전달/방어 인지 FGSM | 확정된 논문 실험 범위; 실험·기록 감사 완료 (`experimental` 원자료 보존) |
| 선택 확장 | JSMA 서브셋, Transferability, VLM·LLM(멀티모달 API) 연동, 추가 방어기법·적대적 학습, 생성형 AI | 시간 허용 시 |

멀티모달 API(GPT/Claude/Gemini)를 이용한 평가는 CNN/MobileNet 자체에 대한 White-box 공격이 아니라, **CNN/MobileNet이 생성한 적대적 이미지를 멀티모달 API에 입력하는 Transfer Attack 평가**입니다.

## 원칙
- 확인된 사실과 계획을 항상 구분한다
- 확인되지 않은 성능 수치를 만들지 않는다
- 가우시안·평균 필터는 실험 완료 상태로 기록하되, 방어 인지 공격과 정상 성능 손실을 함께 보고한다
- 코드 병합이나 기록 감사 통과를 공식 결과 채택·독립 모델 추론·최종 논문 검증으로 간주하지 않는다

최신 수치와 논문 준비 상태는 [현재 연구 상태](CURRENT_RESEARCH_STATUS.md) 및 [논문 관리 현황](PAPER_RELEASE_STATUS.md)을 따른다.

## Bounded international research roadmap — 2026-10-30

These are **candidate issue scopes**, not issued assignments, scheduled experiments, completed results or a promise of journal acceptance. The October 31 international-research transition is a planning goal. The historical roadmap above is preserved; latest recorded extensions are linked from [current research status](CURRENT_RESEARCH_STATUS.md). Reuse existing issues/PRs before opening duplicates.

| Candidate issue | Bounded question and dependencies | Required completion evidence / stop boundary |
|---|---|---|
| R1: independent reproduction and mismatch diagnosis | Can an independent environment reproduce the fixed reference under the existing Stage B contract? After the first public saved-record task, use the selected cross-only handoff only with authorized private input access. Source-ID lineage, rights and vessel/scene grouping remain prior dependencies for new generalization claims. | Source/input hashes, actual execution logs and outputs, unchanged comparison criteria, discrepancy report. Asset-only checks or missing arrays remain INCOMPLETE; stop at the agreed diagnostic scope, not a forced PASS. |
| R2: matched-training control across seeds | Do the one-seed observations persist under the predeclared matched protocol? Coordinate with open #87 and the separately saved October 24 package. | Separately approved compute/data plan, matched initialization/training exposure, seed-specific records, clean/robust results and uncertainty with justified sampling assumptions. One seed and 6.15% PGD50 accuracy are not general defense validation. |
| R3: additional attack/defense evaluation | Which bounded adaptive/iterative or black-box condition adds evidence beyond FGSM? Inspect unfinished #78 and #86 before choosing one condition. | Agreed threat model, epsilon/steps/restarts/query budget, adaptive defense handling, clean cost and ASR cohort definitions, preserved failures, independent review of exact SHA. Do not silently pool own-clean denominators or overwrite baseline metrics. |
| R4: international manuscript evidence package | Which claims are supported by the fixed baseline versus separately approved extensions? | Claim-to-file/SHA mapping, limitations, licensing/access statement and contributor review. Venue selection, authorship agreement and submission require separate human decisions; no private files or contact details published by default. |

[VLM/LLM and maritime operational integration](THREAT_MODEL.md) remain outside demonstrated capabilities. New datasets, physical attacks, sensor/control experiments, compute expenditure and model execution require separately agreed scope and authorization. [Collaboration entry](INTERNATIONAL_COLLABORATION.md) explains the existing code/artifacts and a small first contribution.
