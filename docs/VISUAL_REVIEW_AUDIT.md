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
