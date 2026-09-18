# Strict Visual Review Evidence Audit

## Overview

This document defines the evidence chain, dynamic derivation rule, review methodology, and strict claim boundaries for the visual review evidence audit in `heechan9/AdversarialAI_Security`.

---

## 1. Evidence Chain & Files

Visual review records are stored as immutable CSV files in `results/audit/evidence/`:
- `review_taehee_visual_strict_final.csv` (31 records, reviewed by 김태희)
- `review_jaehyuk_visual_strict_final.csv` (32 records, reviewed by 이재혁)
- `63_images_strict_visual_audit.csv` (63 combined records)
- `manifest.json` (authoritative file SHA-256 values and candidate/rounding contract)

All files preserve UTF-8 BOM encoding and use the exact schema:
- **Split CSVs:** `file_path`, `current_label`, `cnn_prediction`, `cnn_confidence`, `mnv2_prediction`, `mnv2_confidence`, `판정`, `검토자`, `검토일`, `비고`
- **Combined CSV:** Same 10 columns plus `엄격검증_기준`

---

## 2. Dynamic Candidate Derivation Rule

Candidates for visual review are derived dynamically from canonical Clean baseline evaluation CSVs (`results/clean/cnn_baseline_eval.csv` and `results/clean/mobilenet_eval.csv`).

An image sample is selected as a candidate if and only if:
1. **Model Agreement:** Both CNN baseline and MobileNetV2 models predict the exact same class (`cnn_prediction == mnv2_prediction`).
2. **Label Disagreements:** The shared prediction differs from the canonical dataset label (`cnn_prediction != current_label`).
3. **High Confidence:** Both unrounded predicted-class confidences are `>= 0.70`.

For the current canonical Clean evaluation dataset, the audit dynamically derives 63
matching images. This is a reported result of the current canonical CSVs, not an
independently hard-coded acceptance value.

---

## 3. Review Allocation, Judgment Counts & Methodology

- **Review Allocation:** The candidate set is partitioned into two disjoint subsets:
  - 김태희 reviewed 31 images (`review_taehee_visual_strict_final.csv`).
  - 이재혁 reviewed 32 images (`review_jaehyuk_visual_strict_final.csv`).
- **Current Dynamic Judgment Totals:** Derived at audit time from the authoritative evidence CSVs:
  - `라벨 정확`: 55
  - `판단 보류`: 4
  - `라벨 오류 의심`: 4
- **Image-Specific Visual Notes:** All 63 `비고` notes contain unique, image-specific descriptions of physical ship features (e.g. deck structure, hull color, superstructure).
- **AI-Assisted Human-Confirmed Review:** Visual feature descriptions were generated with AI assistance (GPT Plus) and subsequently reviewed and confirmed against physical image files by the assigned human reviewer.
- **Partitioned Single Review:** The review task was divided between the two reviewers. This is partitioned single review, NOT independent double review or inter-rater validation protocol.

---

## 4. Audit Verification Contracts & Mandatory Boundaries

The audit tool (`adversarial_ai.audit.visual_review`) verifies:
1. **Schema & UTF-8 BOM Integrity:** Exact ordered columns, a required UTF-8 BOM, required non-empty fields, numeric confidence ranges (`[0, 1]`), ISO `YYYY-MM-DD` review dates, one consistent non-empty criterion (`엄격검증_기준`), non-repeated unique visual notes (`비고`), and allowed Korean judgment values (`라벨 정확`, `라벨 오류 의심`, `판단 보류`).
2. **Split Disjointness & Combined Equality:** The split review files are strictly disjoint, and their set union matches `63_images_strict_visual_audit.csv` row-for-row on all shared fields.
3. **Candidate Set Equality:** The set of image paths in the review CSVs exactly equals the dynamically derived candidate set.
4. **Canonical Consistency:** Every record matches canonical Clean baseline evaluations for `current_label` and both predictions. Each displayed confidence must equal the corresponding unrounded canonical predicted-class confidence rounded to the three decimal places declared in `manifest.json`; a broad numeric tolerance is not used.
5. **Byte Integrity:** Each CSV's SHA-256 must equal its authoritative digest in `manifest.json`. The CSV paths are marked `-text` in `.gitattributes` so Git does not normalize CRLF bytes.

### Mandatory Claim Boundaries
- **Record Integrity Only:** This audit certifies CSV record integrity, Clean baseline consistency, and review split/union correctness. It does NOT independently inspect raw image bytes and does NOT certify that visual ship-type judgments are objectively correct ground truth.
- **No Publication Authorship:** Participation in visual review does not imply academic or publication co-authorship.


## 감사 통과와 판정 의미의 경계

`PASSED`는 고정된 CSV의 해시·형식·후보 일치·분할/통합 기록 일관성에 대한
통과이다. 실제 이미지의 선종 정답성, 전문가 검토 또는 독립 이중 검토를
입증하지 않는다. `judgment_counts`는 기존 CSV 문자열의 빈도이며 정답률이 아니다.
JSON의 `claim_boundary`와 CLI/Paper Claim 출력에 이 경계를 명시한다.

사용자가 전달한 후속 확인에 따르면 김태희의 **추가 회신**에서 ‘라벨 정확’은
선종 클래스가 아닌 비고 설명이 맞다는 의미였다. 이 확인을 기존 고정 CSV
전체의 의미로 소급 적용하거나 기존 파일을 재라벨링하지 않는다. 추가 회신은
이번 변경에서 가져오지 않으며 공개 저장소에 원본을 추가하지 않는다.

향후 회신 연결용 `summarize_followup_reviews(records, meaning=...)`는 정규화된
행마다 `sample_id`, `reviewer`, `judgment`, `meaning`, `meaning_source`를 요구한다.
의미는 `description_confirmation`(설명 확인) 또는 `class_label_opinion`(선종 의견)
중 명시적으로 확인한 값만 허용한다. 빈값·미확인 값·추가 열·중복 행과 혼합
의미 집계는 `AuditError`로 거부한다. 판정 문자열이나 검토자 이름으로 의미를
추정하지 않는다. 다른 판정값의 의미도 확인 전 자동 변환하지 않는다.

이 함수는 기존 CSV importer가 아닌, 후속 연결에서 사용할 집계 API이다.
확인 출처 문자열은 추적용이며 확인의 진실성을 코드가 인증하는 것은 아니다.
설명 확인과 선종 의견은 각각 집계하더라도 합산해 라벨 정답률로 표현하면 안 된다.
선종 의견만 집계한 경우에도 `label_correctness_verified`는 false이다.
