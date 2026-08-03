# Multimodal API Selection

조사 기준일: 2026-08 | 방법: 각 사 공식 문서만 사용(2차 자료 배제). 확인 불가 항목은 "확인 불가"로 표기.
목적: 선박 전용 API가 아니라, 이미지 입력이 가능한 **범용 멀티모달 API**를 비교한다.

## 비교표

| 항목 | OpenAI (Responses API) | Anthropic (Claude API) | Google (Gemini API) |
|---|---|---|---|
| 정확한 모델 ID | `gpt-5.6` (alias, 비전 가이드 전체가 이 ID 사용). 세부 tier(`gpt-5.6-sol`/`-terra`/`-luna`)는 가격표에 별도 표기 — alias→스냅샷 매핑은 [모델 카탈로그](https://developers.openai.com/api/docs/models)에서 재확인 필요 | `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5-20251001` — **고정 스냅샷 명시** | `gemini-3.6-flash`, `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`(2026.10.16 폐지 예정) |
| 이미지 입력 | 지원 | 지원 | 지원 |
| Structured Output/JSON Schema | 지원 | 지원 (GA) | 지원 |
| Python SDK | `openai` | `anthropic` | `google-genai` |
| 이미지 제한 | PNG/JPEG/WEBP/무정지GIF, 요청당 최대 512MB·1500장 | JPEG/PNG/GIF/WebP, 최대 8000×8000px, 요청당 100~600장 | PNG/JPEG/WEBP/HEIC/HEIF, 요청당 최대 3600장, inline 20MB |
| 가격 (1M 토큰당, 대표 모델) | `gpt-5.6-sol` $5/$30 · `gpt-5.4-mini` $0.375/$2.25 | Opus5 $5/$25 · Haiku4.5 $1/$5 | `3.6-flash` $1.50/$7.50 · `2.5-flash-lite` $0.10/$0.40 |
| 무료 tier | 확인 불가 (공식 문서 명시 없음) | 확인 불가 (공식 문서 명시 없음) | **명시적 Free tier 있음** (Flash/Flash-Lite, Pro는 유료 전용) |
| Rate limit | tier별, 공식 페이지 존재 | RPM/ITPM/OTPM, token bucket, 조직 tier별 | RPM/TPM/RPD, 프로젝트 단위 |
| 데이터 보존 정책 | 2023.3.1부터 학습에 미사용(기본), 최대 30일 보관 후 삭제, ZDR 옵션 | 표준은 짧은 TTL 삭제, ZDR·HIPAA 옵션 | **Free tier: 제품개선에 사용됨 / Paid tier: 미사용** |
| 고정 snapshot 가능 여부 | 확인 불가 (alias 방식으로 보임) | **가능 — 모든 모델 ID가 고정 스냅샷** | 대체로 alias 형태, `-preview` 모델은 변경 가능성 명시 |
| 예상 구현 난이도 | 중간 — patch/tile 방식이 모델별로 달라 비용 계산이 가장 복잡 | 낮음 — 토큰화 공식·비용 예시가 명확 | 낮음 — 258토큰/타일 공식이 가장 단순 |

공식 문서:
- OpenAI: [Images and vision](https://developers.openai.com/api/docs/guides/images-vision) · [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) · [Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses) · [Pricing](https://developers.openai.com/api/docs/pricing) · [Models](https://developers.openai.com/api/docs/models)
- Anthropic: [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview) · [Vision](https://platform.claude.com/docs/en/build-with-claude/vision) · [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) · [Rate limits](https://platform.claude.com/docs/en/api/rate-limits) · [Data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)
- Google: [Pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Image understanding](https://ai.google.dev/gemini-api/docs/image-understanding) · [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) · [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) · [Libraries](https://ai.google.dev/gemini-api/docs/libraries)

## 결론: **Conditional recommendation — OpenAI Responses API**

프로젝트 공식명과 멘토 피드백이 "멀티모달 GPT API"를 명시하고 있고, OpenAI Responses API가 이미지 입력·Structured Output·Python SDK를 모두 공식 지원하므로 기능상 결정적 문제는 없습니다. 다만 조건을 명시합니다:

**조건**
1. 비용이 세 후보 중 가장 높고 계산이 복잡함 — PoC는 반드시 `gpt-5.4-mini` + `detail: low`로 시작해 비용을 확인한 뒤 필요 시 상위 모델로 올릴 것
2. 모델 ID가 고정 스냅샷인지 alias인지 공식 문서로 확인되지 않음 — 논문 재현성 서술을 위해 실제 사용한 정확한 모델 문자열과 호출 시점을 `docs/REPRODUCIBILITY.md`에 반드시 기록할 것
3. 무료 tier·정확한 rate limit 수치는 이번 조사에서 확인 불가 — 계정 생성 시점에 대시보드에서 재확인 필요

**대안 비교 참고**: 비용·재현성만 보면 Gemini(최저가+무료tier)와 Claude(고정 스냅샷)가 더 유리합니다. 멘토 피드백과 상충되지 않는 선에서, 전체 781장×5 규모 실험은 비용 절감을 위해 Gemini/Claude 교차검증을 병행하는 것을 권장합니다(팀 논의 필요 — 최종 확정 아님).

## 확인 불가 항목 (재확인 필요)
- OpenAI 무료 크레딧 정확한 금액, 모델 ID 고정 여부
- Anthropic 무료 크레딧 정확한 금액
- 3사 모두 정확한 rate limit 수치(계정 tier에 따라 상이 — 대시보드 확인 필요)
- 3사 모두 한국에서의 정확한 이용 가능 여부(지원국가 목록 페이지는 확인했으나 "한국" 항목 자체를 직접 검색하지 못함)
