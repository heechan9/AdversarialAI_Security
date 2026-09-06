from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.official_candidate import audit_official_candidate


SOURCE_SHA = "a" * 40


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    copy_dir = tmp_path / "repo"
    for item in ("configs", "results"):
        shutil.copytree(Path(item), copy_dir / item)
    return copy_dir


def _prepare_candidate(repo_copy: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = repo_copy / "results" / "attacks" / "provisional"
    candidate = repo_copy / "results" / "attacks" / "official_candidate"
    candidate.mkdir(parents=True)
    (candidate / "samples").mkdir()

    for model in ("cnn", "mobilenet"):
        shutil.copy2(source / f"fgsm_{model}.csv", candidate)
        metadata_path = source / f"fgsm_{model}_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["executed_at_utc"] = datetime.now(timezone.utc).isoformat()
        (candidate / metadata_path.name).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        for epsilon in ("0", "0.01", "0.03", "0.05"):
            stem = f"fgsm_{model}_eps_{epsilon}"
            for suffix in (
                "samples.csv",
                "report.json",
                "confusion_matrix.csv",
                "confusion_matrix.png",
            ):
                shutil.copy2(source / f"{stem}_{suffix}", candidate)

    for sample in (source / "samples").glob("*.png"):
        shutil.copy2(sample, candidate / "samples")

    cnn_meta = json.loads((candidate / "fgsm_cnn_metadata.json").read_text(encoding="utf-8"))
    context = {
        "schema_version": 1,
        "source_commit_sha": SOURCE_SHA,
        "captured_at_utc": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        "git_status_short": [],
        "python": cnn_meta["python"],
        "tensorflow": cnn_meta["tensorflow"],
        "keras": cnn_meta["keras"],
        "platform": "test-platform",
        "output_dir": "results/attacks/official_candidate",
        "epsilons": [0.0, 0.01, 0.03, 0.05],
    }
    (candidate / "official_execution_context.json").write_text(
        json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    monkeypatch.setattr(
        "adversarial_ai.audit.official_candidate.get_git_commit_sha", lambda _root: SOURCE_SHA
    )
    return candidate


def test_official_candidate_audit_passes_complete_evidence(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_candidate(repo_copy, monkeypatch)
    result = audit_official_candidate(repo_copy)
    assert result["status"] == "PASSED"
    assert result["source_commit_sha"] == SOURCE_SHA
    assert set(result["models"]) == {"cnn", "mobilenet"}


def test_official_candidate_rejects_metadata_epsilon_drift(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _prepare_candidate(repo_copy, monkeypatch)
    path = candidate / "fgsm_cnn_metadata.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["epsilons"] = [0.0, 0.01, 0.03]
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(AuditError, match="epsilon"):
        audit_official_candidate(repo_copy)


def test_official_candidate_rejects_wrong_source_commit(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _prepare_candidate(repo_copy, monkeypatch)
    path = candidate / "official_execution_context.json"
    context = json.loads(path.read_text(encoding="utf-8"))
    context["source_commit_sha"] = "b" * 40
    path.write_text(json.dumps(context), encoding="utf-8")
    with pytest.raises(AuditError, match="commit"):
        audit_official_candidate(repo_copy)


def test_official_candidate_rejects_unexpected_root_artifact(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _prepare_candidate(repo_copy, monkeypatch)
    (candidate / "stale.csv").write_text("stale", encoding="utf-8")
    with pytest.raises(AuditError, match="inventory"):
        audit_official_candidate(repo_copy)


def test_official_candidate_rejects_unexpected_root_directory(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _prepare_candidate(repo_copy, monkeypatch)
    (candidate / "stale").mkdir()
    with pytest.raises(AuditError, match="unexpected entry"):
        audit_official_candidate(repo_copy)


def test_official_candidate_rejects_symlinked_candidate_directory(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _prepare_candidate(repo_copy, monkeypatch)
    moved = candidate.with_name("candidate-target")
    candidate.rename(moved)
    try:
        candidate.symlink_to(moved, target_is_directory=True)
    except OSError:
        pytest.skip("Creating directory symlinks is not permitted on this platform")
    with pytest.raises(AuditError, match="unsafe"):
        audit_official_candidate(repo_copy)


def test_official_candidate_rejects_nested_sample_directory(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _prepare_candidate(repo_copy, monkeypatch)
    (candidate / "samples" / "nested").mkdir()
    with pytest.raises(AuditError, match="samples directory"):
        audit_official_candidate(repo_copy)


def test_official_candidate_rejects_tampered_sample_metric(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _prepare_candidate(repo_copy, monkeypatch)
    path = candidate / "fgsm_cnn_eps_0.01_samples.csv"
    frame = pd.read_csv(path)
    frame.loc[0, "linf"] = 0.05
    frame.to_csv(path, index=False)
    with pytest.raises(AuditError, match="L_infinity"):
        audit_official_candidate(repo_copy)
