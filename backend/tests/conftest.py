import os
import sys

import pytest

# ── Environment setup (must happen before any app imports) ────────────────────
os.environ.setdefault("PARAKIT_API_KEY", "test-api-key")
os.environ.setdefault("PARAKIT_API_ENDPOINT", "https://api.parakit.io/v1/transcribe")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-tests-only")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/taskapp_test")

# Ensure the backend root is on sys.path so all imports resolve correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def patch_asr_api_key(monkeypatch, request):
    """
    Patch asr_service module-level variables so tests don't need a real key.
    Tests marked with ``no_patch_asr`` opt out of this fixture.
    """
    if "no_patch_asr" in request.keywords:
        return

    import services.asr_service as asr_service_mod

    monkeypatch.setattr(asr_service_mod, "PARAKIT_API_KEY", "test-api-key")
    monkeypatch.setattr(
        asr_service_mod,
        "PARAKIT_API_ENDPOINT",
        "https://api.parakit.io/v1/transcribe",
    )
