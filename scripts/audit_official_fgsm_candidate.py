"""Audit an official FGSM candidate without modifying it."""

from __future__ import annotations

import json

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.official_candidate import audit_official_candidate


try:
    print(json.dumps(audit_official_candidate(), ensure_ascii=False, indent=2))
except AuditError as exc:
    raise SystemExit(f"OFFICIAL FGSM CANDIDATE AUDIT: FAILED\n{exc}") from exc
