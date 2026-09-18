"""Audit module package entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.runner import run_full_audit


def main() -> None:
    repo_root = Path(".")
    report_path = repo_root / "results" / "audit" / "evidence_audit_report.json"
    try:
        res = run_full_audit(repo_root=repo_root, output_report_path=report_path)
        print("=" * 60)
        print(" RESEARCH EVIDENCE AUDIT: PASSED")
        print("=" * 60)
        print(f" Source Commit SHA: {res['source_commit_sha']}")
        print(f" Timestamp (UTC):   {res['timestamp_utc']}")
        print("\n Verified Scopes:")
        for scope in res["verified_scopes"]:
            print(f"   [✓] {scope}")
        if res["unverified_scopes"]:
            print("\n Unverified Scopes (Expected on clean checkout):")
            for scope in res["unverified_scopes"]:
                print(f"   [-] {scope}")
        print(f"\n Audit report written to {report_path}")
        sys.exit(0)
    except AuditError as err:
        print("=" * 60, file=sys.stderr)
        print(" RESEARCH EVIDENCE AUDIT: FAILED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f" Error: {err.message}", file=sys.stderr)
        if err.details:
            print(f" Details: {err.details}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print("=" * 60, file=sys.stderr)
        print(" RESEARCH EVIDENCE AUDIT: UNEXPECTED ERROR", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f" Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
