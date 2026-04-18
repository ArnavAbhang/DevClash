"""
routers/ai.py
~~~~~~~~~~~~~
AI feature routes (previously in main.py):

  POST /summarize   →  LLM text summarisation via Groq
  POST /transcribe  →  speech-to-text via Parakit ASR + FFmpeg conversion
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from groq import Groq
from pydantic import BaseModel

from core.config import settings
from services import asr_service
from services.audio_converter import OUTPUT_MIME_TYPE, needs_conversion, to_wav

router = APIRouter(prefix="/api", tags=["ai"])

# Lazy-initialise the Groq client so it is created after the settings are
# fully loaded (important for test environments that patch env vars).
_groq_client: Groq | None = None


def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client

# ── MIME type sets ────────────────────────────────────────────────────────────

_NATIVE_TYPES: set[str] = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
}

_CONVERTIBLE_TYPES: set[str] = {
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/ogg",
    "audio/ogg;codecs=opus",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
    "audio/flac",
    "audio/x-flac",
    "audio/opus",
}

_ALL_ACCEPTED_TYPES: set[str] = _NATIVE_TYPES | _CONVERTIBLE_TYPES


# ── Routes ────────────────────────────────────────────────────────────────────

class TextRequest(BaseModel):
    text: str


@router.post("/summarize")
def summarize(req: TextRequest):
    response = _get_groq().chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Summarize the text in 5 clear bullet points."},
            {"role": "user", "content": req.text},
        ],
    )
    return {"summary": response.choices[0].message.content}


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict:
    """Accept audio in any supported format and return its transcription."""
    raw_type = (audio.content_type or "").strip()
    base_type = raw_type.split(";")[0].strip()

    if raw_type not in _ALL_ACCEPTED_TYPES and base_type not in _ALL_ACCEPTED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported audio format '{raw_type}'. "
                "Accepted: WAV, MP3, WebM, MP4/AAC, Ogg, FLAC, Opus."
            ),
        )

    audio_bytes = await audio.read()

    if needs_conversion(base_type):
        try:
            audio_bytes = await to_wav(audio_bytes)
            mime_for_asr = OUTPUT_MIME_TYPE
        except RuntimeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        mime_for_asr = base_type

    try:
        transcription = await asr_service.transcribe(audio_bytes, mime_for_asr)
    except RuntimeError as exc:
        if "unreachable" in str(exc):
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"transcription": transcription}
