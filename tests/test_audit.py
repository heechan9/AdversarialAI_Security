"""Unit tests for research evidence audit on clean repository state."""

from __future__ import annotations

from pathlib import Path

from adversarial_ai.audit.clean import audit_clean_evaluation
from adversarial_ai.audit.cross_doc import audit_cross_documents
from adversarial_ai.audit.fgsm import audit_fgsm_results
from adversarial_ai.audit.manifest_models import audit_manifest, audit_models
from adversarial_ai.audit.runner import run_full_audit


def test_audit_manifest_clean_state() -> None:
    manifest_path = Path("configs/test_manifest.json")
    res = audit_manifest(manifest_path)
    assert res["test_samples"] == 781
    assert "models/cnn_baseline.h5" in res["manifest_models"]
    assert "models/mobilenet_finetuned.h5" in res["manifest_models"]


def test_audit_clean_evaluation_canonical() -> None:
    cnn_res = audit_clean_evaluation(
        Path("results/clean/cnn_baseline_eval.csv"),
        summary_json_path=Path("results/clean/cnn_baseline_summary.json"),
        expected_model_key="cnn",
    )
    assert cnn_res["correct_count"] == 504
    assert abs(cnn_res["accuracy"] - 0.645326504481434) < 1e-6

    mob_res = audit_clean_evaluation(
        Path("results/clean/mobilenet_eval.csv"),
        summary_json_path=Path("results/clean/mobilenet_summary.json"),
        expected_model_key="mobilenet",
    )
    assert mob_res["correct_count"] == 613
    assert abs(mob_res["accuracy"] - 0.7848911651728553) < 1e-6


def test_audit_fgsm_canonical() -> None:
    prov_dir = Path("results/attacks/provisional")
    cnn_fgsm = audit_fgsm_results(prov_dir, "cnn", clean_correct_count=504)
    assert cnn_fgsm[0.0]["attack_successes"] == 0
    assert cnn_fgsm[0.0]["untargeted_asr"] == 0.0
    assert cnn_fgsm[0.01]["attack_successes"] == 179
    assert cnn_fgsm[0.01]["asr_denominator"] == 504

    mob_fgsm = audit_fgsm_results(prov_dir, "mobilenet", clean_correct_count=613)
    assert mob_fgsm[0.0]["attack_successes"] == 0
    assert mob_fgsm[0.01]["attack_successes"] == 516
    assert mob_fgsm[0.01]["asr_denominator"] == 613


def test_audit_cross_doc_canonical() -> None:
    res = audit_cross_documents(
        repo_root=Path("."),
        clean_metrics={
            "cnn": {"correct_count": 504},
            "mobilenet": {"correct_count": 613},
        },
    )
    assert res["provenance_verified"] is True
    assert res["readme_claims_verified"] is True


def test_run_full_audit_canonical(tmp_path: Path) -> None:
    out_report = tmp_path / "report.json"
    res = run_full_audit(repo_root=Path("."), output_report_path=out_report)
    assert res["status"] == "PASSED"
    assert out_report.is_file()
