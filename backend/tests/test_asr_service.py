# Feature: speech-to-text-asr
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from services import asr_service  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: build a fake httpx.Response
# ---------------------------------------------------------------------------

def _make_response(status_code: int, body: dict | str) -> MagicMock:
    """Return a MagicMock that looks like an httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if isinstance(body, dict):
        resp.text = json.dumps(body)
        resp.json.return_value = body
    else:
        resp.text = body
        resp.json.return_value = {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Property 3: ASR service extracts transcription from API response
# Feature: speech-to-text-asr, Property 3: ASR service extracts transcription from API response
# ---------------------------------------------------------------------------

@given(transcription=st.text())
@settings(max_examples=20, deadline=None)
def test_property3_transcription_extracted(transcription: str) -> None:
    """For any transcription string T in the mock response, transcribe() returns exactly T."""
    fake_resp = _make_response(200, {"transcription": transcription})

    async def _fake_post(*args, **kwargs):
        return fake_resp

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=_fake_post)):
        result = asyncio.run(asr_service.transcribe(b"audio", "audio/wav"))

    assert result == transcription


# ---------------------------------------------------------------------------
# Property 4: HTTP error propagation with status code
# Feature: speech-to-text-asr, Property 4: HTTP error propagation with status code
# ---------------------------------------------------------------------------

@given(status_code=st.integers(min_value=400, max_value=599))
@settings(max_examples=20, deadline=None)
def test_property4_http_error_propagation(status_code: int) -> None:
    """For any 4xx/5xx status code, transcribe() raises RuntimeError containing that code."""
    fake_resp = _make_response(status_code, "error body")

    async def _fake_post(*args, **kwargs):
        return fake_resp

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=_fake_post)):
        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(asr_service.transcribe(b"audio", "audio/wav"))

    assert str(status_code) in str(exc_info.value)


# ---------------------------------------------------------------------------
# Property 5: Authorization header on every request
# Feature: speech-to-text-asr, Property 5: Authorization header on every request
# ---------------------------------------------------------------------------

@given(
    audio_bytes=st.binary(min_size=1),
    mime_type=st.sampled_from(["audio/wav", "audio/mpeg"]),
)
@settings(max_examples=20, deadline=None)
def test_property5_auth_header_always_present(audio_bytes: bytes, mime_type: str) -> None:
    """For any audio bytes and MIME type, the outgoing request carries the correct Bearer token."""
    captured_headers: dict = {}
    fake_resp = _make_response(200, {"transcription": "ok"})

    async def _fake_post(url, *, headers=None, **kwargs):
        captured_headers.update(headers or {})
        return fake_resp

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=_fake_post)):
        asyncio.run(asr_service.transcribe(audio_bytes, mime_type))

    # The key used is whatever os.getenv returns at call time (patched to "test-api-key"
    # by the autouse fixture in conftest.py)
    expected_key = os.getenv("PARAKIT_API_KEY", "test-api-key")
    assert captured_headers.get("Authorization") == f"Bearer {expected_key}"


# ---------------------------------------------------------------------------
# Unit test: missing PARAKIT_API_KEY raises ValueError at call time
# ---------------------------------------------------------------------------

@pytest.mark.no_patch_asr
def test_missing_api_key_raises_value_error(monkeypatch) -> None:
    """transcribe() raises ValueError when PARAKIT_API_KEY is absent from the environment."""
    monkeypatch.delenv("PARAKIT_API_KEY", raising=False)
    # Also clear the module-level cached value so the call-time check triggers
    monkeypatch.setattr(asr_service, "PARAKIT_API_KEY", None)

    with pytest.raises(ValueError, match="PARAKIT_API_KEY is not set"):
        asyncio.run(asr_service.transcribe(b"audio", "audio/wav"))
