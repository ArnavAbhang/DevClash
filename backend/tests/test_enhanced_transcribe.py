# Feature: production-grade-transcription
import asyncio
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from main import app
from routers.ai import (
    _remove_repetitions, 
    _phrases_similar, 
    _check_conversation_history_overlap,
    _apply_confidence_filtering,
    _intelligent_buffering,
    TranscriptSegment
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests for enhanced deduplication functions
# ---------------------------------------------------------------------------

class TestAdvancedDeduplication:
    """Test the enhanced _remove_repetitions function."""
    
    def test_removes_consecutive_duplicate_sentences(self):
        """Should remove consecutive duplicate sentences."""
        text = "Hello world. Hello world. How are you?"
        result = _remove_repetitions(text)
        assert result == "Hello world. How are you?"
    
    def test_removes_repeated_words(self):
        """Should remove repeated word sequences."""
        text = "The the the meeting is starting"
        result = _remove_repetitions(text)
        assert result == "The meeting is starting"
    
    def test_removes_filler_word_repetitions(self):
        """Should remove repeated filler words."""
        text = "Um um um, let's start the meeting"
        result = _remove_repetitions(text)
        assert result == "Um, let's start the meeting"
    
    def test_removes_repeated_phrases(self):
        """Should remove repeated phrase patterns."""
        text = "Let's go let's go let's go to the meeting"
        result = _remove_repetitions(text)
        assert result == "Let's go to the meeting"
    
    def test_handles_empty_text(self):
        """Should handle empty or None text gracefully."""
        assert _remove_repetitions("") == ""
        assert _remove_repetitions(None) == ""
    
    def test_normalizes_whitespace(self):
        """Should normalize excessive whitespace."""
        text = "Hello    world.   How   are you?"
        result = _remove_repetitions(text)
        assert "    " not in result
        assert "   " not in result


class TestPhraseSimilarity:
    """Test the _phrases_similar function."""
    
    def test_identical_phrases_are_similar(self):
        """Identical phrases should be considered similar."""
        phrase1 = ["hello", "world"]
        phrase2 = ["hello", "world"]
        assert _phrases_similar(phrase1, phrase2) is True
    
    def test_case_insensitive_comparison(self):
        """Should be case insensitive."""
        phrase1 = ["Hello", "World"]
        phrase2 = ["hello", "world"]
        assert _phrases_similar(phrase1, phrase2) is True
    
    def test_different_length_phrases_not_similar(self):
        """Phrases of different lengths should not be similar."""
        phrase1 = ["hello", "world"]
        phrase2 = ["hello", "world", "today"]
        assert _phrases_similar(phrase1, phrase2) is False
    
    def test_partially_similar_phrases(self):
        """Should handle partially similar phrases based on threshold."""
        phrase1 = ["hello", "world", "today"]
        phrase2 = ["hello", "world", "tomorrow"]
        # 2/3 = 0.67, below default threshold of 0.8
        assert _phrases_similar(phrase1, phrase2) is False
        # But should be similar with lower threshold
        assert _phrases_similar(phrase1, phrase2, threshold=0.6) is True


class TestConversationHistoryOverlap:
    """Test the _check_conversation_history_overlap function."""
    
    def test_detects_exact_repetition(self):
        """Should detect exact repetitions in conversation history."""
        transcription = "Hello everyone"
        history = "Welcome to the meeting. Hello everyone. Let's start."
        assert _check_conversation_history_overlap(transcription, history) is True
    
    def test_detects_high_word_overlap(self):
        """Should detect high word overlap."""
        transcription = "meeting agenda today"
        history = "Today we have a meeting with an important agenda"
        assert _check_conversation_history_overlap(transcription, history) is True
    
    def test_allows_new_content(self):
        """Should allow genuinely new content."""
        transcription = "Let's discuss the budget"
        history = "Welcome everyone to today's meeting"
        assert _check_conversation_history_overlap(transcription, history) is False
    
    def test_handles_empty_inputs(self):
        """Should handle empty inputs gracefully."""
        assert _check_conversation_history_overlap("", "some history") is True
        assert _check_conversation_history_overlap("new text", "") is False
        assert _check_conversation_history_overlap("", "") is False


class TestConfidenceFiltering:
    """Test the _apply_confidence_filtering function."""
    
    def test_filters_low_confidence_segments(self):
        """Should filter out segments below confidence threshold."""
        segments = [
            {"text": "Hello", "start": 0.0, "end": 1.0, "no_speech_prob": 0.1},  # High confidence
            {"text": "world", "start": 1.0, "end": 2.0, "no_speech_prob": 0.8},  # Low confidence
            {"text": "today", "start": 2.0, "end": 3.0, "no_speech_prob": 0.2},  # High confidence
        ]
        
        result = _apply_confidence_filtering(segments, threshold=0.7)
        
        assert len(result) == 2
        assert result[0].text == "Hello"
        assert result[1].text == "today"
    
    def test_assigns_speakers(self):
        """Should assign speaker identifiers to segments."""
        segments = [
            {"text": "Hello", "start": 0.0, "end": 1.0, "no_speech_prob": 0.1},
            {"text": "world", "start": 1.0, "end": 2.0, "no_speech_prob": 0.1},
        ]
        
        result = _apply_confidence_filtering(segments)
        
        assert all(seg.speaker is not None for seg in result)
        assert result[0].speaker == "Speaker A"
    
    def test_filters_very_short_segments(self):
        """Should filter out very short segments that are likely noise."""
        segments = [
            {"text": "Hi", "start": 0.0, "end": 1.0, "no_speech_prob": 0.1},  # Too short
            {"text": "Hello everyone", "start": 1.0, "end": 2.0, "no_speech_prob": 0.1},  # Good
        ]
        
        result = _apply_confidence_filtering(segments)
        
        assert len(result) == 1
        assert result[0].text == "Hello everyone"


class TestIntelligentBuffering:
    """Test the _intelligent_buffering function."""
    
    def test_combines_same_speaker_segments(self):
        """Should combine segments from the same speaker."""
        segments = [
            TranscriptSegment("Hello", 0.0, 1.0, 0.9, "Speaker A"),
            TranscriptSegment("everyone", 1.0, 2.0, 0.9, "Speaker A"),
            TranscriptSegment("How are you?", 2.0, 3.0, 0.9, "Speaker B"),
        ]
        
        result = _intelligent_buffering(segments)
        
        assert "Hello everyone" in result
        assert "How are you?" in result
    
    def test_handles_speaker_changes(self):
        """Should handle speaker changes appropriately."""
        segments = [
            TranscriptSegment("Good morning", 0.0, 1.0, 0.9, "Speaker A"),
            TranscriptSegment("Good morning to you too", 1.0, 2.0, 0.9, "Speaker B"),
        ]
        
        result = _intelligent_buffering(segments)
        
        assert "Good morning" in result
        assert "Good morning to you too" in result
    
    def test_handles_empty_segments(self):
        """Should handle empty segment list gracefully."""
        result = _intelligent_buffering([])
        assert result == ""


# ---------------------------------------------------------------------------
# Integration tests for enhanced transcribe endpoint
# ---------------------------------------------------------------------------

class TestEnhancedTranscribeEndpoint:
    """Test the enhanced transcribe endpoint."""
    
    def _wav_file(self, audio_bytes: bytes) -> tuple:
        """Return (filename, file-like, content_type) suitable for httpx multipart."""
        return ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")
    
    @patch('routers.ai._get_groq')
    def test_enhanced_transcribe_with_segments(self, mock_groq):
        """Should return enhanced response with segments and metadata."""
        # Mock Groq response with segments
        mock_result = MagicMock()
        mock_result.segments = [
            {"text": "Hello everyone", "start": 0.0, "end": 2.0, "no_speech_prob": 0.1},
            {"text": "Welcome to the meeting", "start": 2.0, "end": 4.0, "no_speech_prob": 0.2},
        ]
        mock_result.duration = 4.0
        
        mock_groq.return_value.audio.transcriptions.create.return_value = mock_result
        
        response = client.post(
            "/api/transcribe",
            files={"audio": self._wav_file(b"fake_audio_data" * 100)},
            data={
                "confidence_threshold": "0.8",
                "enable_speaker_identification": "true",
                "language": "en",
                "enhanced_response": "true"  # Request enhanced response
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "transcription" in data
        assert "segments" in data
        assert "metadata" in data
        
        metadata = data["metadata"]
        assert metadata["confidence_threshold"] == 0.8
        assert metadata["speaker_identification_enabled"] is True
        assert metadata["language"] == "en"
        assert "processing_time" in metadata
        assert "filtered_segments" in metadata
        assert "total_segments" in metadata
    
    @patch('routers.ai._get_groq')
    def test_conversation_history_filtering(self, mock_groq):
        """Should filter out repetitions based on conversation history."""
        mock_result = MagicMock()
        mock_result.segments = [
            {"text": "Hello everyone", "start": 0.0, "end": 2.0, "no_speech_prob": 0.1},
        ]
        mock_result.duration = 2.0
        
        mock_groq.return_value.audio.transcriptions.create.return_value = mock_result
        
        response = client.post(
            "/api/transcribe",
            files={"audio": self._wav_file(b"fake_audio_data" * 100)},
            data={
                "conversation_history": "Welcome to the meeting. Hello everyone. Let's start.",
                "confidence_threshold": "0.7"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be filtered out due to conversation history overlap
        assert data["transcription"] == ""
    
    def test_small_audio_file_handling(self):
        """Should handle small audio files gracefully."""
        response = client.post(
            "/api/transcribe",
            files={"audio": self._wav_file(b"small")},
            data={"enhanced_response": "true"}  # Request enhanced response to test metadata
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["transcription"] == ""
        assert data["segments"] == []
        assert "metadata" in data
    
    def test_parameter_validation(self):
        """Should validate and clamp parameters to valid ranges."""
        with patch('routers.ai._get_groq') as mock_groq:
            mock_result = MagicMock()
            mock_result.segments = []
            mock_result.duration = 0.0
            mock_groq.return_value.audio.transcriptions.create.return_value = mock_result
            
            response = client.post(
                "/api/transcribe",
                files={"audio": self._wav_file(b"fake_audio_data" * 100)},
                data={
                    "confidence_threshold": "1.5",  # Should be clamped to 1.0
                    "temperature": "-0.5",  # Should be clamped to 0.0
                    "enhanced_response": "true"  # Request enhanced response to test metadata
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            metadata = data["metadata"]
            assert metadata["confidence_threshold"] == 1.0
            assert metadata["temperature"] == 0.0
    
    def test_backward_compatibility_simple_response(self):
        """Should return simple response format by default for backward compatibility."""
        with patch('routers.ai._get_groq') as mock_groq:
            mock_result = MagicMock()
            mock_result.segments = [
                {"text": "Hello world", "start": 0.0, "end": 2.0, "no_speech_prob": 0.1},
            ]
            mock_result.duration = 2.0
            mock_groq.return_value.audio.transcriptions.create.return_value = mock_result
            
            response = client.post(
                "/api/transcribe",
                files={"audio": self._wav_file(b"fake_audio_data" * 100)},
                # No enhanced_response parameter - should default to simple format
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should only contain transcription field for backward compatibility
            assert "transcription" in data
            assert data["transcription"] == "Hello world"
            assert "segments" not in data
            assert "metadata" not in data


# ---------------------------------------------------------------------------
# Configuration endpoint tests
# ---------------------------------------------------------------------------

class TestAudioConfigEndpoints:
    """Test the audio configuration endpoints."""
    
    def test_get_audio_config(self):
        """Should return current audio configuration."""
        response = client.get("/api/transcribe/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "config" in data
        config = data["config"]
        assert "confidence_threshold" in config
        assert "enable_speaker_identification" in config
        assert "enable_intelligent_buffering" in config
    
    def test_update_audio_config(self):
        """Should update audio configuration."""
        new_config = {
            "confidence_threshold": 0.8,
            "enable_speaker_identification": False,
            "temperature": 0.3,
            "language": "es"
        }
        
        response = client.post("/api/transcribe/config", json=new_config)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Audio configuration updated successfully"
        assert "config" in data
        
        config = data["config"]
        assert config["confidence_threshold"] == 0.8
        assert config["enable_speaker_identification"] is False
        assert config["temperature"] == 0.3
        assert config["language"] == "es"
    
    def test_config_parameter_validation(self):
        """Should validate and clamp configuration parameters."""
        invalid_config = {
            "confidence_threshold": 2.0,  # Should be clamped to 1.0
            "temperature": -1.0,  # Should be clamped to 0.0
            "max_segment_length": 100,  # Should be clamped to 60
        }
        
        response = client.post("/api/transcribe/config", json=invalid_config)
        
        assert response.status_code == 200
        data = response.json()
        
        config = data["config"]
        assert config["confidence_threshold"] == 1.0
        assert config["temperature"] == 0.0
        assert config["max_segment_length"] == 60


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

@given(text=st.text())
@settings(max_examples=50, deadline=None)
def test_property_deduplication_preserves_meaning(text: str):
    """For any text, deduplication should not remove unique content."""
    result = _remove_repetitions(text)
    
    # Result should not be longer than original
    assert len(result) <= len(text)
    
    # If original had content, result should have some content (unless all repetitive)
    if text.strip() and not all(c in " \t\n.,!?" for c in text):
        # Allow empty result only if input was very repetitive
        unique_words = set(text.lower().split())
        if len(unique_words) > 1:
            assert len(result.strip()) > 0


@given(
    transcription=st.text(min_size=1, max_size=100),
    history=st.text(min_size=0, max_size=200)
)
@settings(max_examples=30, deadline=None)
def test_property_history_overlap_consistency(transcription: str, history: str):
    """History overlap detection should be consistent and not produce false positives for unique content."""
    result = _check_conversation_history_overlap(transcription, history)
    
    # Should be boolean
    assert isinstance(result, bool)
    
    # Empty transcription should always be filtered
    if not transcription.strip():
        assert result is True
    
    # If transcription is exactly in history, should be filtered
    if transcription.lower().strip() in history.lower():
        assert result is True


@given(
    segments=st.lists(
        st.fixed_dictionaries({
            "text": st.text(min_size=1, max_size=50),
            "start": st.floats(min_value=0.0, max_value=100.0),
            "end": st.floats(min_value=0.0, max_value=100.0),
            "no_speech_prob": st.floats(min_value=0.0, max_value=1.0)
        }),
        min_size=0,
        max_size=10
    ),
    threshold=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=30, deadline=None)
def test_property_confidence_filtering_respects_threshold(segments, threshold):
    """Confidence filtering should respect the threshold parameter."""
    result = _apply_confidence_filtering(segments, threshold)
    
    # All returned segments should meet the confidence threshold
    for segment in result:
        confidence = 1.0 - segment.no_speech_prob
        assert confidence >= threshold
    
    # Result should not be longer than input
    assert len(result) <= len(segments)