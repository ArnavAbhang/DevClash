"""
routers/ai.py
~~~~~~~~~~~~~
AI feature routes:

  POST /summarize   →  LLM text summarisation via Groq
  POST /transcribe  →  speech-to-text via Groq Whisper (whisper-large-v3-turbo)
"""

import io
import re
import json
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from groq import Groq
from pydantic import BaseModel

from core.config import settings

@dataclass
class TranscriptSegment:
    """Represents a segment of transcribed audio with metadata."""
    text: str
    start_time: float
    end_time: float
    confidence: float
    speaker: Optional[str] = None
    no_speech_prob: float = 0.0

@dataclass
class AudioProcessingConfig:
    """Configuration for audio processing and transcription."""
    confidence_threshold: float = 0.7
    enable_speaker_identification: bool = True
    enable_intelligent_buffering: bool = True
    max_segment_length: int = 30  # seconds
    temperature: float = 0.2
    language: str = "en"

# Global configuration instance
audio_config = AudioProcessingConfig()

router = APIRouter(prefix="/api", tags=["ai"])

_groq_client: Optional[Groq] = None


def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


_MIME_TO_EXT: dict[str, str] = {
    # Standard audio formats
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/x-m4a": "m4a",
    "audio/m4a": "m4a",
    "audio/aac": "aac",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
    "audio/opus": "opus",
    
    # Additional formats for production support
    "audio/amr": "amr",
    "audio/3gpp": "3gp",
    "audio/x-ms-wma": "wma",
    "audio/vnd.wave": "wav",
    "audio/L16": "wav",
    "audio/pcm": "wav",
    
    # Codec-specific variants
    "audio/webm;codecs=opus": "webm",
    "audio/ogg;codecs=opus": "ogg",
    "audio/mp4;codecs=aac": "mp4",
}


def _remove_repetitions(text: str) -> str:
    """
    Advanced deduplication function that removes repeated phrases from Whisper hallucinations.
    Handles consecutive duplicate sentences, repeated n-gram loops, and common ASR artifacts.
    
    Args:
        text: Raw transcription text that may contain repetitions
        
    Returns:
        Cleaned text with repetitions removed
    """
    if not text:
        return text or ""

    # 1. Normalize whitespace and remove common ASR artifacts
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'[.]{2,}', '.', text)  # Multiple periods
    text = re.sub(r'[,]{2,}', ',', text)  # Multiple commas
    
    # 2. Remove common filler words that get repeated (improved pattern)
    # Handle "um um um" -> "um" more effectively
    text = re.sub(r'\b(um|uh|ah|er)\s+(\1\s*)+', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(like|you know|so|well)\s+(\1\s+)+', r'\1 ', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(and|the|a|an|to|of|in|for|on|with|at|by|from)\s+(\1\s+)+', r'\1 ', text, flags=re.IGNORECASE)

    # 3. Collapse repeated consecutive sentences/clauses
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    deduped: List[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and (not deduped or sentence.lower() != deduped[-1].lower()):
            deduped.append(sentence)
    text = ' '.join(deduped)

    # 4. Advanced word-level repetition removal
    words = text.split()
    if len(words) <= 2:
        return text
        
    # Remove immediate word repetitions (the the the -> the)
    result_words = [words[0]]
    for i in range(1, len(words)):
        if words[i].lower() != words[i-1].lower():
            result_words.append(words[i])
    words = result_words

    # 5. Remove repeated phrase patterns (2-8 word sequences)
    for phrase_len in range(min(8, len(words)//2), 1, -1):
        i = 0
        new_words = []
        while i < len(words):
            if i + phrase_len * 2 <= len(words):
                phrase1 = words[i:i+phrase_len]
                phrase2 = words[i+phrase_len:i+phrase_len*2]
                
                # Check if phrases are similar (allowing for minor variations)
                if _phrases_similar(phrase1, phrase2):
                    # Count consecutive repetitions
                    repetitions = 1
                    next_start = i + phrase_len * 2
                    while next_start + phrase_len <= len(words):
                        next_phrase = words[next_start:next_start+phrase_len]
                        if _phrases_similar(phrase1, next_phrase):
                            repetitions += 1
                            next_start += phrase_len
                        else:
                            break
                    
                    # Keep only one instance of the repeated phrase
                    new_words.extend(phrase1)
                    i = next_start
                else:
                    new_words.append(words[i])
                    i += 1
            else:
                new_words.append(words[i])
                i += 1
        words = new_words

    # 6. Final cleanup
    text = ' '.join(words)
    text = re.sub(r'\s+([.!?])', r'\1', text)  # Fix spacing before punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def _phrases_similar(phrase1: List[str], phrase2: List[str], threshold: float = 0.8) -> bool:
    """
    Check if two phrases are similar enough to be considered repetitions.
    
    Args:
        phrase1, phrase2: Lists of words to compare
        threshold: Similarity threshold (0.0 to 1.0)
        
    Returns:
        True if phrases are similar enough to be considered repetitions
    """
    if len(phrase1) != len(phrase2):
        return False
        
    if not phrase1:
        return True
        
    # Calculate word-level similarity
    matches = sum(1 for w1, w2 in zip(phrase1, phrase2) 
                  if w1.lower() == w2.lower())
    similarity = matches / len(phrase1)
    
    return similarity >= threshold


def _identify_speaker(segment_data: Dict[str, Any], previous_speaker: Optional[str] = None) -> Optional[str]:
    """
    Attempt to identify speaker from audio segment data.
    This is a simplified implementation - in production, you'd use more sophisticated
    speaker diarization techniques.
    
    Args:
        segment_data: Segment data from Whisper API
        previous_speaker: Previously identified speaker for continuity
        
    Returns:
        Speaker identifier or None if unable to determine
    """
    # For now, use a simple heuristic based on audio characteristics
    # In a real implementation, this would use speaker diarization models
    
    # Check if segment has speaker information (some Whisper variants provide this)
    if 'speaker' in segment_data:
        return segment_data['speaker']
    
    # Simple heuristic: alternate speakers based on silence gaps
    # This is very basic and would need improvement for production
    if 'no_speech_prob' in segment_data:
        no_speech_prob = segment_data['no_speech_prob']
        if no_speech_prob > 0.3:  # Significant pause might indicate speaker change
            return "Speaker B" if previous_speaker == "Speaker A" else "Speaker A"
    
    # Default to continuing with previous speaker or starting with A
    return previous_speaker or "Speaker A"


def _apply_confidence_filtering(segments: List[Dict[str, Any]], threshold: float = 0.7) -> List[TranscriptSegment]:
    """
    Filter segments based on confidence scores and convert to TranscriptSegment objects.
    
    Args:
        segments: Raw segments from Whisper API
        threshold: Minimum confidence threshold
        
    Returns:
        List of filtered and processed TranscriptSegment objects
    """
    filtered_segments = []
    previous_speaker = None
    
    for segment in segments:
        # Calculate confidence score (Whisper doesn't always provide this directly)
        confidence = 1.0 - segment.get('no_speech_prob', 0.0)
        
        # Apply confidence threshold
        if confidence < threshold:
            continue
            
        # Skip very short segments that are likely noise
        text = segment.get('text', '').strip()
        if len(text) < 3:
            continue
            
        # Identify speaker
        speaker = _identify_speaker(segment, previous_speaker)
        previous_speaker = speaker
        
        # Create TranscriptSegment
        transcript_segment = TranscriptSegment(
            text=text,
            start_time=segment.get('start', 0.0),
            end_time=segment.get('end', 0.0),
            confidence=confidence,
            speaker=speaker,
            no_speech_prob=segment.get('no_speech_prob', 0.0)
        )
        
        filtered_segments.append(transcript_segment)
    
    return filtered_segments


def _intelligent_buffering(segments: List[TranscriptSegment]) -> str:
    """
    Apply intelligent buffering to ensure complete sentences and natural breaks.
    
    Args:
        segments: List of transcript segments
        
    Returns:
        Buffered and processed transcription text
    """
    if not segments:
        return ""
    
    # Combine segments into coherent text blocks
    text_parts = []
    current_speaker = None
    current_text = ""
    
    for segment in segments:
        # Check for speaker changes
        if segment.speaker != current_speaker:
            if current_text.strip():
                text_parts.append(current_text.strip())
            current_text = segment.text
            current_speaker = segment.speaker
        else:
            # Same speaker, continue building text
            current_text += " " + segment.text
    
    # Add final text
    if current_text.strip():
        text_parts.append(current_text.strip())
    
    # Join with appropriate spacing
    full_text = " ".join(text_parts)
    
    # Ensure sentences end properly
    full_text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', full_text)
    
    return full_text.strip()


def _check_conversation_history_overlap(transcription: str, conversation_history: str) -> bool:
    """
    Enhanced conversation history checking to detect repetitions and overlaps.
    
    Args:
        transcription: New transcription to check
        conversation_history: Previous conversation history
        
    Returns:
        True if transcription appears to be a repetition, False otherwise
    """
    if not conversation_history:
        return False
        
    if not transcription or not transcription.strip():
        return True  # Empty transcription should be filtered
    
    # Normalize both texts for comparison
    trans_normalized = re.sub(r'[^\w\s]', '', transcription.lower()).strip()
    history_normalized = re.sub(r'[^\w\s]', '', conversation_history.lower()).strip()
    
    if not trans_normalized:
        return True  # Empty transcription should be filtered
    
    # Check for exact substring match
    if trans_normalized in history_normalized:
        return True
    
    # Check for high word overlap (>80% of words already said)
    trans_words = set(trans_normalized.split())
    history_words = set(history_normalized.split())
    
    if len(trans_words) > 2:
        overlap_ratio = len(trans_words & history_words) / len(trans_words)
        if overlap_ratio > 0.8:
            return True
    
    # Check for repeated phrases at the end of history
    # This catches cases where the same phrase is being repeated
    history_words_list = history_normalized.split()
    trans_words_list = trans_normalized.split()
    
    if len(trans_words_list) >= 3 and len(history_words_list) >= len(trans_words_list):
        # Check if transcription matches the end of history
        history_end = history_words_list[-len(trans_words_list):]
        if history_end == trans_words_list:
            return True
    
    return False


# ── Routes ────────────────────────────────────────────────────────────────────

class AudioConfigRequest(BaseModel):
    confidence_threshold: Optional[float] = None
    enable_speaker_identification: Optional[bool] = None
    enable_intelligent_buffering: Optional[bool] = None
    max_segment_length: Optional[int] = None
    temperature: Optional[float] = None
    language: Optional[str] = None


@router.post("/transcribe/config")
def update_audio_config(config: AudioConfigRequest):
    """
    Update audio processing configuration settings.
    
    Args:
        config: New configuration parameters
        
    Returns:
        Updated configuration
    """
    global audio_config
    
    if config.confidence_threshold is not None:
        audio_config.confidence_threshold = max(0.0, min(1.0, config.confidence_threshold))
    
    if config.enable_speaker_identification is not None:
        audio_config.enable_speaker_identification = config.enable_speaker_identification
    
    if config.enable_intelligent_buffering is not None:
        audio_config.enable_intelligent_buffering = config.enable_intelligent_buffering
    
    if config.max_segment_length is not None:
        audio_config.max_segment_length = max(5, min(60, config.max_segment_length))
    
    if config.temperature is not None:
        audio_config.temperature = max(0.0, min(1.0, config.temperature))
    
    if config.language is not None:
        audio_config.language = config.language
    
    return {
        "message": "Audio configuration updated successfully",
        "config": asdict(audio_config)
    }


@router.get("/transcribe/config")
def get_audio_config():
    """
    Get current audio processing configuration.
    
    Returns:
        Current configuration settings
    """
    return {
        "config": asdict(audio_config)
    }


class TextRequest(BaseModel):
    text: str
def summarize(req: TextRequest):
    """
    Generate an AI summary of the provided text using Groq's LLaMA model.
    Always assumes transcript is available from the system and outputs exactly 5 bullet points.
    """
    text = req.text.strip()
    
    # Handle empty transcript case
    if not text:
        return {"summary": "Error: No transcript data received from system"}
    
    if len(text) < 10:
        return {"summary": "Error: No transcript data received from system"}
    
    try:
        # Enhanced system prompt for consistent 5-bullet-point summaries
        system_prompt = """You are an AI assistant that processes meeting transcripts from the system.

CRITICAL INSTRUCTIONS:
- Always assume the meeting transcript is available from the system
- Do NOT ask the user for input
- Extract the transcript and generate a clear and structured summary
- Output exactly 5 concise bullet points
- If transcript is empty, return: "Error: No transcript data received from system"

Your task:
1. Extract the transcript (already provided)
2. Generate a clear and structured summary
3. Output exactly 5 concise bullet points

Format your response as exactly 5 bullet points using this format:
• [Key point 1]
• [Key point 2] 
• [Key point 3]
• [Key point 4]
• [Key point 5]

Focus on:
- Key discussion topics
- Important decisions made
- Action items and assignments
- Deadlines and next steps
- Critical outcomes or concerns"""
        
        response = _get_groq().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Process this meeting transcript and provide exactly 5 bullet points:\n\n{text}"},
            ],
            temperature=0.1,  # Very low temperature for consistent formatting
            max_tokens=400,   # Enough for 5 bullet points
        )
        
        summary = response.choices[0].message.content
        if not summary:
            return {"summary": "Error: No transcript data received from system"}
            
        # Ensure the summary is properly formatted
        summary = summary.strip()
        
        # If the AI didn't format properly, try to fix it
        if not summary.startswith('•') and not summary.startswith('-') and not summary.startswith('*'):
            # Split into lines and format as bullet points
            lines = [line.strip() for line in summary.split('\n') if line.strip()]
            if len(lines) >= 5:
                summary = '\n'.join([f"• {line}" for line in lines[:5]])
            else:
                # If we don't have enough lines, keep original
                pass
                
        return {"summary": summary}
        
    except Exception as exc:
        print(f"[ERROR] Groq summarization error: {exc}")
        return {"summary": "Error: No transcript data received from system"}


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    conversation_history: Optional[str] = Form(None),
    confidence_threshold: Optional[float] = Form(None),
    enable_speaker_identification: Optional[bool] = Form(None),
    language: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    enhanced_response: Optional[bool] = Form(False),
) -> dict:
    """
    Enhanced transcription endpoint with production-grade features:
    - Advanced deduplication and repetition removal
    - Conversation history context for better accuracy
    - Confidence-based filtering with configurable thresholds
    - Speaker identification capabilities
    - Intelligent buffering for complete sentence processing
    - Support for multiple audio formats and quality levels
    
    Args:
        audio: Audio file to transcribe
        conversation_history: Previous conversation context to avoid repetitions
        confidence_threshold: Minimum confidence score for segments (0.0-1.0)
        enable_speaker_identification: Whether to attempt speaker identification
        language: Language code for transcription (default: "en")
        temperature: Randomness for transcription (0.0-1.0, default: 0.2)
        enhanced_response: Whether to return enhanced response with metadata (default: False for backward compatibility)
        
    Returns:
        Transcription response (simple format for backward compatibility, enhanced format if requested)
    """
    # Set defaults for backward compatibility
    confidence_threshold = confidence_threshold if confidence_threshold is not None else audio_config.confidence_threshold
    enable_speaker_identification = enable_speaker_identification if enable_speaker_identification is not None else audio_config.enable_speaker_identification
    temperature = temperature if temperature is not None else audio_config.temperature
    language = language or audio_config.language
    enhanced_response = enhanced_response or False
    
    # Validate parameters
    confidence_threshold = max(0.0, min(1.0, confidence_threshold))
    temperature = max(0.0, min(1.0, temperature))
    
    # Process audio file
    raw_type = (audio.content_type or "").strip()
    base_type = raw_type.split(";")[0].strip()
    ext = _MIME_TO_EXT.get(base_type) or _MIME_TO_EXT.get(raw_type) or "webm"

    audio_bytes = await audio.read()
    print(f"[DEBUG] Enhanced transcribe - Audio size: {len(audio_bytes)} bytes, ext: {ext}, confidence_threshold: {confidence_threshold}")

    # Skip processing very small audio files
    if len(audio_bytes) < 500:
        if enhanced_response:
            return {
                "transcription": "",
                "segments": [],
                "metadata": {
                    "confidence_threshold": confidence_threshold,
                    "speaker_identification_enabled": enable_speaker_identification,
                    "language": language,
                    "processing_time": 0.0,
                    "filtered_segments": 0,
                    "total_segments": 0
                }
            }
        else:
            return {"transcription": ""}

    try:
        import time
        start_time = time.time()
        
        # Enhanced Whisper API call with verbose response
        result = _get_groq().audio.transcriptions.create(
            file=(f"audio.{ext}", io.BytesIO(audio_bytes), base_type or f"audio/{ext}"),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",  # Get detailed segment information
            temperature=temperature,
            language=language,
        )

        # Extract and process segments
        raw_segments = getattr(result, "segments", None) or []
        total_segments = len(raw_segments)
        
        # Apply confidence-based filtering and speaker identification
        filtered_segments = _apply_confidence_filtering(
            raw_segments, 
            threshold=confidence_threshold
        )
        
        # Apply intelligent buffering for complete sentences
        if audio_config.enable_intelligent_buffering:
            transcription = _intelligent_buffering(filtered_segments)
        else:
            # Fallback to simple text joining
            transcription = " ".join(seg.text for seg in filtered_segments).strip()

        # Apply advanced deduplication
        transcription = _remove_repetitions(transcription)

        # Check against conversation history for repetitions
        if conversation_history and transcription:
            if _check_conversation_history_overlap(transcription, conversation_history):
                print(f"[DEBUG] Detected conversation history overlap: '{transcription}' - filtering out")
                transcription = ""
                filtered_segments = []

        processing_time = time.time() - start_time
        
        # Return response based on requested format
        if enhanced_response:
            # Enhanced response with metadata
            response = {
                "transcription": transcription,
                "segments": [asdict(seg) for seg in filtered_segments] if enable_speaker_identification else [],
                "metadata": {
                    "confidence_threshold": confidence_threshold,
                    "speaker_identification_enabled": enable_speaker_identification,
                    "language": language,
                    "temperature": temperature,
                    "processing_time": round(processing_time, 3),
                    "filtered_segments": len(filtered_segments),
                    "total_segments": total_segments,
                    "audio_duration": getattr(result, "duration", 0.0),
                    "format": ext
                }
            }
        else:
            # Simple response for backward compatibility
            response = {"transcription": transcription}
        
        print(f"[DEBUG] Enhanced transcription complete - Text: '{transcription}', Segments: {len(filtered_segments)}, Time: {processing_time:.3f}s")
        
        return response

    except Exception as exc:
        print(f"[ERROR] Enhanced Groq Whisper error: {exc}")
        raise HTTPException(status_code=502, detail=f"Enhanced transcription failed: {exc}") from exc
