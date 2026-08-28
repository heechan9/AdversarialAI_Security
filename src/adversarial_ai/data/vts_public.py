"""Validation helpers for the two VTS public-data CSV files supplied to the project."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any


VOYAGE_COLUMNS = (
    "callsgn", "ptentVtsYr", "vyg", "comCnt", "vslKornNm", "vslEngNm",
    "ptentDt", "dfptDt", "ioprtVtsType", "ioprtVtsNm", "fcltSpecCd",
    "fcltSpecSubCd", "fcltKornNm", "updtDt", "jobDt",
)
POSITION_COLUMNS = (
    "callsgn", "ptentYr", "vyg", "mmsiNo", "imoNo", "vslNm", "lot",
    "lat", "sog", "cog", "rot", "hdgAng", "drft", "nvgtStts", "updtTm",
)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: str | Path, expected_columns: tuple[str, ...]) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != expected_columns:
            raise ValueError(f"unexpected CSV schema: {reader.fieldnames}")
        return list(reader)


def _is_missing(value: str) -> bool:
    return value.strip().lower() in {"", "none", "null", "nan"}


def _validate_timestamp(value: str, field: str) -> None:
    if not _is_missing(value) and (len(value) != 14 or not value.isdigit()):
        raise ValueError(f"{field} must be YYYYMMDDhhmmss: {value!r}")


def load_voyage_events(path: str | Path) -> list[dict[str, str]]:
    rows = _read_csv(path, VOYAGE_COLUMNS)
    for row in rows:
        for field in ("ptentDt", "dfptDt", "updtDt", "jobDt"):
            _validate_timestamp(row[field], field)
    return rows


def load_positions(path: str | Path) -> list[dict[str, str]]:
    rows = _read_csv(path, POSITION_COLUMNS)
    for row in rows:
        _validate_timestamp(row["updtTm"], "updtTm")
        if not _is_missing(row["lot"]):
            longitude = float(row["lot"])
            if not -180 <= longitude <= 180:
                raise ValueError(f"longitude out of range: {longitude}")
        if not _is_missing(row["lat"]):
            latitude = float(row["lat"])
            if not -90 <= latitude <= 90:
                raise ValueError(f"latitude out of range: {latitude}")
    return rows


def validate_uploaded_vts_data(
    voyage_path: str | Path,
    position_path: str | Path,
    *,
    expected_voyage_sha256: str,
    expected_position_sha256: str,
) -> dict[str, Any]:
    """Validate immutable assets and return only descriptive, non-model metrics."""
    actual_voyage_hash = sha256_file(voyage_path)
    actual_position_hash = sha256_file(position_path)
    if actual_voyage_hash != expected_voyage_sha256:
        raise ValueError("voyage-event SHA-256 mismatch")
    if actual_position_hash != expected_position_sha256:
        raise ValueError("position SHA-256 mismatch")

    voyages = load_voyage_events(voyage_path)
    positions = load_positions(position_path)
    voyage_callsigns = {row["callsgn"] for row in voyages if row["callsgn"]}
    position_callsigns = {row["callsgn"] for row in positions if row["callsgn"]}

    return {
        "voyage_records": len(voyages),
        "position_records": len(positions),
        "voyage_event_counts": dict(Counter(row["ioprtVtsNm"] for row in voyages)),
        "navigation_status_counts": dict(Counter(row["nvgtStts"] for row in positions)),
        "callsign_intersection_count": len(voyage_callsigns & position_callsigns),
        "join_allowed": False,
    }
