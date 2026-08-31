"""Mutation tests proving that tampered evidence causes non-zero exit / AuditError."""

from __future__ import annotations

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
    df = pd.read_csv(eval_csv)
    # Tamper with predicted label of a row without updating 'correct' column
    df.loc[1, "predicted_label"] = "Tug"  # Row 1 was predicted as Aircraft Carrier (correct=True)
    df.to_csv(eval_csv, index=False)

    with pytest.raises(AuditError) as exc_info:
        audit_clean_evaluation(eval_csv, expected_model_key="cnn")
    assert "correct" in str(exc_info.value).lower() or "disagrees" in str(exc_info.value).lower()


def test_mutation_tampered_clean_accuracy_count(repo_copy: Path) -> None:
    eval_csv = repo_copy / "results" / "clean" / "cnn_baseline_eval.csv"
    df = pd.read_csv(eval_csv)
    # Invert predictions and correct values for first 10 rows
    df.loc[:9, "predicted_label"] = df.loc[:9, "true_label"]
    df.loc[:9, "correct"] = True
    df.to_csv(eval_csv, index=False)

    with pytest.raises(AuditError) as exc_info:
        audit_clean_evaluation(eval_csv, expected_model_key="cnn")
    assert "must be 504" in str(exc_info.value) or "disagrees" in str(exc_info.value)


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
    data = json.loads(manifest_p.read_text())
    data["test_files"].pop()  # 780 instead of 781
    manifest_p.write_text(json.dumps(data))

    with pytest.raises(AuditError) as exc_info:
        audit_manifest(manifest_p)
    assert "781" in str(exc_info.value)


def test_mutation_manifest_reordered_or_duplicate(repo_copy: Path) -> None:
    manifest_p = repo_copy / "configs" / "test_manifest.json"
    data = json.loads(manifest_p.read_text())
    data["test_files"][0] = data["test_files"][1]  # Create duplicate
    manifest_p.write_text(json.dumps(data))

    with pytest.raises(AuditError) as exc_info:
        audit_manifest(manifest_p)
    assert "Duplicate" in str(exc_info.value)


def test_mutation_model_sha_mismatch(repo_copy: Path) -> None:
    meta_p = repo_copy / "results" / "clean" / "cnn_baseline_metadata.json"
    meta = json.loads(meta_p.read_text())
    meta["model_sha256"] = "a" * 64
    meta_p.write_text(json.dumps(meta))

    manifest_models = {
        "models/cnn_baseline.h5": "cb256b1a5d6f605d355334e4e8667257a2bfbd29e08836cc4114869bd7068701"
    }
    with pytest.raises(AuditError) as exc_info:
        audit_models(manifest_models, [meta_p])
    assert "mismatch" in str(exc_info.value).lower()


def test_mutation_doc_claim_mismatch(repo_copy: Path) -> None:
    readme_p = repo_copy / "README.md"
    content = readme_p.read_text().replace("0.6453264951705933", "0.999999")
    readme_p.write_text(content)

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
        run_full_audit(repo_root=repo_copy)
