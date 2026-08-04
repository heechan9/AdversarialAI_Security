# Project Scope

프로젝트 공식명: 자율운항선박 VLM·LLM 기반 AI 보안 프레임워크 구현
2026 스마트해운물류 × ICT 멘토링

## 3단계 연구 구조

1. **Clean Baseline** — CNN·MobileNet 선박 10클래스 분류 모델의 공격 없는 기준 성능 확보
2. **Adversarial Attack** — FGSM·BIM·PGD·JSMA를 CNN/MobileNet에 White-box로 적용, 취약성 정량 분석
3. **Safety Simulation** — 인식 오류가 항로판단에 미치는 영향을 검증하는 **연구용 안전영향 시뮬레이터** (실제 자율운항 제어시스템이 아님)

## 범위 단계 (Decision Gate 포함)

| 구분 | 범위 | 상태 |
|---|---|---|
| 최소 필수범위 | CNN Clean Baseline + CNN FGSM + 공통 평가체계 | 진행 대상 |
| 1차 확장 | CNN BIM·PGD | 최소범위 완료 후 |
| 2차 확장 | MobileNet Clean 평가 + MobileNet FGSM·BIM·PGD | Decision Gate — 팀/멘토 확정 필요 |
| 선택 확장 | JSMA 서브셋, Transferability, VLM·LLM(멀티모달 API) 연동, 방어기법, 생성형 AI | 시간 허용 시 |

멀티모달 API(GPT/Claude/Gemini)를 이용한 평가는 CNN/MobileNet 자체에 대한 White-box 공격이 아니라, **CNN/MobileNet이 생성한 적대적 이미지를 멀티모달 API에 입력하는 Transfer Attack 평가**입니다.

## 원칙
- 확인된 사실과 계획을 항상 구분한다
- 확인되지 않은 성능 수치를 만들지 않는다
- 방어기법은 공격 실험 완료 후 선택적으로 검토한다
