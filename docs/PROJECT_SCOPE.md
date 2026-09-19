# Project Scope

프로젝트 공식명: 자율운항선박 VLM·LLM 기반 AI 보안 프레임워크 구현
2026 스마트해운물류 × ICT 멘토링

## 3단계 연구 구조

1. **Clean Baseline** — CNN·MobileNet 선박 10클래스 분류 모델의 공격 없는 기준 성능 확보
2. **Adversarial Attack** — FGSM·BIM·PGD·JSMA를 CNN/MobileNet에 White-box로 적용, 취약성 정량 분석
3. **Safety Simulation** — 인식 오류가 항로판단에 미치는 영향을 검증하는 **연구용 안전영향 시뮬레이터** (실제 자율운항 제어시스템이 아님)

위 구조는 전체 연구 로드맵이다. 현재 저장소에서 canonical evidence로
검증된 범위와 계획 범위를 혼동하지 않는다.

| 근거 상태 | 현재 범위 |
| --- | --- |
| 구현·검증됨 | CNN·MobileNetV2 Clean baseline |
| 예비 결과·감사됨 | one-step untargeted FGSM (`provisional`) |
| 코드 지원과 결과 주장을 분리해야 함 | targeted FGSM 등 canonical 결과가 고정되지 않은 기능 |
| 구현·실험됨 (experimental) | 고정 3×3 가우시안·평균 필터 전처리, 기존 FGSM 입력·방어 인지 FGSM 비교 및 근거 감사 |
| 구현됨 (기록 재생) | MARIS 설명용 3D·회색 CAD 보기·저장 이미지 및 방어 결과 비교; 실시간 추론·운항 제어 아님 |
| 계획 | BIM·PGD·JSMA, 모델 간 transfer evaluation, VLM·LLM 연동, 적대적 학습, 안전영향 시뮬레이션 |
| 장기 확장 | physical patch, camera/AIS/GNSS/radar fusion, navigation decision robustness, MASS cyber-physical red teaming |

현재 실증 범위와 해양 운영 영향의 경계는 `docs/THREAT_MODEL.md`를 따른다.

## 범위 단계 (Decision Gate 포함)

| 구분 | 범위 | 상태 |
|---|---|---|
| 최소 필수범위 | CNN Clean Baseline + CNN FGSM + 공통 평가체계 | 구현·근거 감사 완료; FGSM 수치는 provisional |
| 1차 확장 | CNN BIM·PGD | 최소범위 완료 후 |
| 2차 확장 | MobileNet Clean 평가 + MobileNet FGSM·BIM·PGD | Clean·FGSM 구현 및 기록 감사 완료; FGSM provisional, BIM·PGD는 계획 |
| 전처리 비교 | 가우시안·평균 필터 + 전달/방어 인지 FGSM | 구현·실험 완료 (experimental); 공식 채택은 별도 |
| 선택 확장 | JSMA 서브셋, Transferability, VLM·LLM(멀티모달 API) 연동, 추가 방어기법·적대적 학습, 생성형 AI | 시간 허용 시 |

멀티모달 API(GPT/Claude/Gemini)를 이용한 평가는 CNN/MobileNet 자체에 대한 White-box 공격이 아니라, **CNN/MobileNet이 생성한 적대적 이미지를 멀티모달 API에 입력하는 Transfer Attack 평가**입니다.

## 원칙
- 확인된 사실과 계획을 항상 구분한다
- 확인되지 않은 성능 수치를 만들지 않는다
- 가우시안·평균 필터는 실험 완료 상태로 기록하되, 방어 인지 공격과 정상 성능 손실을 함께 보고한다
- 코드 병합이나 기록 감사 통과를 공식 결과 채택·독립 모델 추론·최종 논문 검증으로 간주하지 않는다

최신 수치와 논문 준비 상태는 [현재 연구 상태](CURRENT_RESEARCH_STATUS.md) 및 [논문 관리 현황](PAPER_RELEASE_STATUS.md)을 따른다.
