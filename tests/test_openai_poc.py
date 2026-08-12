"""Mock-only unit tests for the Phase 1 OpenAI classification PoC.

No real API calls are made anywhere in this file. All OpenAI interaction
is stubbed with a fake client whose .responses.create() returns a
pre-built fake response object.
"""

from __future__ import annotations

import inspect
import json
import traceback

import httpx
import pytest
from PIL import Image

from adversarial_ai.multimodal import openai_classifier as oc
from adversarial_ai.multimodal.openai_classifier import (
    ClassificationError,
    build_error_record,
    build_request,
    classify_image,
    get_api_key,
    get_client,
    record_result,
)
from adversarial_ai.multimodal.schema import PERCEPTION_SCHEMA, SHIP_CLASSES


def _assemble_fake_key() -> str:
    """Build an sk-shaped string at runtime (not as a source-code literal)
    so secret scanners don't flag this test file as containing a real key."""
    parts = ["sk", "proj", "RUNTIMEASSEMBLEDFAKEKEYNEVERREAL0123456789"]
    return "-".join(parts)


class _FakeUsage:
    def __init__(self, input_tokens=100, output_tokens=20):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeContentPart:
    """One item in a "message" output item's .content list -- the real
    nested shape refusals actually appear in."""

    def __init__(self, type_, refusal=None, text=None):
        self.type = type_
        self.refusal = refusal
        self.text = text


class _FakeMessageItem:
    def __init__(self, content):
        self.type = "message"
        self.content = content


class _FakeFlatRefusalItem:
    """A flatter, non-nested refusal shape, tolerated as a fallback."""

    def __init__(self, refusal):
        self.type = "refusal"
        self.refusal = refusal


class _FakeError:
    def __init__(self, message):
        self.message = message


class _FakeResponse:
    def __init__(
        self,
        payload=None,
        response_id="resp_fake_001",
        usage=None,
        status="completed",
        output=None,
        output_text_override=None,
        model="gpt-4o-mini-2024-07-18",
        error=None,
    ):
        if output_text_override is not None:
            self.output_text = output_text_override
        elif payload is not None:
            self.output_text = json.dumps(payload)
        else:
            self.output_text = ""
        self.id = response_id
        self.usage = usage or _FakeUsage()
        self.status = status
        self.output = output or []
        self.model = model
        self.error = error


class _FakeResponses:
    def __init__(self, response=None, exception=None):
        self._response = response
        self._exception = exception
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._exception is not None:
            raise self._exception
        return self._response


class _FakeClient:
    def __init__(self, response=None, exception=None):
        self.responses = _FakeResponses(response=response, exception=exception)


def _valid_payload(**overrides):
    payload = {
        "predicted_class": "Aircraft Carrier",
        "reason": "Large flat deck with aircraft visible.",
        "uncertain": False,
        "attack_suspected": False,
        "self_reported_confidence": 0.87,
    }
    payload.update(overrides)
    return payload


def _make_real_image(tmp_path, name="ship.png", size=(4, 4), color=(120, 120, 130)):
    """Create an actual valid PNG or JPEG (format inferred from the
    extension), not placeholder bytes -- content validation now really
    decodes the file."""
    path = tmp_path / name
    ext = path.suffix.lower()
    fmt = "PNG" if ext == ".png" else "JPEG"
    img = Image.new("RGB", size, color=color)
    img.save(path, format=fmt)
    return path


def _make_corrupted_image(tmp_path, name="broken.png"):
    path = tmp_path / name
    path.write_bytes(b"not a real image, just garbage bytes 1234567890")
    return path


def _make_spoofed_image(tmp_path):
    """Real JPEG bytes saved under a .png extension -- extension spoofing."""
    path = tmp_path / "spoofed.png"
    img = Image.new("RGB", (4, 4), color=(10, 20, 30))
    img.save(path, format="JPEG")
    return path


# ---------------------------------------------------------------------
# 1. API Key 누락 시 명확한 오류
# ---------------------------------------------------------------------
def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_api_key()
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_client()


# ---------------------------------------------------------------------
# 2. PNG/JPEG 입력 처리 (실제 디코딩 검증 포함)
# ---------------------------------------------------------------------
@pytest.mark.parametrize("filename", ["ship.png", "ship.jpg", "ship.jpeg", "SHIP.PNG"])
def test_supported_extensions_accepted(tmp_path, filename):
    image = _make_real_image(tmp_path, name=filename)
    request, sha256 = build_request(image)
    assert request["model"]
    assert len(sha256) == 64


# 3. 지원하지 않는 확장자 거부
@pytest.mark.parametrize("filename", ["ship.gif", "ship.bmp", "ship.webp", "ship.txt"])
def test_unsupported_extension_rejected(tmp_path, filename):
    path = tmp_path / filename
    path.write_bytes(b"irrelevant content, extension check happens first")
    with pytest.raises(ValueError, match="Unsupported image extension"):
        build_request(path)


def test_corrupted_image_content_rejected(tmp_path):
    image = _make_corrupted_image(tmp_path)
    with pytest.raises(ValueError, match="not a valid image"):
        build_request(image)


def test_extension_spoofed_image_rejected(tmp_path):
    image = _make_spoofed_image(tmp_path)
    with pytest.raises(ValueError, match="extension spoofing"):
        build_request(image)


# 이미지 자원 상한 (바이트 / 픽셀)
def test_oversized_file_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "MAX_IMAGE_BYTES", 100)  # force a tiny cap
    image = _make_real_image(tmp_path, size=(50, 50))
    assert image.stat().st_size > 100
    with pytest.raises(ValueError, match="too large"):
        build_request(image)


def test_oversized_pixel_count_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "MAX_IMAGE_PIXELS", 100)  # force a tiny cap
    image = _make_real_image(tmp_path, size=(20, 20))  # 400 pixels > 100
    with pytest.raises(ValueError, match="resolution too large"):
        build_request(image)


# 4. 이미지 SHA-256 기록
def test_image_sha256_recorded_correctly(tmp_path):
    import hashlib

    image = _make_real_image(tmp_path)
    _, sha256 = build_request(image)
    assert sha256 == hashlib.sha256(image.read_bytes()).hexdigest()


# 5. JSON Schema 검증 (well-formed payload passes)
def test_valid_payload_passes_through_classify(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    result = classify_image(image, client=fake_client)
    assert result["predicted_class"] == "Aircraft Carrier"
    assert result["status"] == "success"
    assert result["error_type"] is None


# 6. enum 이외 클래스 거부
def test_invalid_predicted_class_rejected(tmp_path):
    image = _make_real_image(tmp_path)
    bad_payload = _valid_payload(predicted_class="Yacht")
    fake_client = _FakeClient(response=_FakeResponse(bad_payload))
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "schema_validation"


def test_predicted_class_key_shaped_value_sanitized(tmp_path):
    # predicted_class comes straight from the API response -- if a
    # malformed/malicious response put a key-shaped string there, it must
    # not leak into the exception message or traceback.
    image = _make_real_image(tmp_path)
    fake_key = _assemble_fake_key()
    bad_payload = _valid_payload(predicted_class=fake_key)
    fake_client = _FakeClient(response=_FakeResponse(bad_payload))
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "schema_validation"
    assert fake_key not in str(excinfo.value)
    assert "REDACTED" in str(excinfo.value)
    assert fake_key not in traceback.format_exc()


def test_unexpected_field_name_key_shaped_value_sanitized(tmp_path):
    # An unexpected top-level field name is also API-response-derived
    # content and must be sanitized the same way.
    image = _make_real_image(tmp_path)
    fake_key = _assemble_fake_key()
    bad_payload = _valid_payload()
    bad_payload[fake_key] = "unexpected extra field"
    fake_client = _FakeClient(response=_FakeResponse(bad_payload))
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "schema_validation"
    assert fake_key not in str(excinfo.value)
    assert "REDACTED" in str(excinfo.value)
    assert fake_key not in traceback.format_exc()


# 7. confidence 범위 검증
@pytest.mark.parametrize("bad_confidence", [-0.1, 1.1, 2.0, True, False])
def test_confidence_out_of_range_rejected(tmp_path, bad_confidence):
    image = _make_real_image(tmp_path)
    bad_payload = _valid_payload(self_reported_confidence=bad_confidence)
    fake_client = _FakeClient(response=_FakeResponse(bad_payload))
    with pytest.raises(ClassificationError):
        classify_image(image, client=fake_client)


# 8. 누락 필드 거부
@pytest.mark.parametrize("missing_field", list(PERCEPTION_SCHEMA["required"]))
def test_missing_required_field_rejected(tmp_path, missing_field):
    image = _make_real_image(tmp_path)
    payload = _valid_payload()
    del payload[missing_field]
    fake_client = _FakeClient(response=_FakeResponse(payload))
    with pytest.raises(ClassificationError, match="missing required fields"):
        classify_image(image, client=fake_client)


# ---------------------------------------------------------------------
# 9. 절대경로 미저장 + 경로 검증 (classify_image와 build_error_record 둘 다)
# ---------------------------------------------------------------------
def test_absolute_path_not_stored_in_result(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))

    result = classify_image(image, client=fake_client)
    assert str(tmp_path) not in result["relative_image_path"]
    assert result["relative_image_path"] == image.name

    result2 = classify_image(
        image, client=fake_client, relative_path="Aircraft Carrier/ship.png"
    )
    assert str(tmp_path) not in result2["relative_image_path"]
    assert result2["relative_image_path"] == "Aircraft Carrier/ship.png"


_BAD_RELATIVE_PATHS = [
    "C:\\Users\\hc247\\ship.png",
    "C:/Users/hc247/ship.png",
    "/home/hc247/ship.png",
    "../../etc/passwd",
    "Aircraft Carrier/../../secret.png",
    "C:ship.png",  # Windows drive-relative path -- ntpath.isabs() alone misses this
]


@pytest.mark.parametrize("bad_relative_path", _BAD_RELATIVE_PATHS)
def test_absolute_or_traversal_relative_path_rejected_in_classify(tmp_path, bad_relative_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    with pytest.raises(ValueError):
        classify_image(image, client=fake_client, relative_path=bad_relative_path)


@pytest.mark.parametrize("bad_relative_path", _BAD_RELATIVE_PATHS)
def test_absolute_or_traversal_relative_path_rejected_in_error_record(tmp_path, bad_relative_path):
    # build_error_record() must validate independently -- a batch harness
    # could call it directly without ever going through classify_image().
    image = _make_real_image(tmp_path)
    exc = ClassificationError("boom", error_type="api_error", latency_seconds=0.1)
    with pytest.raises(ValueError):
        build_error_record(image, exc, relative_path=bad_relative_path)


# ---------------------------------------------------------------------
# 10. API Key가 로그·결과·traceback에 포함되지 않음
# ---------------------------------------------------------------------
def test_api_key_never_appears_in_error_or_result(tmp_path):
    image = _make_real_image(tmp_path)
    fake_key = _assemble_fake_key()
    fake_client = _FakeClient(exception=RuntimeError(f"auth failed for key {fake_key}"))

    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert fake_key not in str(excinfo.value)
    assert "REDACTED" in str(excinfo.value)
    assert excinfo.value.error_type == "api_error"

    fake_client_ok = _FakeClient(response=_FakeResponse(_valid_payload()))
    result = classify_image(image, client=fake_client_ok)
    assert "sk-" not in json.dumps(result)


def test_api_key_never_appears_in_traceback(tmp_path):
    image = _make_real_image(tmp_path)
    fake_key = _assemble_fake_key()
    fake_client = _FakeClient(exception=RuntimeError(f"auth failed for key {fake_key}"))

    try:
        classify_image(image, client=fake_client)
    except ClassificationError:
        tb_text = traceback.format_exc()
        assert fake_key not in tb_text
    else:
        pytest.fail("expected ClassificationError to be raised")


# ---------------------------------------------------------------------
# 11. API 오류·timeout·rate limit 처리
# ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "exc",
    [
        TimeoutError("request timed out"),
        RuntimeError("rate limit exceeded"),
        ConnectionError("connection reset"),
    ],
)
def test_api_errors_wrapped_as_classification_error(tmp_path, exc):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(exception=exc)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "api_error"
    assert excinfo.value.latency_seconds is not None


# ---------------------------------------------------------------------
# 2번(재지적) 항목: 전체 response.status 값 + 중첩 refusal 구조
# ---------------------------------------------------------------------
def test_incomplete_response_status_detected(tmp_path):
    image = _make_real_image(tmp_path)
    response = _FakeResponse(payload=_valid_payload(), status="incomplete")
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "incomplete"
    assert excinfo.value.response_id == "resp_fake_001"


@pytest.mark.parametrize("status", ["failed", "cancelled"])
def test_terminal_failure_statuses_detected(tmp_path, status):
    image = _make_real_image(tmp_path)
    response = _FakeResponse(status=status, error=_FakeError("something went wrong"))
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == status
    assert "something went wrong" in str(excinfo.value)


def test_failed_status_error_message_is_sanitized(tmp_path):
    image = _make_real_image(tmp_path)
    fake_key = _assemble_fake_key()
    response = _FakeResponse(status="failed", error=_FakeError(f"auth error, key={fake_key}"))
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert fake_key not in str(excinfo.value)


@pytest.mark.parametrize("status", ["queued", "in_progress"])
def test_non_terminal_statuses_detected(tmp_path, status):
    image = _make_real_image(tmp_path)
    response = _FakeResponse(payload=_valid_payload(), status=status)
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "not_completed"


def test_unexpected_status_value_detected(tmp_path):
    image = _make_real_image(tmp_path)
    response = _FakeResponse(payload=_valid_payload(), status="some_future_status")
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "unexpected_status"


def test_unexpected_status_message_is_sanitized(tmp_path):
    image = _make_real_image(tmp_path)
    fake_key = _assemble_fake_key()
    response = _FakeResponse(payload=_valid_payload(), status=f"weird_status_{fake_key}")
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert fake_key not in str(excinfo.value)
    assert "REDACTED" in str(excinfo.value)
    assert fake_key not in traceback.format_exc()


def test_none_status_treated_as_unexpected(tmp_path):
    # A missing/None status must not be treated as an implicit success --
    # with a pinned SDK version, status should always be present and
    # equal to "completed" for a usable synchronous response.
    image = _make_real_image(tmp_path)
    response = _FakeResponse(payload=_valid_payload(), status=None)
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "unexpected_status"


def test_nested_refusal_in_message_content_detected(tmp_path):
    # The real Responses API shape: a "message" output item whose
    # .content list contains a part of type "refusal" -- not a flat
    # top-level "refusal" item.
    image = _make_real_image(tmp_path)
    response = _FakeResponse(
        output_text_override="",
        output=[_FakeMessageItem(content=[_FakeContentPart("refusal", refusal="cannot help with that")])],
    )
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "refusal"
    assert "cannot help with that" in str(excinfo.value)


def test_refusal_message_is_sanitized(tmp_path):
    image = _make_real_image(tmp_path)
    fake_key = _assemble_fake_key()
    response = _FakeResponse(
        output_text_override="",
        output=[_FakeMessageItem(content=[_FakeContentPart("refusal", refusal=f"blocked, key={fake_key}")])],
    )
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert fake_key not in str(excinfo.value)
    assert "REDACTED" in str(excinfo.value)
    assert fake_key not in traceback.format_exc()


def test_flat_refusal_item_still_tolerated(tmp_path):
    # Fallback shape, in case a different SDK version exposes refusal
    # directly at the top level instead of nested in a message.
    image = _make_real_image(tmp_path)
    response = _FakeResponse(
        output_text_override="",
        output=[_FakeFlatRefusalItem(refusal="policy violation")],
    )
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "refusal"


def test_empty_output_text_detected(tmp_path):
    image = _make_real_image(tmp_path)
    response = _FakeResponse(output_text_override="")
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "empty_output"


def test_invalid_json_output_detected(tmp_path):
    image = _make_real_image(tmp_path)
    response = _FakeResponse(output_text_override="{not valid json")
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "invalid_json"


@pytest.mark.parametrize(
    "bad_top_level", [json.dumps([1, 2, 3]), json.dumps(42), json.dumps("just a string")]
)
def test_non_object_top_level_json_detected(tmp_path, bad_top_level):
    image = _make_real_image(tmp_path)
    response = _FakeResponse(output_text_override=bad_top_level)
    fake_client = _FakeClient(response=response)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)
    assert excinfo.value.error_type == "invalid_top_level"


# ---------------------------------------------------------------------
# 실패도 JSONL에 기록 가능해야 함
# ---------------------------------------------------------------------
def test_build_error_record_and_record_result_capture_failures(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(exception=TimeoutError("request timed out"))

    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=fake_client)

    error_record = build_error_record(image, excinfo.value)
    assert error_record["status"] == "error"
    assert error_record["error_type"] == "api_error"
    assert error_record["latency_seconds"] is not None
    assert "sk-" not in json.dumps(error_record)

    out_file = tmp_path / "results.jsonl"
    record_result(error_record, ground_truth="Aircraft Carrier", condition="clean", output_path=out_file)
    saved = json.loads(out_file.read_text().strip())
    assert saved["status"] == "error"
    assert saved["ground_truth"] == "Aircraft Carrier"


# ---------------------------------------------------------------------
# ground_truth / condition 검증
# ---------------------------------------------------------------------
def test_record_result_rejects_invalid_ground_truth(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    result = classify_image(image, client=fake_client)
    with pytest.raises(ValueError, match="ground_truth"):
        record_result(
            result, ground_truth="Yacht", condition="clean", output_path=tmp_path / "r.jsonl"
        )


def test_record_result_rejects_invalid_condition(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    result = classify_image(image, client=fake_client)
    with pytest.raises(ValueError, match="condition"):
        record_result(
            result,
            ground_truth="Aircraft Carrier",
            condition="tampered",
            output_path=tmp_path / "r.jsonl",
        )


def test_record_result_clean_requires_no_attack_name_or_epsilon(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    result = classify_image(image, client=fake_client)
    with pytest.raises(ValueError, match="attack_name and epsilon"):
        record_result(
            result,
            ground_truth="Aircraft Carrier",
            condition="clean",
            attack_name="fgsm",
            epsilon=0.03,
            output_path=tmp_path / "r.jsonl",
        )


def test_record_result_adversarial_requires_valid_attack_name(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    result = classify_image(image, client=fake_client)
    with pytest.raises(ValueError, match="attack_name"):
        record_result(
            result,
            ground_truth="Aircraft Carrier",
            condition="adversarial",
            attack_name="deepfool",  # not fgsm/bim/pgd
            epsilon=0.03,
            output_path=tmp_path / "r.jsonl",
        )


@pytest.mark.parametrize("bad_epsilon", [None, -0.01, float("nan"), float("inf"), True])
def test_record_result_adversarial_requires_valid_epsilon(tmp_path, bad_epsilon):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    result = classify_image(image, client=fake_client)
    with pytest.raises(ValueError, match="epsilon"):
        record_result(
            result,
            ground_truth="Aircraft Carrier",
            condition="adversarial",
            attack_name="fgsm",
            epsilon=bad_epsilon,
            output_path=tmp_path / "r.jsonl",
        )


def test_record_result_adversarial_with_valid_attack_and_epsilon(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    result = classify_image(image, client=fake_client)
    out_file = tmp_path / "r.jsonl"
    record_result(
        result,
        ground_truth="Aircraft Carrier",
        condition="adversarial",
        attack_name="bim",
        epsilon=0.03,
        output_path=out_file,
    )
    saved = json.loads(out_file.read_text().strip())
    assert saved["attack_name"] == "bim"
    assert saved["epsilon"] == 0.03
    # never sent to the API
    request, _ = build_request(image)
    assert "attack_name" not in json.dumps(request)
    assert "bim" not in json.dumps(request)


# ---------------------------------------------------------------------
# 12. clean/adversarial 상태와 ground truth가 API 프롬프트에 포함되지 않음
# ---------------------------------------------------------------------
def test_build_request_has_no_ground_truth_or_condition_params():
    sig = inspect.signature(build_request)
    param_names = set(sig.parameters)
    assert "ground_truth" not in param_names
    assert "condition" not in param_names
    assert "label" not in param_names


def test_request_payload_never_contains_ground_truth_markers(tmp_path):
    image = _make_real_image(tmp_path)
    request, _ = build_request(image)
    serialized = json.dumps(request)
    for forbidden in ("ground_truth", "\"condition\":", "true_label"):
        assert forbidden not in serialized


def test_record_result_adds_ground_truth_locally_only(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    request, _ = build_request(image)
    result = classify_image(image, client=fake_client)

    out_file = tmp_path / "results.jsonl"
    record_result(
        result, ground_truth="Aircraft Carrier", condition="clean", output_path=out_file
    )

    saved = json.loads(out_file.read_text().strip())
    assert saved["ground_truth"] == "Aircraft Carrier"
    assert saved["condition"] == "clean"

    assert "ground_truth" not in json.dumps(request)
    assert "condition" not in json.dumps(request)


def test_schema_requires_all_properties_and_no_additional():
    assert set(PERCEPTION_SCHEMA["required"]) == set(PERCEPTION_SCHEMA["properties"])
    assert PERCEPTION_SCHEMA["additionalProperties"] is False


def test_request_uses_strict_structured_output(tmp_path):
    image = _make_real_image(tmp_path)
    request, _ = build_request(image)
    fmt = request["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["strict"] is True
    assert fmt["schema"] == PERCEPTION_SCHEMA


# ---------------------------------------------------------------------
# 재현성 + store=False
# ---------------------------------------------------------------------
def test_request_pins_model_snapshot_and_reproducibility_params(tmp_path):
    image = _make_real_image(tmp_path)
    request, _ = build_request(image)
    assert request["model"] == "gpt-4o-mini-2024-07-18"
    assert request["max_output_tokens"] > 0
    image_item = request["input"][1]["content"][1]
    assert image_item["type"] == "input_image"
    assert image_item["detail"] == "high"


def test_request_sets_store_false(tmp_path):
    image = _make_real_image(tmp_path)
    request, _ = build_request(image)
    assert request["store"] is False


def test_result_records_reproducibility_metadata(tmp_path):
    image = _make_real_image(tmp_path)
    fake_client = _FakeClient(response=_FakeResponse(_valid_payload()))
    result = classify_image(image, client=fake_client)
    assert result["requested_model"] == "gpt-4o-mini-2024-07-18"
    assert result["response_model"] == "gpt-4o-mini-2024-07-18"
    assert result["prompt_schema_hash"]
    assert result["image_detail"] == "high"


def test_missing_image_file_raises_before_any_network_call(tmp_path):
    missing = tmp_path / "does_not_exist.png"
    with pytest.raises(FileNotFoundError):
        build_request(missing)


# ---------------------------------------------------------------------
# openai SDK 3.0.0 compatibility check -- real OpenAI client + a
# httpx.MockTransport that intercepts every request. No network calls
# occur; this verifies our request dict actually serializes correctly
# through the real SDK's request-building path, not just through our own
# _FakeClient stand-in used everywhere else in this file.
# ---------------------------------------------------------------------
def _mock_transport_handler(captured: dict, payload: dict | None = None, status_code: int = 200):
    """Build an httpx.MockTransport handler that records the outgoing
    request body and returns a canned Responses-API-shaped reply. No real
    network I/O happens -- httpx.MockTransport intercepts at the
    transport layer, before any socket is opened."""
    payload = payload or _valid_payload()
    payload_text = json.dumps(payload)

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            status_code,
            json={
                "id": "resp_mock_001",
                "object": "response",
                "status": "completed",
                "model": "gpt-4o-mini-2024-07-18",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_mock_001",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": payload_text, "annotations": []}
                        ],
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            },
        )

    return handler


def _real_client_with_mock_transport(handler, api_key=None):
    from openai import OpenAI

    if api_key is None:
        api_key = _assemble_fake_key()

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return OpenAI(api_key=api_key, http_client=http_client)


def test_real_sdk_serializes_request_with_all_required_fields(tmp_path):
    image = _make_real_image(tmp_path)
    captured: dict = {}
    client = _real_client_with_mock_transport(_mock_transport_handler(captured))

    result = classify_image(image, client=client)

    assert result["status"] == "success"
    assert result["predicted_class"] == "Aircraft Carrier"

    body = captured["body"]
    assert body["model"] == "gpt-4o-mini-2024-07-18"
    assert body["store"] is False
    assert body["max_output_tokens"] == oc.DEFAULT_MAX_OUTPUT_TOKENS
    assert "text" in body and body["text"]["format"]["type"] == "json_schema"
    assert "input" in body
    # the image content part must actually be present in what the real
    # SDK serialized, not just in our own request dict before it got
    # handed to the SDK.
    serialized_input = json.dumps(body["input"])
    assert "input_image" in serialized_input
    assert "detail" in serialized_input


def test_real_sdk_makes_zero_real_network_calls(tmp_path):
    # httpx.MockTransport guarantees no socket is opened; this test just
    # documents/asserts that the mock handler was actually invoked
    # exactly once (proving the request path was exercised) rather than
    # the call being skipped entirely.
    image = _make_real_image(tmp_path)
    call_count = {"n": 0}

    def counting_handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return _mock_transport_handler({})(request)

    client = _real_client_with_mock_transport(counting_handler)
    classify_image(image, client=client)
    assert call_count["n"] == 1


def test_real_sdk_transport_error_wrapped_as_classification_error(tmp_path):
    image = _make_real_image(tmp_path)

    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated connection failure, no real network used")

    client = _real_client_with_mock_transport(failing_handler)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=client)
    assert excinfo.value.error_type == "api_error"


def test_real_sdk_fake_key_never_leaks_on_transport_error(tmp_path):
    image = _make_real_image(tmp_path)
    fake_key = _assemble_fake_key()

    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"simulated failure mentioning key {fake_key}")

    client = _real_client_with_mock_transport(failing_handler, api_key=fake_key)
    with pytest.raises(ClassificationError) as excinfo:
        classify_image(image, client=client)
    assert fake_key not in str(excinfo.value)
    assert fake_key not in traceback.format_exc()
