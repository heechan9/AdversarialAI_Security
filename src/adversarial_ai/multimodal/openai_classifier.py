"""Phase 1 OpenAI Responses API PoC for single-image ship classification.

Design notes:
- The API key is read only from the OPENAI_API_KEY environment variable.
  It is never hardcoded, printed, or included in any exception message,
  log line, result record, or exception traceback (all raises use
  ``from None`` to suppress chaining of the original exception, which
  could otherwise carry the raw key text into a traceback).
- build_request() has no parameters for ground truth or clean/adversarial
  condition. Those are never sent to the model -- there is nothing in the
  function signature that could leak them, by construction. The caller
  (an evaluation harness) adds ground truth / condition to the recorded
  result only AFTER the API call returns, for local analysis only, and
  both are validated against known values before being written.
- ``store: False`` is set explicitly so the response is not retained as
  application state for later retrieval. This does not by itself imply
  Zero Data Retention; separate OpenAI abuse-monitoring retention
  policies may still apply.
- Only PNG/JPEG inputs are supported, and content is actually decoded and
  verified with Pillow (not just extension-checked), including a check
  that the decoded format matches the extension (rejects extension
  spoofing), plus explicit file-size and pixel-count caps.
- Every terminal, non-"completed" response status (failed, cancelled,
  incomplete) and non-terminal status (queued, in_progress) is handled
  explicitly, and a refusal nested inside a "message" output item's
  content list (the real Responses API shape) is detected -- not just a
  flat top-level "refusal" item.
- Results store a caller-supplied relative path (validated to reject
  absolute paths and ".." components, in both build_error_record() and
  classify_image()) or, if none is given, just the filename -- never the
  absolute filesystem path.
- Failures are raised as ClassificationError with a specific error_type,
  and can be converted to a JSONL-recordable dict via
  build_error_record() so they are never silently dropped by a batch
  runner.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

from adversarial_ai.multimodal.schema import PERCEPTION_SCHEMA, SHIP_CLASSES

# Pinned to a dated snapshot rather than a rolling alias, for reproducibility.
DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"
DEFAULT_MAX_OUTPUT_TOKENS = 500
DEFAULT_TIMEOUT_SECONDS = 60.0
IMAGE_DETAIL = "high"

# Resource caps: reject anything larger before it is even base64-encoded
# or sent, both to bound API cost and to avoid pathological memory use.
# CONFIRMED (not proposed) based on measuring all 781 images in the
# project's fixed test manifest on 2026-08-12: max file size was
# 2,906,627 bytes and max resolution was 6487x4327 (28,069,249 pixels).
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # ~3.6x headroom over the measured max
MAX_IMAGE_PIXELS = 40_000_000  # ~1.42x headroom over the measured max

_SUPPORTED_EXTENSIONS = {
    ".png": ("image/png", "PNG"),
    ".jpg": ("image/jpeg", "JPEG"),
    ".jpeg": ("image/jpeg", "JPEG"),
}

_VALID_CONDITIONS = ("clean", "adversarial")
_VALID_ATTACK_NAMES = ("fgsm", "bim", "pgd")

SYSTEM_PROMPT = (
    "You are a ship-image classifier for a maritime research project. "
    "Classify the ship in the image into exactly one of the given classes. "
    "Respond only with the requested structured fields."
)

USER_PROMPT_TEMPLATE = (
    "Classify the ship shown in the image into exactly one of these "
    "classes: {classes}. Provide a short reason, whether you are "
    "uncertain, whether the image shows signs of adversarial tampering, "
    "and your own self-assessed confidence score."
).format(classes=", ".join(SHIP_CLASSES))

_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{10,}")

# response.status values that mean the call is not usably complete.
_TERMINAL_FAILURE_STATUSES = ("failed", "cancelled")
_NON_TERMINAL_STATUSES = ("queued", "in_progress")


def _sanitize(message: str) -> str:
    """Strip anything matching an OpenAI-style API key from a string
    before it is raised, logged, or recorded anywhere."""
    return _KEY_PATTERN.sub("sk-***REDACTED***", message)


def _prompt_schema_hash() -> str:
    """Short stable hash of the prompts + schema, so results can be tied
    back to exactly which prompt/schema version produced them."""
    payload = json.dumps(
        {"system": SYSTEM_PROMPT, "user": USER_PROMPT_TEMPLATE, "schema": PERCEPTION_SCHEMA},
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


PROMPT_SCHEMA_HASH = _prompt_schema_hash()


class ClassificationError(RuntimeError):
    """Raised for any failure that happens after an API call was attempted
    (or that is response-shape related). Carries enough structured info
    (error_type, response_id, latency) to build a recordable result via
    build_error_record(), so failures are never silently dropped."""

    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        response_id: str | None = None,
        latency_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.response_id = response_id
        self.latency_seconds = latency_seconds


class _ResponseIssue(Exception):
    """Internal-only signal for a specific response-shape problem, before
    it is converted into a ClassificationError with response_id/latency
    attached by the caller."""

    def __init__(self, message: str, error_type: str) -> None:
        super().__init__(message)
        self.error_type = error_type


def get_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)


def get_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Set it (e.g. in a local .env file, never committed) before "
            "running the OpenAI PoC."
        )
    return api_key


def get_client():
    """Build an OpenAI client. Checks for the API key BEFORE importing the
    openai package, so callers that only need to know whether a key is
    configured don't need the package installed. A client-level timeout
    is set explicitly for reproducible failure behavior."""
    api_key = get_api_key()
    from openai import OpenAI

    return OpenAI(api_key=api_key, timeout=DEFAULT_TIMEOUT_SECONDS)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _PixelLimitExceeded(Exception):
    """Internal-only signal so a pixel-limit violation is reported with
    its own clear message, distinct from a generic decode failure."""

    def __init__(self, width: int, height: int, pixel_count: int) -> None:
        super().__init__(f"{width}x{height} ({pixel_count} pixels)")
        self.width = width
        self.height = height
        self.pixel_count = pixel_count


def _validate_image_content(path: Path, expected_format: str) -> None:
    """Actually decode the image with Pillow (not just check the
    extension), confirm the decoded format matches the extension (rejects
    extension spoofing), and enforce file-size / pixel-count caps.

    The pixel-count check runs BEFORE img.verify() (not after), so an
    oversized image is rejected without paying the cost of a full
    decode/verify pass.

    NOTE: MAX_IMAGE_BYTES and MAX_IMAGE_PIXELS are confirmed values,
    measured against the actual 781-image project dataset (see the
    constants' comments above for the measured max and the headroom
    applied) -- not placeholder guesses.
    """
    file_size = path.stat().st_size
    if file_size > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image file too large: {file_size} bytes exceeds the "
            f"{MAX_IMAGE_BYTES}-byte limit"
        )

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(path) as img:
            actual_format = img.format
            width, height = img.size
            pixel_count = width * height
            if pixel_count > MAX_IMAGE_PIXELS:
                raise _PixelLimitExceeded(width, height, pixel_count)
            img.verify()
    except _PixelLimitExceeded as exc:
        raise ValueError(
            f"Image resolution too large: {exc.width}x{exc.height} "
            f"({exc.pixel_count} pixels) exceeds the {MAX_IMAGE_PIXELS}-pixel "
            "limit"
        ) from None
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError(f"File is not a valid image: {_sanitize(str(exc))}") from None

    if actual_format != expected_format:
        raise ValueError(
            f"Image content format {actual_format!r} does not match its "
            f"extension (expected {expected_format!r}) -- possible "
            "extension spoofing"
        )


def _encode_image(path: Path) -> tuple[str, str]:
    """Return (data_url, sha256). Raises ValueError for unsupported
    extensions, corrupted content, format/extension mismatches, or
    resource limits being exceeded."""
    ext = path.suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported image extension {ext!r}. Supported: "
            f"{sorted(_SUPPORTED_EXTENSIONS)}"
        )
    mime, expected_format = _SUPPORTED_EXTENSIONS[ext]
    _validate_image_content(path, expected_format)

    sha256 = _sha256_file(path)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}", sha256


def _validate_relative_path(relative_path: str) -> None:
    """Reject absolute paths (POSIX or Windows-style) and '..' traversal,
    regardless of which OS this code happens to run on. Called from both
    classify_image() and build_error_record() independently, since the
    latter can be invoked directly by a batch harness without going
    through classify_image() first."""
    import ntpath
    import posixpath

    if posixpath.isabs(relative_path) or ntpath.isabs(relative_path):
        raise ValueError(f"relative_path must not be absolute: {relative_path!r}")
    drive, _tail = ntpath.splitdrive(relative_path)
    if drive:
        raise ValueError(
            f"relative_path must not include a drive letter (Windows "
            f"drive-relative paths like 'C:ship.png' are rejected too): "
            f"{relative_path!r}"
        )
    normalized = relative_path.replace("\\", "/")
    if ".." in normalized.split("/"):
        raise ValueError(f"relative_path must not contain '..': {relative_path!r}")


def build_request(image_path: str | Path, *, model: str | None = None) -> tuple[dict[str, Any], str]:
    """Build a Responses API request for one image.

    Returns (request_dict, image_sha256). This function intentionally has
    no ground_truth or condition parameter -- nothing about the true label
    or clean/adversarial status can be sent to the API through this path.
    ``store`` is explicitly False so the response is not persisted as
    application state for later retrieval.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path.name}")
    data_url, sha256 = _encode_image(path)

    request = {
        "model": model or get_model(),
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": USER_PROMPT_TEMPLATE},
                    {"type": "input_image", "image_url": data_url, "detail": IMAGE_DETAIL},
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "ship_perception",
                "schema": PERCEPTION_SCHEMA,
                "strict": True,
            }
        },
        "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
        "store": False,
    }
    return request, sha256


def _validate_output(parsed: dict) -> None:
    required = PERCEPTION_SCHEMA["required"]
    missing = [k for k in required if k not in parsed]
    if missing:
        raise ValueError(f"Response missing required fields: {missing}")
    extra = set(parsed) - set(PERCEPTION_SCHEMA["properties"])
    if extra:
        raise ValueError(f"Response has unexpected fields: {sorted(extra)}")
    if parsed["predicted_class"] not in SHIP_CLASSES:
        raise ValueError(
            f"predicted_class not in allowed enum: {parsed['predicted_class']!r}"
        )
    confidence = parsed["self_reported_confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError(f"self_reported_confidence must be numeric: {confidence!r}")
    if not (0 <= confidence <= 1):
        raise ValueError(f"self_reported_confidence out of range [0, 1]: {confidence!r}")
    if not isinstance(parsed["uncertain"], bool):
        raise ValueError("uncertain must be a boolean")
    if not isinstance(parsed["attack_suspected"], bool):
        raise ValueError("attack_suspected must be a boolean")
    if not isinstance(parsed["reason"], str):
        raise ValueError("reason must be a string")


def _find_nested_refusal(response: Any) -> str | None:
    """Look for a refusal in the REAL Responses API shape: a top-level
    output item of type "message" whose .content list contains a part of
    type "refusal". Also tolerates a flatter top-level "refusal" item, in
    case a different SDK version exposes it that way. Returns the refusal
    text if found, else None."""
    for item in getattr(response, "output", None) or []:
        item_type = getattr(item, "type", None)
        if item_type == "message":
            for part in getattr(item, "content", None) or []:
                if getattr(part, "type", None) == "refusal":
                    return getattr(part, "refusal", None) or "no reason given"
        elif item_type == "refusal":
            return getattr(item, "refusal", None) or "no reason given"
    return None


def _extract_text(response: Any) -> str:
    """Distinguish every non-"completed" status, a (possibly nested)
    refusal, and empty output from normal text output, before anything is
    passed to json.loads()."""
    status = getattr(response, "status", None)

    if status in _TERMINAL_FAILURE_STATUSES:
        error_obj = getattr(response, "error", None)
        error_msg = getattr(error_obj, "message", None) if error_obj is not None else None
        detail = f": {_sanitize(error_msg)}" if error_msg else ""
        raise _ResponseIssue(f"OpenAI response status={status}{detail}", status)
    if status in _NON_TERMINAL_STATUSES:
        raise _ResponseIssue(
            f"OpenAI response not yet completed (status={status})", "not_completed"
        )
    if status == "incomplete":
        raise _ResponseIssue(
            "OpenAI response is incomplete (status=incomplete)", "incomplete"
        )
    if status is None or status != "completed":
        raise _ResponseIssue(f"Unexpected OpenAI response status: {status!r}", "unexpected_status")

    refusal_text = _find_nested_refusal(response)
    if refusal_text is not None:
        raise _ResponseIssue(f"OpenAI refused to respond: {refusal_text}", "refusal")

    text = getattr(response, "output_text", None)
    if not text:
        raise _ResponseIssue("OpenAI response contained no output_text", "empty_output")
    return text


def _now_utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def classify_image(
    image_path: str | Path,
    *,
    relative_path: str | None = None,
    client: Any | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Run one classification call and return a result record.

    Raises ClassificationError (never a bare/chained exception carrying
    the original traceback) for any failure after the API call is
    attempted; see build_error_record() to convert that into a
    JSONL-recordable dict.
    """
    path = Path(image_path)
    if relative_path is not None:
        _validate_relative_path(relative_path)
    display_path = relative_path or path.name

    request, sha256 = build_request(path, model=model)
    requested_model = request["model"]

    if client is None:
        client = get_client()

    start = time.monotonic()
    try:
        response = client.responses.create(**request)
    except Exception as exc:
        latency = time.monotonic() - start
        raise ClassificationError(
            f"OpenAI API call failed: {_sanitize(str(exc))}",
            error_type="api_error",
            latency_seconds=latency,
        ) from None
    latency = time.monotonic() - start
    response_id = getattr(response, "id", None)
    response_model = getattr(response, "model", None)

    try:
        text = _extract_text(response)
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise _ResponseIssue(
                f"Top-level JSON was {type(parsed).__name__}, not an object",
                "invalid_top_level",
            )
        _validate_output(parsed)
    except _ResponseIssue as exc:
        raise ClassificationError(
            _sanitize(str(exc)), error_type=exc.error_type,
            response_id=response_id, latency_seconds=latency,
        ) from None
    except json.JSONDecodeError as exc:
        raise ClassificationError(
            f"Response was not valid JSON: {_sanitize(str(exc))}",
            error_type="invalid_json",
            response_id=response_id, latency_seconds=latency,
        ) from None
    except ValueError as exc:
        raise ClassificationError(
            _sanitize(str(exc)), error_type="schema_validation",
            response_id=response_id, latency_seconds=latency,
        ) from None

    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "input_tokens", None) if usage is not None else None
    output_tokens = getattr(usage, "output_tokens", None) if usage is not None else None

    return {
        "relative_image_path": display_path,
        "image_sha256": sha256,
        "requested_model": requested_model,
        "response_model": response_model,
        "prompt_schema_hash": PROMPT_SCHEMA_HASH,
        "image_detail": IMAGE_DETAIL,
        "predicted_class": parsed["predicted_class"],
        "reason": parsed["reason"],
        "uncertain": parsed["uncertain"],
        "attack_suspected": parsed["attack_suspected"],
        "self_reported_confidence": parsed["self_reported_confidence"],
        "response_id": response_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_seconds": latency,
        "executed_at_utc": _now_utc_iso(),
        "status": "success",
        "error_type": None,
        "error_message": None,
    }


def build_error_record(
    image_path: str | Path,
    exc: ClassificationError,
    *,
    relative_path: str | None = None,
    model: str | None = None,
    image_sha256: str | None = None,
) -> dict[str, Any]:
    """Convert a ClassificationError into a JSONL-recordable dict with the
    same shape as a success record, so failures show up in results
    instead of disappearing. Validates ``relative_path`` independently of
    classify_image(), since this can be called directly by a batch
    harness without going through classify_image() first."""
    if relative_path is not None:
        _validate_relative_path(relative_path)
    path = Path(image_path)
    return {
        "relative_image_path": relative_path or path.name,
        "image_sha256": image_sha256,
        "requested_model": model or get_model(),
        "response_model": None,
        "prompt_schema_hash": PROMPT_SCHEMA_HASH,
        "image_detail": IMAGE_DETAIL,
        "predicted_class": None,
        "reason": None,
        "uncertain": None,
        "attack_suspected": None,
        "self_reported_confidence": None,
        "response_id": exc.response_id,
        "input_tokens": None,
        "output_tokens": None,
        "latency_seconds": exc.latency_seconds,
        "executed_at_utc": _now_utc_iso(),
        "status": "error",
        "error_type": exc.error_type,
        "error_message": _sanitize(str(exc)),
    }


def record_result(
    result: dict[str, Any],
    *,
    ground_truth: str,
    condition: str,
    attack_name: str | None = None,
    epsilon: float | None = None,
    output_path: str | Path,
) -> None:
    """Merge ground truth and clean/adversarial condition into a result
    record for LOCAL analysis only, then append it as one JSON line.

    ``attack_name`` and ``epsilon`` let local analysis distinguish which
    attack (fgsm/bim/pgd) and which perturbation budget produced an
    adversarial sample -- required when condition="adversarial", and
    required to be None when condition="clean". None of these four
    values (ground_truth, condition, attack_name, epsilon) are ever part
    of the request sent to the API (see build_request, which has no
    parameters for any of them) -- they are added here, strictly after
    the API call has already returned or failed.
    """
    if ground_truth not in SHIP_CLASSES:
        raise ValueError(f"ground_truth must be one of {SHIP_CLASSES}: {ground_truth!r}")
    if condition not in _VALID_CONDITIONS:
        raise ValueError(f"condition must be one of {_VALID_CONDITIONS}: {condition!r}")

    if condition == "clean":
        if attack_name is not None or epsilon is not None:
            raise ValueError(
                "attack_name and epsilon must both be None when condition='clean'"
            )
    else:  # condition == "adversarial"
        if attack_name not in _VALID_ATTACK_NAMES:
            raise ValueError(
                f"attack_name must be one of {_VALID_ATTACK_NAMES} when "
                f"condition='adversarial': {attack_name!r}"
            )
        if (
            epsilon is None
            or isinstance(epsilon, bool)
            or not isinstance(epsilon, (int, float))
            or not math.isfinite(epsilon)
            or epsilon < 0
        ):
            raise ValueError(
                "epsilon must be a finite number >= 0 when "
                f"condition='adversarial': {epsilon!r}"
            )

    record = dict(result)
    record["ground_truth"] = ground_truth
    record["condition"] = condition
    record["attack_name"] = attack_name
    record["epsilon"] = epsilon
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
