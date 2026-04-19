"""
routers/ai.py
~~~~~~~~~~~~~
AI feature routes:

  POST /summarize   →  LLM text summarisation via Groq
  POST /transcribe  →  speech-to-text via Groq Whisper (whisper-large-v3-turbo)
"""

import io
import re
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from groq import Groq
from pydantic import BaseModel

from core.config import settings

router = APIRouter(prefix="/api", tags=["ai"])

_groq_client: Optional[Groq] = None


def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


_MIME_TO_EXT: dict[str, str] = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/x-m4a": "m4a",
    "audio/aac": "aac",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
    "audio/opus": "opus",
}


def _remove_repetitions(text: str) -> str:
    """
    Remove repeated phrases that Whisper hallucinates on silence/pauses.
    Handles both consecutive duplicate sentences and repeated n-gram loops.
    """
    if not text:
        return text

    # 1. Collapse repeated consecutive sentences/clauses
    #    e.g. "hello world. hello world." → "hello world."
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    deduped: list[str] = []
    for s in sentences:
        if not deduped or s.strip().lower() != deduped[-1].strip().lower():
            deduped.append(s)
    text = ' '.join(deduped)

    # 2. Collapse repeated word-level loops (e.g. "the the the the")
    text = re.sub(r'\b(\w+)(\s+\1){2,}\b', r'\1', text, flags=re.IGNORECASE)

    # 3. Collapse repeated short phrases (2-6 words) that appear 3+ times
    words = text.split()
    for n in range(6, 1, -1):
        i = 0
        result: list[str] = []
        while i < len(words):
            phrase = words[i:i+n]
            if len(phrase) < n:
                result.extend(phrase)
                break
            # Count how many times this phrase repeats consecutively
            count = 1
            while words[i+count*n:i+(count+1)*n] == phrase:
                count += 1
            result.extend(phrase)
            i += n * count
        words = result
    text = ' '.join(words)

    return text.strip()


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
async def transcribe(
    audio: UploadFile = File(...),
    conversation_history: Optional[str] = Form(None),
) -> dict:
    """
    Accept audio and return transcription via Groq Whisper.
    Pass conversation_history to detect and remove repeated segments.
    """
    raw_type = (audio.content_type or "").strip()
    base_type = raw_type.split(";")[0].strip()

    ext = _MIME_TO_EXT.get(base_type) or _MIME_TO_EXT.get(raw_type) or "webm"

    audio_bytes = await audio.read()
    print(f"[DEBUG] Audio size: {len(audio_bytes)} bytes, ext: {ext}")

    if len(audio_bytes) < 500:
        return {"transcription": ""}

    try:
        # Don't pass prompt to Whisper — it causes more repetition than it prevents
        result = _get_groq().audio.transcriptions.create(
            file=(f"audio.{ext}", io.BytesIO(audio_bytes), base_type or f"audio/{ext}"),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",  # gives us segments + no_speech_prob
            temperature=0.2,                 # slight randomness to break repetition loops
            language="en",
        )

        # Filter out segments where Whisper itself is uncertain (no speech)
        segments = getattr(result, "segments", None) or []
        if segments:
            # Only keep segments with reasonable confidence
            text_parts = [
                seg["text"] for seg in segments
                if seg.get("no_speech_prob", 0) < 0.5 and len(seg["text"].strip()) > 0
            ]
            transcription = " ".join(text_parts).strip()
        else:
            transcription = (getattr(result, "text", "") or "").strip()

        # Post-process: remove hallucinated repetitions
        transcription = _remove_repetitions(transcription)

        # If we have conversation history, check if this transcription is a repeat
        # of something already said (Whisper's biggest hallucination pattern)
        if conversation_history and transcription:
            history_lower = conversation_history.lower()
            trans_lower = transcription.lower()
            
            # Check if this exact phrase already exists in the conversation
            if trans_lower in history_lower:
                print(f"[DEBUG] Detected repeated phrase: '{transcription}' - filtering out")
                transcription = ""
            else:
                # Check for substantial overlap (>70% of words already said)
                trans_words = set(trans_lower.split())
                history_words = set(history_lower.split())
                if len(trans_words) > 3:
                    overlap_ratio = len(trans_words & history_words) / len(trans_words)
                    if overlap_ratio > 0.7:
                        print(f"[DEBUG] High word overlap ({overlap_ratio:.1%}): '{transcription}' - filtering out")
                        transcription = ""

        print(f"[DEBUG] Final transcription: '{transcription}'")

    except Exception as exc:
        print(f"[ERROR] Groq Whisper error: {exc}")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc

    return {"transcription": transcription}
