"""Run the claim-level paper evidence audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.paper_claims import audit_paper_claims


def main() -> int:
    try:
        claims = audit_paper_claims(Path("."))
    except AuditError as exc:
        print(f"PAPER CLAIM AUDIT FAILED: {exc}", file=sys.stderr)
        return 1

    report = {
        "status": "PASSED",
        "claims": [claim.to_dict() for claim in claims],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"PAPER CLAIM AUDIT: PASSED ({len(claims)}/{len(claims)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
