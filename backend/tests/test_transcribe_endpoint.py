# Feature: speech-to-text-asr
import io
import os
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

# Ensure env vars are set before the app (and asr_service) are imported
os.environ.setdefault("PARAKIT_API_KEY", "test-key")
os.environ.setdefault("PARAKIT_API_ENDPOINT", "https://fake.parakit.io/transcribe")

from main import app  # noqa: E402

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wav_file(audio_bytes: bytes) -> tuple:
    """Return (filename, file-like, content_type) suitable for httpx multipart."""
    return ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")


# ---------------------------------------------------------------------------
# Property 1: Transcription round-trip
# Feature: speech-to-text-asr, Property 1: Transcription round-trip
# ---------------------------------------------------------------------------

@given(
    audio_bytes=st.binary(min_size=1),
    transcription=st.text(),
)
@settings(max_examples=20, deadline=None)
def test_property1_transcription_round_trip(audio_bytes: bytes, transcription: str) -> None:
    """For any audio bytes and any transcription T, the endpoint returns {"transcription": T}."""
    with patch(
        "routers.ai.asr_service.transcribe",
        new=AsyncMock(return_value=transcription),
    ):
        resp = client.post(
            "/api/transcribe",
            files={"audio": _wav_file(audio_bytes)},
        )

    assert resp.status_code == 200
    assert resp.json()["transcription"] == transcription


# ---------------------------------------------------------------------------
# Property 2: Invalid MIME type rejection
# Feature: speech-to-text-asr, Property 2: Invalid MIME type rejection
# ---------------------------------------------------------------------------

# All MIME types accepted by the endpoint (including codec variants).
_ACCEPTED_TYPES = {
    "audio/wav", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/x-m4a",
    "audio/webm", "audio/webm;codecs=opus",
    "audio/ogg", "audio/ogg;codecs=opus",
}


@given(
    mime_type=st.text(
        alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
    ).filter(lambda m: m.strip() not in _ACCEPTED_TYPES
             and m.strip().split(";")[0].strip() not in _ACCEPTED_TYPES),
)
@settings(max_examples=20, deadline=None)
def test_property2_invalid_mime_type_rejected(mime_type: str) -> None:
    """For any printable MIME type not in the accepted set, the endpoint returns HTTP 415."""
    resp = client.post(
        "/api/transcribe",
        files={"audio": ("audio.bin", io.BytesIO(b"data"), mime_type)},
    )
    assert resp.status_code == 415


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_missing_audio_field_returns_422() -> None:
    """Omitting the audio field entirely should yield HTTP 422."""
    resp = client.post("/api/transcribe")
    assert resp.status_code == 422


def test_network_timeout_returns_503() -> None:
    """When the ASR service raises 'unreachable', the endpoint returns HTTP 503."""
    with patch(
        "routers.ai.asr_service.transcribe",
        new=AsyncMock(side_effect=RuntimeError("ASR service unreachable: timed out")),
    ):
        resp = client.post(
            "/api/transcribe",
            files={"audio": _wav_file(b"audio")},
        )
    assert resp.status_code == 503


def test_parakit_api_error_returns_502() -> None:
    """When the ASR service raises a Parakit API error, the endpoint returns HTTP 502."""
    with patch(
        "routers.ai.asr_service.transcribe",
        new=AsyncMock(side_effect=RuntimeError("Parakit API error 500: internal error")),
    ):
        resp = client.post(
            "/api/transcribe",
            files={"audio": _wav_file(b"audio")},
        )
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# FFmpeg conversion path tests
# ---------------------------------------------------------------------------

def _webm_file(audio_bytes: bytes) -> tuple:
    """Return a multipart tuple with audio/webm content type."""
    return ("audio.webm", io.BytesIO(audio_bytes), "audio/webm")


def _mp4_file(audio_bytes: bytes) -> tuple:
    """Return a multipart tuple with audio/mp4 content type."""
    return ("audio.mp4", io.BytesIO(audio_bytes), "audio/mp4")


def _ogg_file(audio_bytes: bytes) -> tuple:
    """Return a multipart tuple with audio/ogg content type."""
    return ("audio.ogg", io.BytesIO(audio_bytes), "audio/ogg")


FAKE_WAV = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\x3e\x00\x00\x00\x7d\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"


def test_webm_is_converted_and_transcribed() -> None:
    """WebM audio is converted to WAV via FFmpeg then forwarded to the ASR service."""
    with (
        patch("routers.ai.to_wav", new=AsyncMock(return_value=FAKE_WAV)) as mock_convert,
        patch("routers.ai.asr_service.transcribe", new=AsyncMock(return_value="hello")) as mock_asr,
    ):
        resp = client.post("/api/transcribe", files={"audio": _webm_file(b"webm-data")})

    assert resp.status_code == 200
    assert resp.json()["transcription"] == "hello"
    mock_convert.assert_awaited_once_with(b"webm-data")
    # ASR must receive WAV bytes and the WAV MIME type
    mock_asr.assert_awaited_once_with(FAKE_WAV, "audio/wav")


def test_mp4_is_converted_and_transcribed() -> None:
    """MP4/AAC audio is converted to WAV via FFmpeg then forwarded to the ASR service."""
    with (
        patch("routers.ai.to_wav", new=AsyncMock(return_value=FAKE_WAV)),
        patch("routers.ai.asr_service.transcribe", new=AsyncMock(return_value="world")) as mock_asr,
    ):
        resp = client.post("/api/transcribe", files={"audio": _mp4_file(b"mp4-data")})

    assert resp.status_code == 200
    mock_asr.assert_awaited_once_with(FAKE_WAV, "audio/wav")


def test_ogg_is_converted_and_transcribed() -> None:
    """Ogg audio is converted to WAV via FFmpeg then forwarded to the ASR service."""
    with (
        patch("routers.ai.to_wav", new=AsyncMock(return_value=FAKE_WAV)),
        patch("routers.ai.asr_service.transcribe", new=AsyncMock(return_value="ogg text")) as mock_asr,
    ):
        resp = client.post("/api/transcribe", files={"audio": _ogg_file(b"ogg-data")})

    assert resp.status_code == 200
    mock_asr.assert_awaited_once_with(FAKE_WAV, "audio/wav")


def test_wav_skips_conversion() -> None:
    """WAV audio bypasses FFmpeg and goes directly to the ASR service."""
    with (
        patch("routers.ai.to_wav", new=AsyncMock(return_value=FAKE_WAV)) as mock_convert,
        patch("routers.ai.asr_service.transcribe", new=AsyncMock(return_value="direct")) as mock_asr,
    ):
        resp = client.post("/api/transcribe", files={"audio": _wav_file(b"wav-data")})

    assert resp.status_code == 200
    mock_convert.assert_not_awaited()
    mock_asr.assert_awaited_once_with(b"wav-data", "audio/wav")


def test_ffmpeg_not_installed_returns_422() -> None:
    """If FFmpeg is missing, the endpoint returns HTTP 422 with a clear message."""
    with patch(
        "routers.ai.to_wav",
        new=AsyncMock(side_effect=RuntimeError("FFmpeg is not installed or not on PATH.")),
    ):
        resp = client.post("/api/transcribe", files={"audio": _webm_file(b"webm-data")})

    assert resp.status_code == 422
    assert "FFmpeg" in resp.json()["detail"]


def test_corrupt_audio_returns_422() -> None:
    """If FFmpeg cannot decode the file, the endpoint returns HTTP 422."""
    with patch(
        "routers.ai.to_wav",
        new=AsyncMock(side_effect=RuntimeError("FFmpeg conversion failed (exit 1): Invalid data")),
    ):
        resp = client.post("/api/transcribe", files={"audio": _webm_file(b"not-audio")})

    assert resp.status_code == 422
    assert "FFmpeg conversion failed" in resp.json()["detail"]


@given(
    audio_bytes=st.binary(min_size=1),
    transcription=st.text(),
)
@settings(max_examples=20, deadline=None)
def test_property_webm_round_trip(audio_bytes: bytes, transcription: str) -> None:
    """For any bytes uploaded as WebM, after conversion the endpoint returns the transcription."""
    with (
        patch("routers.ai.to_wav", new=AsyncMock(return_value=FAKE_WAV)),
        patch("routers.ai.asr_service.transcribe", new=AsyncMock(return_value=transcription)),
    ):
        resp = client.post("/api/transcribe", files={"audio": _webm_file(audio_bytes)})

    assert resp.status_code == 200
    assert resp.json()["transcription"] == transcription
