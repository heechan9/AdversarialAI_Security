"""Mutation tests proving that tampered evidence causes non-zero exit / AuditError."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from adversarial_ai.audit.clean import audit_clean_evaluation
from adversarial_ai.audit.cross_doc import audit_cross_documents
from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.fgsm import audit_fgsm_results
from adversarial_ai.audit.manifest_models import audit_manifest, audit_models
from adversarial_ai.audit.runner import run_full_audit
from adversarial_ai.audit.visual_review import audit_visual_reviews, derive_candidate_rows


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    """Create a temporary copy of repo structure for mutation testing."""
    copy_dir = tmp_path / "repo"
    for item in ["configs", "docs", "results", "README.md"]:
        src = Path(item)
        dst = copy_dir / item
        if src.is_dir():
            shutil.copytree(src, dst)
        elif src.is_file():
            shutil.copy2(src, dst)
    return copy_dir


def test_mutation_tampered_clean_csv(repo_copy: Path) -> None:
    eval_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    summary_json = repo_copy / "results" / "clean" / "cnn_baseline_summary.json"
    df = pd.read_csv(eval_csv)
    # Tamper with predicted label of a row without updating 'correct' column
    df.loc[1, "predicted_label"] = "Tug"  # Row 1 was predicted as Aircraft Carrier (correct=True)
    df.to_csv(eval_csv, index=False)

    with pytest.raises(AuditError) as exc_info:
        audit_clean_evaluation(eval_csv, summary_json_path=summary_json)
    assert "correct" in str(exc_info.value).lower() or "disagrees" in str(exc_info.value).lower()


def test_mutation_tampered_clean_accuracy_count(repo_copy: Path) -> None:
    eval_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    summary_json = repo_copy / "results" / "clean" / "cnn_baseline_summary.json"
    df = pd.read_csv(eval_csv)
    # Invert predictions and correct values for first 10 rows
    df.loc[:9, "predicted_label"] = df.loc[:9, "true_label"]
    df.loc[:9, "correct"] = True
    df.to_csv(eval_csv, index=False)

    with pytest.raises(AuditError) as exc_info:
        audit_clean_evaluation(eval_csv, summary_json_path=summary_json)
    assert "disagrees" in str(exc_info.value).lower()


def test_mutation_tampered_fgsm_asr_denominator(repo_copy: Path) -> None:
    prov_dir = repo_copy / "results" / "attacks" / "provisional"
    # Pass incorrect clean_correct_count (500 instead of 504)
    with pytest.raises(AuditError) as exc_info:
        audit_fgsm_results(prov_dir, "cnn", clean_correct_count=500)
    assert "denominator" in str(exc_info.value)


def test_mutation_tampered_fgsm_linf_violation(repo_copy: Path) -> None:
    sample_csv = repo_copy / "results" / "attacks" / "provisional" / "fgsm_cnn_eps_0.01_samples.csv"
    df = pd.read_csv(sample_csv)
    df.loc[0, "linf"] = 0.05  # Violates eps=0.01
    df.to_csv(sample_csv, index=False)

    with pytest.raises(AuditError) as exc_info:
        audit_fgsm_results(repo_copy / "results" / "attacks" / "provisional", "cnn", clean_correct_count=504)
    assert "L_infinity" in str(exc_info.value)


def test_mutation_tampered_eps_zero_violation(repo_copy: Path) -> None:
    sample_csv = repo_copy / "results" / "attacks" / "provisional" / "fgsm_cnn_eps_0_samples.csv"
    df = pd.read_csv(sample_csv)
    df.loc[0, "attack_success"] = True  # Violates eps=0 invariant
    df.to_csv(sample_csv, index=False)

    with pytest.raises(AuditError) as exc_info:
        audit_fgsm_results(repo_copy / "results" / "attacks" / "provisional", "cnn", clean_correct_count=504)
    assert "eps=0" in str(exc_info.value) or "attack_success" in str(exc_info.value)


def test_mutation_manifest_missing_sample(repo_copy: Path) -> None:
    manifest_p = repo_copy / "configs" / "test_manifest.json"
    data = json.loads(manifest_p.read_text(encoding="utf-8"))
    data["test_files"].pop()  # 780 instead of 781
    manifest_p.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(AuditError) as exc_info:
        audit_manifest(manifest_p)
    assert "781" in str(exc_info.value)


def test_mutation_manifest_reordered_or_duplicate(repo_copy: Path) -> None:
    manifest_p = repo_copy / "configs" / "test_manifest.json"
    data = json.loads(manifest_p.read_text(encoding="utf-8"))
    data["test_files"][0] = data["test_files"][1]  # Create duplicate
    manifest_p.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(AuditError) as exc_info:
        audit_manifest(manifest_p)
    assert "Duplicate" in str(exc_info.value)


def test_mutation_model_sha_mismatch(repo_copy: Path) -> None:
    meta_p = repo_copy / "results" / "clean" / "cnn_baseline_metadata.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    meta["model_sha256"] = "a" * 64
    meta_p.write_text(json.dumps(meta), encoding="utf-8")

    manifest_models = {
        "models/cnn_baseline.h5": "cb256b1a5d6f605d355334e4e8667257a2bfbd29e08836cc4114869bd7068701"
    }
    with pytest.raises(AuditError) as exc_info:
        audit_models(manifest_models, [meta_p])
    assert "mismatch" in str(exc_info.value).lower()


def test_mutation_doc_claim_mismatch(repo_copy: Path) -> None:
    readme_p = repo_copy / "README.md"
    content = readme_p.read_text(encoding="utf-8").replace("0.6453264951705933", "0.999999")
    readme_p.write_text(content, encoding="utf-8")

    with pytest.raises(AuditError) as exc_info:
        audit_cross_documents(repo_root=repo_copy)
    assert "README.md" in str(exc_info.value)


def test_run_full_audit_tampered_fails(repo_copy: Path) -> None:
    # Tamper one file in repo_copy
    sample_csv = repo_copy / "results" / "attacks" / "provisional" / "fgsm_mobilenet_eps_0.03_samples.csv"
    df = pd.read_csv(sample_csv)
    df.loc[0, "linf"] = 0.1
    df.to_csv(sample_csv, index=False)

    with pytest.raises(AuditError):
        run_full_audit(repo_root=repo_copy, output_report_path=repo_copy / "report.json")


def test_mutation_visual_review_missing_path(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    cnn_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_copy / "results" / "clean" / "mobilenet_eval.csv"

    comb_file = ev_dir / "63_images_strict_visual_audit.csv"
    df = pd.read_csv(comb_file, encoding="utf-8-sig")
    df = df.iloc[:-1]  # Drop 1 path
    df.to_csv(comb_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(ev_dir, cnn_csv, mob_csv)
    assert "discrepancy" in str(exc_info.value).lower() or "does not match" in str(exc_info.value).lower()


def test_mutation_visual_review_split_combined_drift(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    cnn_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_copy / "results" / "clean" / "mobilenet_eval.csv"

    taehee_file = ev_dir / "review_taehee_visual_strict_final.csv"
    df = pd.read_csv(taehee_file, encoding="utf-8-sig")
    df.loc[0, "current_label"] = "Tug"
    df.to_csv(taehee_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(ev_dir, cnn_csv, mob_csv)
    assert "drift" in str(exc_info.value).lower()


def test_mutation_visual_review_generic_repeated_notes(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    cnn_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_copy / "results" / "clean" / "mobilenet_eval.csv"

    comb_file = ev_dir / "63_images_strict_visual_audit.csv"
    df = pd.read_csv(comb_file, encoding="utf-8-sig")
    df.loc[1, "비고"] = df.loc[0, "비고"]  # Duplicate note
    df.to_csv(comb_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(ev_dir, cnn_csv, mob_csv)
    assert "duplicate" in str(exc_info.value).lower() or "generic" in str(exc_info.value).lower()


def test_mutation_visual_review_blank_criteria(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    cnn_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_copy / "results" / "clean" / "mobilenet_eval.csv"

    comb_file = ev_dir / "63_images_strict_visual_audit.csv"
    df = pd.read_csv(comb_file, encoding="utf-8-sig")
    df.loc[0, "엄격검증_기준"] = "   "
    df.to_csv(comb_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(ev_dir, cnn_csv, mob_csv)
    assert "blank" in str(exc_info.value).lower() or "엄격검증_기준" in str(exc_info.value)


def test_mutation_visual_review_altered_confidence(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    cnn_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_copy / "results" / "clean" / "mobilenet_eval.csv"

    comb_file = ev_dir / "63_images_strict_visual_audit.csv"
    split_file = ev_dir / "review_jaehyuk_visual_strict_final.csv"
    for f in (comb_file, split_file):
        df = pd.read_csv(f, encoding="utf-8-sig")
        if "DDG/DDG_1045.jpeg" in df["file_path"].values:
            df.loc[df["file_path"] == "DDG/DDG_1045.jpeg", "cnn_confidence"] = 0.123
            df.to_csv(f, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(ev_dir, cnn_csv, mob_csv)
    assert "confidence" in str(exc_info.value).lower()


def test_mutation_visual_review_invalid_judgment(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    cnn_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_copy / "results" / "clean" / "mobilenet_eval.csv"

    comb_file = ev_dir / "63_images_strict_visual_audit.csv"
    split_file = ev_dir / "review_jaehyuk_visual_strict_final.csv"
    for f in (comb_file, split_file):
        df = pd.read_csv(f, encoding="utf-8-sig")
        if "DDG/DDG_1045.jpeg" in df["file_path"].values:
            df.loc[df["file_path"] == "DDG/DDG_1045.jpeg", "판정"] = "INVALID_JUDGMENT"
            df.to_csv(f, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(ev_dir, cnn_csv, mob_csv)
    assert "judgment" in str(exc_info.value).lower()


def test_mutation_visual_review_wrong_reviewer(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    cnn_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_copy / "results" / "clean" / "mobilenet_eval.csv"

    taehee_file = ev_dir / "review_taehee_visual_strict_final.csv"
    comb_file = ev_dir / "63_images_strict_visual_audit.csv"
    df_t = pd.read_csv(taehee_file, encoding="utf-8-sig")
    df_t.loc[0, "검토자"] = "WrongReviewer"
    df_t.to_csv(taehee_file, index=False, encoding="utf-8-sig")

    df_c = pd.read_csv(comb_file, encoding="utf-8-sig")
    df_c.loc[df_c["file_path"] == df_t.loc[0, "file_path"], "검토자"] = "WrongReviewer"
    df_c.to_csv(comb_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(ev_dir, cnn_csv, mob_csv)
    assert "reviewer" in str(exc_info.value).lower()


def test_mutation_visual_review_changed_threshold(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    cnn_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_copy / "results" / "clean" / "mobilenet_eval.csv"

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(ev_dir, cnn_csv, mob_csv, confidence_threshold=0.80)
    assert "threshold" in str(exc_info.value).lower()


def test_mutation_visual_review_missing_bom(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    taehee_file = ev_dir / "review_taehee_visual_strict_final.csv"
    raw = taehee_file.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    taehee_file.write_bytes(raw[3:])

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(
            ev_dir,
            repo_copy / "results" / "clean" / "cnn_baseline_eval.csv",
            repo_copy / "results" / "clean" / "mobilenet_eval.csv",
        )
    assert "bom" in str(exc_info.value).lower()


def test_mutation_visual_review_extra_schema_column(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    taehee_file = ev_dir / "review_taehee_visual_strict_final.csv"
    frame = pd.read_csv(taehee_file, encoding="utf-8-sig")
    frame["unexpected_extra"] = "x"
    frame.to_csv(taehee_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(
            ev_dir,
            repo_copy / "results" / "clean" / "cnn_baseline_eval.csv",
            repo_copy / "results" / "clean" / "mobilenet_eval.csv",
        )
    assert "schema" in str(exc_info.value).lower()


@pytest.mark.parametrize("review_date", ["", "2026/09/05", "2026-02-30"])
def test_mutation_visual_review_invalid_review_date(
    repo_copy: Path, review_date: str
) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    taehee_file = ev_dir / "review_taehee_visual_strict_final.csv"
    frame = pd.read_csv(taehee_file, encoding="utf-8-sig", dtype=str)
    frame.loc[0, "검토일"] = review_date
    frame.to_csv(taehee_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(
            ev_dir,
            repo_copy / "results" / "clean" / "cnn_baseline_eval.csv",
            repo_copy / "results" / "clean" / "mobilenet_eval.csv",
        )
    assert "검토일" in str(exc_info.value) or "date" in str(exc_info.value).lower()


def test_mutation_visual_review_blank_note(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    jaehyuk_file = ev_dir / "review_jaehyuk_visual_strict_final.csv"
    frame = pd.read_csv(jaehyuk_file, encoding="utf-8-sig", dtype=str)
    frame.loc[0, "비고"] = " "
    frame.to_csv(jaehyuk_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(
            ev_dir,
            repo_copy / "results" / "clean" / "cnn_baseline_eval.csv",
            repo_copy / "results" / "clean" / "mobilenet_eval.csv",
        )
    assert "비고" in str(exc_info.value) or "empty" in str(exc_info.value).lower()


def test_mutation_visual_review_altered_nonblank_criteria(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    combined_file = ev_dir / "63_images_strict_visual_audit.csv"
    frame = pd.read_csv(combined_file, encoding="utf-8-sig", dtype=str)
    frame.loc[0, "엄격검증_기준"] = "임의로 바꾼 기준"
    frame.to_csv(combined_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(
            ev_dir,
            repo_copy / "results" / "clean" / "cnn_baseline_eval.csv",
            repo_copy / "results" / "clean" / "mobilenet_eval.csv",
        )
    assert "엄격검증_기준" in str(exc_info.value)


def test_mutation_visual_review_consistent_criteria_tamper_hits_hash(
    repo_copy: Path,
) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    combined_file = ev_dir / "63_images_strict_visual_audit.csv"
    frame = pd.read_csv(combined_file, encoding="utf-8-sig", dtype=str)
    frame["엄격검증_기준"] = "모든 행에 동일하게 바꾼 임의 기준"
    frame.to_csv(combined_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(
            ev_dir,
            repo_copy / "results" / "clean" / "cnn_baseline_eval.csv",
            repo_copy / "results" / "clean" / "mobilenet_eval.csv",
        )
    assert "sha-256" in str(exc_info.value).lower()


def _mutate_split_and_combined(
    evidence_dir: Path, file_path: str, column: str, value: object
) -> None:
    for name in (
        "review_taehee_visual_strict_final.csv",
        "review_jaehyuk_visual_strict_final.csv",
        "63_images_strict_visual_audit.csv",
    ):
        path = evidence_dir / name
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames
            rows = list(reader)
        changed = False
        for row in rows:
            if row["file_path"] == file_path:
                row[column] = str(value)
                changed = True
        if changed:
            assert fieldnames is not None
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)


def test_mutation_visual_review_confidence_rounding_boundary(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    cnn_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_copy / "results" / "clean" / "mobilenet_eval.csv"
    candidates = derive_candidate_rows(cnn_csv, mob_csv)
    file_path, candidate = next(
        (path, row)
        for path, row in candidates.items()
        if row["cnn_confidence_raw"] < 0.95
    )
    altered = candidate["cnn_confidence_raw"] + 0.004
    _mutate_split_and_combined(ev_dir, file_path, "cnn_confidence", altered)

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(ev_dir, cnn_csv, mob_csv)
    assert "rounded" in str(exc_info.value).lower()


def test_mutation_visual_review_duplicate_path(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    combined_file = ev_dir / "63_images_strict_visual_audit.csv"
    frame = pd.read_csv(combined_file, encoding="utf-8-sig", dtype=str)
    frame.loc[1, "file_path"] = frame.loc[0, "file_path"]
    frame.to_csv(combined_file, index=False, encoding="utf-8-sig")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(
            ev_dir,
            repo_copy / "results" / "clean" / "cnn_baseline_eval.csv",
            repo_copy / "results" / "clean" / "mobilenet_eval.csv",
        )
    assert "duplicate" in str(exc_info.value).lower()


def test_mutation_visual_review_extra_candidate_path(repo_copy: Path) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    combined_file = ev_dir / "63_images_strict_visual_audit.csv"
    combined = pd.read_csv(combined_file, encoding="utf-8-sig", dtype=str)
    original_path = combined.loc[0, "file_path"]
    fake_path = "DDG/not-a-canonical-candidate.jpeg"
    _mutate_split_and_combined(ev_dir, original_path, "file_path", fake_path)

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(
            ev_dir,
            repo_copy / "results" / "clean" / "cnn_baseline_eval.csv",
            repo_copy / "results" / "clean" / "mobilenet_eval.csv",
        )
    assert "discrepancy" in str(exc_info.value).lower()


@pytest.mark.parametrize("column", ["current_label", "cnn_prediction", "mnv2_prediction"])
def test_mutation_visual_review_canonical_fields(
    repo_copy: Path, column: str
) -> None:
    ev_dir = repo_copy / "results" / "audit" / "evidence"
    combined_file = ev_dir / "63_images_strict_visual_audit.csv"
    combined = pd.read_csv(combined_file, encoding="utf-8-sig", dtype=str)
    file_path = combined.loc[0, "file_path"]
    _mutate_split_and_combined(ev_dir, file_path, column, "TAMPERED")

    with pytest.raises(AuditError) as exc_info:
        audit_visual_reviews(
            ev_dir,
            repo_copy / "results" / "clean" / "cnn_baseline_eval.csv",
            repo_copy / "results" / "clean" / "mobilenet_eval.csv",
        )
    assert column in str(exc_info.value)
