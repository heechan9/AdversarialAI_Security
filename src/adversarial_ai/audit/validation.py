"""Shared fail-closed validation helpers for audit evidence."""

from __future__ import annotations

import math
import re
from pathlib import PurePosixPath
from typing import Any, Iterable

from adversarial_ai.audit.exceptions import AuditError


def normalize_relative_path(value: Any, context: str) -> str:
    """Return a normalized POSIX path that cannot escape its evidence root."""
    if not isinstance(value, str) or not value.strip():
        raise AuditError(f"{context} must be a non-empty relative path")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        "\x00" in normalized
        or re.match(r"^[A-Za-z]:", normalized)
        or path.is_absolute()
        or path.drive
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise AuditError(f"{context} must not be absolute or escape its evidence root")
    return path.as_posix()


def parse_strict_booleans(values: Iterable[Any], context: str) -> list[bool]:
    """Parse only explicit true/false tokens instead of truthy string coercion."""
    parsed: list[bool] = []
    for index, value in enumerate(values):
        token = str(value).strip().lower()
        if token == "true":
            parsed.append(True)
        elif token == "false":
            parsed.append(False)
        else:
            raise AuditError(
                f"{context}[{index}] must be an explicit True or False value"
            )
    return parsed


def parse_finite_numbers(
    values: Iterable[Any],
    context: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> list[float]:
    """Parse finite numbers and optionally enforce inclusive bounds."""
    parsed: list[float] = []
    for index, value in enumerate(values):
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise AuditError(f"{context}[{index}] must be numeric") from exc
        if not math.isfinite(number):
            raise AuditError(f"{context}[{index}] must be finite")
        if minimum is not None and number < minimum:
            raise AuditError(f"{context}[{index}] must be >= {minimum}")
        if maximum is not None and number > maximum:
            raise AuditError(f"{context}[{index}] must be <= {maximum}")
        parsed.append(number)
    return parsed


def require_nonempty_strings(values: Iterable[Any], context: str) -> list[str]:
    """Reject missing, non-string, or whitespace-only string evidence values."""
    parsed: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise AuditError(f"{context}[{index}] must be a non-empty string")
        parsed.append(value)
    return parsed
