"""
transcript_buffer.py
~~~~~~~~~~~~~~~~~~~
Production-grade transcript buffer service for managing transcript segments
with intelligent processing, speaker detection, and quality control.

This service provides:
- TranscriptSegment class with speaker and timing data
- TranscriptBuffer class for managing transcript segments
- Intelligent buffering for complete sentence processing
- Advanced deduplication and quality control
- Speaker identification and tracking
- Context management for conversation history
"""

import re
import time
import hashlib
from typing import List, Optional, Dict, Any, Set, Tuple
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
from datetime import datetime, timedelta

import numpy as np
from groq import Groq

from core.config import settings

# Import quality monitor (will be imported when needed to avoid circular imports)


@dataclass
class TranscriptSegment:
    """
    Represents a segment of transcribed audio with comprehensive metadata.
    
    Attributes:
        id: Unique identifier for the segment
        text: Transcribed text content
        speaker: Identified speaker (e.g., "Speaker A", "John Doe")
        timestamp: Unix timestamp when segment was created
        start_time: Start time in audio (seconds)
        end_time: End time in audio (seconds)
        confidence: Confidence score from ASR (0.0-1.0)
        no_speech_prob: Probability of no speech (0.0-1.0)
        language: Detected/specified language code
        audio_hash: Hash of source audio for deduplication
        processing_metadata: Additional processing information
    """
    id: str
    text: str
    speaker: Optional[str]
    timestamp: float
    start_time: float
    end_time: float
    confidence: float
    no_speech_prob: float = 0.0
    language: str = "en"
    audio_hash: Optional[str] = None
    processing_metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize processing metadata if not provided."""
        if self.processing_metadata is None:
            self.processing_metadata = {}
    
    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return max(0.0, self.end_time - self.start_time)
    
    @property
    def word_count(self) -> int:
        """Get word count in segment text."""
        return len(self.text.split()) if self.text else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranscriptSegment':
        """Create segment from dictionary representation."""
        return cls(**data)


class TranscriptBuffer:
    """
    Production-grade transcript buffer for managing and processing transcript segments.
    
    Features:
    - Intelligent buffering with sentence boundary detection
    - Advanced deduplication using multiple strategies
    - Speaker identification and tracking
    - Context-aware processing with conversation history
    - Quality control with confidence filtering
    - Performance optimization with caching
    """
    
    def __init__(
        self,
        max_segments: int = 1000,
        max_history_duration: float = 3600.0,  # 1 hour
        confidence_threshold: float = 0.7,
        enable_speaker_identification: bool = True,
        enable_intelligent_buffering: bool = True,
        deduplication_window: int = 10,
        speaker_change_threshold: float = 0.5,
        enable_quality_monitoring: bool = True,
        quality_monitor_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize TranscriptBuffer with configuration.
        
        Args:
            max_segments: Maximum number of segments to keep in buffer
            max_history_duration: Maximum duration of history to maintain (seconds)
            confidence_threshold: Minimum confidence score for segments
            enable_speaker_identification: Whether to perform speaker identification
            enable_intelligent_buffering: Whether to use intelligent sentence buffering
            deduplication_window: Number of recent segments to check for duplicates
            speaker_change_threshold: Threshold for detecting speaker changes
            enable_quality_monitoring: Whether to enable quality monitoring
            quality_monitor_config: Configuration for quality monitor
        """
        self.max_segments = max_segments
        self.max_history_duration = max_history_duration
        self.confidence_threshold = confidence_threshold
        self.enable_speaker_identification = enable_speaker_identification
        self.enable_intelligent_buffering = enable_intelligent_buffering
        self.deduplication_window = deduplication_window
        self.speaker_change_threshold = speaker_change_threshold
        self.enable_quality_monitoring = enable_quality_monitoring
        
        # Core data structures
        self.segments: deque[TranscriptSegment] = deque(maxlen=max_segments)
        self.segment_index: Dict[str, TranscriptSegment] = {}
        self.audio_hashes: Set[str] = set()
        self.text_hashes: Set[str] = set()
        
        # Speaker tracking
        self.speakers: Dict[str, Dict[str, Any]] = {}
        self.current_speaker: Optional[str] = None
        self.speaker_segments: Dict[str, List[str]] = defaultdict(list)
        
        # Processing state
        self.total_duration: float = 0.0
        self.last_processed_time: float = 0.0
        self.processing_stats: Dict[str, Any] = {
            "total_segments": 0,
            "filtered_segments": 0,
            "duplicate_segments": 0,
            "speaker_changes": 0,
            "average_confidence": 0.0,
            "processing_time": 0.0,
        }
        
        # Buffering state
        self.pending_buffer: List[TranscriptSegment] = []
        self.sentence_buffer: str = ""
        self.last_sentence_end: float = 0.0
        
        # Quality monitoring
        self.quality_monitor = None
        if self.enable_quality_monitoring:
            self._initialize_quality_monitor(quality_monitor_config or {})
        
        # Groq client for AI processing
        self._groq_client: Optional[Groq] = None
    
    def _initialize_quality_monitor(self, config: Dict[str, Any]) -> None:
        """Initialize quality monitor with configuration."""
        try:
            from .transcript_quality import create_quality_monitor
            
            self.quality_monitor = create_quality_monitor(
                confidence_threshold=config.get("confidence_threshold", self.confidence_threshold),
                quality_window_size=config.get("quality_window_size", 50),
                alert_thresholds=config.get("alert_thresholds"),
                enable_auto_adjustment=config.get("enable_auto_adjustment", True)
            )
        except ImportError as e:
            print(f"[WARNING] Could not initialize quality monitor: {e}")
            self.enable_quality_monitoring = False
    
    def _get_groq(self) -> Groq:
        """Get or create Groq client instance."""
        if self._groq_client is None:
            self._groq_client = Groq(api_key=settings.groq_api_key)
        return self._groq_client
    
    def _generate_segment_id(self, text: str, timestamp: float) -> str:
        """Generate unique segment ID based on content and timestamp."""
        content = f"{text}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_audio_hash(self, audio_data: bytes) -> str:
        """Generate hash for audio data to detect duplicates."""
        return hashlib.sha256(audio_data).hexdigest()[:16]
    
    def _generate_text_hash(self, text: str) -> str:
        """Generate hash for text content to detect duplicates."""
        normalized_text = re.sub(r'[^\w\s]', '', text.lower()).strip()
        return hashlib.md5(normalized_text.encode()).hexdigest()[:12]
    
    def _cleanup_old_segments(self):
        """Remove old segments based on time and count limits."""
        current_time = time.time()
        
        # Remove segments older than max_history_duration
        while (self.segments and 
               current_time - self.segments[0].timestamp > self.max_history_duration):
            old_segment = self.segments.popleft()
            self._remove_segment_from_indexes(old_segment)
        
        # Update processing stats
        self.processing_stats["total_segments"] = len(self.segments)
    
    def _remove_segment_from_indexes(self, segment: TranscriptSegment):
        """Remove segment from all indexes and tracking structures."""
        # Remove from segment index
        if segment.id in self.segment_index:
            del self.segment_index[segment.id]
        
        # Remove from hash sets
        if segment.audio_hash:
            self.audio_hashes.discard(segment.audio_hash)
        
        text_hash = self._generate_text_hash(segment.text)
        self.text_hashes.discard(text_hash)
        
        # Remove from speaker tracking
        if segment.speaker and segment.id in self.speaker_segments[segment.speaker]:
            self.speaker_segments[segment.speaker].remove(segment.id)
    
    def _detect_sentence_boundaries(self, text: str) -> List[Tuple[int, int]]:
        """
        Detect sentence boundaries in text for intelligent buffering.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of (start, end) positions for each sentence
        """
        if not text:
            return []
        
        # Enhanced sentence boundary detection
        sentence_endings = re.finditer(r'[.!?]+(?:\s+|$)', text)
        boundaries = []
        start = 0
        
        for match in sentence_endings:
            end = match.end()
            if end > start:
                boundaries.append((start, end))
                start = end
        
        # Handle remaining text without sentence ending
        if start < len(text):
            boundaries.append((start, len(text)))
        
        return boundaries
    
    def _is_complete_sentence(self, text: str) -> bool:
        """Check if text represents a complete sentence."""
        if not text or len(text.strip()) < 3:
            return False
        
        text = text.strip()
        
        # Check for sentence ending punctuation
        if re.search(r'[.!?]$', text):
            return True
        
        # Check for common complete phrases
        complete_patterns = [
            r'\b(yes|no|okay|ok|sure|right|exactly|absolutely)\b$',
            r'\b(thank you|thanks|please|sorry|excuse me)\b$',
            r'\b(hello|hi|goodbye|bye|see you)\b$',
        ]
        
        for pattern in complete_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _should_buffer_segment(self, segment: TranscriptSegment) -> bool:
        """
        Determine if segment should be buffered for intelligent processing.
        
        Args:
            segment: Segment to evaluate
            
        Returns:
            True if segment should be buffered, False if it should be processed immediately
        """
        if not self.enable_intelligent_buffering:
            return False
        
        # Don't buffer if confidence is too low
        if segment.confidence < self.confidence_threshold:
            return False
        
        # Don't buffer if text is very short
        if len(segment.text.strip()) < 5:
            return False
        
        # Buffer if sentence is incomplete
        if not self._is_complete_sentence(segment.text):
            return True
        
        # Buffer if there's a very short gap to next segment (likely continuation)
        if (self.pending_buffer and 
            segment.start_time - self.pending_buffer[-1].end_time < 0.5):
            return True
        
        return False
    
    def _merge_buffered_segments(self, segments: List[TranscriptSegment]) -> TranscriptSegment:
        """
        Merge multiple segments into a single coherent segment.
        
        Args:
            segments: List of segments to merge
            
        Returns:
            Merged segment with combined text and metadata
        """
        if not segments:
            raise ValueError("Cannot merge empty segment list")
        
        if len(segments) == 1:
            return segments[0]
        
        # Combine text with proper spacing
        combined_text = " ".join(seg.text.strip() for seg in segments if seg.text.strip())
        
        # Calculate weighted confidence
        total_duration = sum(seg.duration for seg in segments)
        if total_duration > 0:
            weighted_confidence = sum(
                seg.confidence * seg.duration for seg in segments
            ) / total_duration
        else:
            weighted_confidence = sum(seg.confidence for seg in segments) / len(segments)
        
        # Use first segment as base
        base_segment = segments[0]
        
        # Create merged segment
        merged_segment = TranscriptSegment(
            id=self._generate_segment_id(combined_text, base_segment.timestamp),
            text=combined_text,
            speaker=base_segment.speaker,  # Assume same speaker for buffered segments
            timestamp=base_segment.timestamp,
            start_time=base_segment.start_time,
            end_time=segments[-1].end_time,
            confidence=weighted_confidence,
            no_speech_prob=min(seg.no_speech_prob for seg in segments),
            language=base_segment.language,
            audio_hash=base_segment.audio_hash,
            processing_metadata={
                "merged_from": len(segments),
                "original_segments": [seg.id for seg in segments],
                "merge_timestamp": time.time(),
            }
        )
        
        return merged_segment
    
    async def processAudioChunk(
        self,
        audio_data: bytes,
        mime_type: str = "audio/webm",
        context: Optional[Dict[str, Any]] = None
    ) -> List[TranscriptSegment]:
        """
        Process audio chunk with intelligent buffering and quality control.
        
        Args:
            audio_data: Raw audio data bytes
            mime_type: MIME type of audio data
            context: Additional context for processing
            
        Returns:
            List of processed transcript segments
        """
        start_time = time.time()
        
        try:
            # Generate audio hash for deduplication
            audio_hash = self._generate_audio_hash(audio_data)
            
            # Check for duplicate audio
            if audio_hash in self.audio_hashes:
                self.processing_stats["duplicate_segments"] += 1
                return []
            
            # Skip very small audio chunks
            if len(audio_data) < 500:
                return []
            
            # Transcribe audio using Groq Whisper
            import io
            
            # Determine file extension from MIME type
            ext_map = {
                "audio/webm": "webm",
                "audio/wav": "wav",
                "audio/mp3": "mp3",
                "audio/mpeg": "mp3",
                "audio/ogg": "ogg",
                "audio/mp4": "mp4",
            }
            ext = ext_map.get(mime_type, "webm")
            
            # Call Groq Whisper API
            result = self._get_groq().audio.transcriptions.create(
                file=(f"audio.{ext}", io.BytesIO(audio_data), mime_type),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                temperature=0.2,
                language="en",
            )
            
            # Process segments from API response
            raw_segments = getattr(result, "segments", [])
            processed_segments = []
            
            for raw_segment in raw_segments:
                # Create TranscriptSegment
                segment_text = raw_segment.get("text", "").strip()
                if not segment_text or len(segment_text) < 3:
                    continue
                
                confidence = 1.0 - raw_segment.get("no_speech_prob", 0.0)
                
                # Apply confidence filtering
                was_filtered = confidence < self.confidence_threshold
                if was_filtered:
                    self.processing_stats["filtered_segments"] += 1
                    # Track filtered segment for quality monitoring
                    if self.quality_monitor:
                        temp_segment = TranscriptSegment(
                            id=self._generate_segment_id(segment_text, time.time()),
                            text=segment_text,
                            speaker=None,
                            timestamp=time.time(),
                            start_time=raw_segment.get("start", 0.0),
                            end_time=raw_segment.get("end", 0.0),
                            confidence=confidence,
                            no_speech_prob=raw_segment.get("no_speech_prob", 0.0),
                            language="en",
                            audio_hash=audio_hash,
                            processing_metadata={
                                "source": "groq_whisper",
                                "model": "whisper-large-v3-turbo",
                                "processing_timestamp": time.time(),
                            }
                        )
                        self.quality_monitor.track_segment_quality(
                            temp_segment, 
                            time.time() - start_time, 
                            was_filtered=True
                        )
                    continue
                
                # Create segment
                segment = TranscriptSegment(
                    id=self._generate_segment_id(segment_text, time.time()),
                    text=segment_text,
                    speaker=None,  # Will be identified later
                    timestamp=time.time(),
                    start_time=raw_segment.get("start", 0.0),
                    end_time=raw_segment.get("end", 0.0),
                    confidence=confidence,
                    no_speech_prob=raw_segment.get("no_speech_prob", 0.0),
                    language="en",
                    audio_hash=audio_hash,
                    processing_metadata={
                        "source": "groq_whisper",
                        "model": "whisper-large-v3-turbo",
                        "processing_timestamp": time.time(),
                    }
                )
                
                # Identify speaker if enabled
                if self.enable_speaker_identification:
                    segment.speaker = self.identifySpeakers([segment])[0].speaker
                
                # Track segment quality if monitoring is enabled
                if self.quality_monitor:
                    segment_processing_time = time.time() - start_time
                    self.quality_monitor.track_segment_quality(
                        segment, 
                        segment_processing_time, 
                        was_filtered=False
                    )
                
                processed_segments.append(segment)
            
            # Add to buffer and process
            for segment in processed_segments:
                self._add_segment_to_buffer(segment)
            
            # Process buffered segments
            final_segments = self._process_buffered_segments()
            
            # Update processing stats
            processing_time = time.time() - start_time
            self.processing_stats["processing_time"] += processing_time
            self.processing_stats["total_segments"] = len(self.segments)
            
            # Add audio hash to prevent duplicates
            self.audio_hashes.add(audio_hash)
            
            return final_segments
            
        except Exception as e:
            print(f"[ERROR] TranscriptBuffer.processAudioChunk failed: {e}")
            return []
    
    def _add_segment_to_buffer(self, segment: TranscriptSegment):
        """Add segment to appropriate buffer based on processing strategy."""
        if self._should_buffer_segment(segment):
            self.pending_buffer.append(segment)
        else:
            # Process immediately
            if self.pending_buffer:
                # Flush pending buffer first
                self.pending_buffer.append(segment)
                self._flush_pending_buffer()
            else:
                # Add directly to main buffer
                self._add_segment_to_main_buffer(segment)
    
    def _process_buffered_segments(self) -> List[TranscriptSegment]:
        """Process and return any completed segments from buffer."""
        completed_segments = []
        
        # Check if we should flush the buffer
        if (self.pending_buffer and 
            (len(self.pending_buffer) >= 5 or  # Buffer is getting full
             time.time() - self.pending_buffer[0].timestamp > 10.0)):  # Buffer is getting old
            completed_segments.extend(self._flush_pending_buffer())
        
        return completed_segments
    
    def _flush_pending_buffer(self) -> List[TranscriptSegment]:
        """Flush pending buffer and return processed segments."""
        if not self.pending_buffer:
            return []
        
        # Merge buffered segments if appropriate
        if len(self.pending_buffer) > 1 and self.enable_intelligent_buffering:
            merged_segment = self._merge_buffered_segments(self.pending_buffer)
            self._add_segment_to_main_buffer(merged_segment)
            self.pending_buffer.clear()
            return [merged_segment]
        else:
            # Add segments individually
            segments = list(self.pending_buffer)
            for segment in segments:
                self._add_segment_to_main_buffer(segment)
            self.pending_buffer.clear()
            return segments
    
    def _add_segment_to_main_buffer(self, segment: TranscriptSegment):
        """Add segment to main buffer with deduplication."""
        # Check for text-based duplicates
        text_hash = self._generate_text_hash(segment.text)
        if text_hash in self.text_hashes:
            self.processing_stats["duplicate_segments"] += 1
            return
        
        # Add to main structures
        self.segments.append(segment)
        self.segment_index[segment.id] = segment
        self.text_hashes.add(text_hash)
        
        # Update speaker tracking
        if segment.speaker:
            # Initialize speaker info if not exists
            if segment.speaker not in self.speakers:
                self.speakers[segment.speaker] = {
                    "first_seen": segment.timestamp,
                    "total_segments": 0,
                    "total_duration": 0.0,
                    "average_confidence": 0.0,
                    "speaking_patterns": [],
                }
            
            # Update speaker statistics
            speaker_info = self.speakers[segment.speaker]
            speaker_info["total_segments"] += 1
            speaker_info["total_duration"] += segment.duration
            speaker_info["average_confidence"] = (
                (speaker_info["average_confidence"] * (speaker_info["total_segments"] - 1) + segment.confidence) /
                speaker_info["total_segments"]
            )
            
            self.speaker_segments[segment.speaker].append(segment.id)
            self.current_speaker = segment.speaker
        
        # Update duration
        self.total_duration += segment.duration
        self.last_processed_time = segment.timestamp
        
        # Cleanup old segments
        self._cleanup_old_segments()
    
    def deduplicateSegments(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """
        Advanced deduplication method for quality control.
        
        Uses multiple strategies:
        1. Exact text matching
        2. Fuzzy text similarity
        3. Audio hash comparison
        4. Temporal overlap detection
        5. Speaker consistency checking
        
        Args:
            segments: List of segments to deduplicate
            
        Returns:
            Deduplicated list of segments
        """
        if not segments:
            return []
        
        deduplicated = []
        seen_hashes = set()
        seen_texts = set()
        
        for segment in segments:
            # Skip if we've seen this exact text
            text_hash = self._generate_text_hash(segment.text)
            if text_hash in seen_texts:
                self.processing_stats["duplicate_segments"] += 1
                continue
            
            # Skip if we've seen this audio hash
            if segment.audio_hash and segment.audio_hash in seen_hashes:
                self.processing_stats["duplicate_segments"] += 1
                continue
            
            # Check for fuzzy duplicates against recent segments
            is_duplicate = False
            for recent_segment in deduplicated[-self.deduplication_window:]:
                if self._are_segments_similar(segment, recent_segment):
                    self.processing_stats["duplicate_segments"] += 1
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(segment)
                seen_texts.add(text_hash)
                if segment.audio_hash:
                    seen_hashes.add(segment.audio_hash)
        
        return deduplicated
    
    def _are_segments_similar(self, seg1: TranscriptSegment, seg2: TranscriptSegment, threshold: float = 0.85) -> bool:
        """
        Check if two segments are similar enough to be considered duplicates.
        
        Args:
            seg1, seg2: Segments to compare
            threshold: Similarity threshold (0.0-1.0)
            
        Returns:
            True if segments are similar enough to be duplicates
        """
        # Exact text match
        if seg1.text.strip().lower() == seg2.text.strip().lower():
            return True
        
        # Audio hash match
        if seg1.audio_hash and seg2.audio_hash and seg1.audio_hash == seg2.audio_hash:
            return True
        
        # Temporal overlap check
        if (abs(seg1.start_time - seg2.start_time) < 1.0 and 
            abs(seg1.end_time - seg2.end_time) < 1.0):
            # Check text similarity for overlapping segments
            similarity = self._calculate_text_similarity(seg1.text, seg2.text)
            if similarity > threshold:
                return True
        
        # Fuzzy text similarity for same speaker
        if (seg1.speaker and seg2.speaker and seg1.speaker == seg2.speaker):
            similarity = self._calculate_text_similarity(seg1.text, seg2.text)
            if similarity > threshold:
                return True
        
        return False
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings using word overlap.
        
        Args:
            text1, text2: Texts to compare
            
        Returns:
            Similarity score (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        words1 = set(re.sub(r'[^\w\s]', '', text1.lower()).split())
        words2 = set(re.sub(r'[^\w\s]', '', text2.lower()).split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def identifySpeakers(self, segments: List[TranscriptSegment]) -> List[TranscriptSegment]:
        """
        Enhanced speaker identification method for speaker detection.
        
        Uses multiple strategies:
        1. Audio characteristics analysis (simplified)
        2. Temporal patterns and silence gaps
        3. Speaking style consistency
        4. Context-based speaker tracking
        
        Args:
            segments: List of segments to process for speaker identification
            
        Returns:
            Segments with updated speaker information
        """
        if not segments or not self.enable_speaker_identification:
            return segments
        
        identified_segments = []
        
        for i, segment in enumerate(segments):
            # If segment already has a speaker assigned, keep it unless we detect a change
            if segment.speaker:
                identified_speaker = segment.speaker
            else:
                # Start with current speaker as default
                identified_speaker = self.current_speaker or "Speaker A"
                
                # Check for speaker change indicators
                if self._should_change_speaker(segment, segments[:i]):
                    # Determine new speaker
                    if self.current_speaker == "Speaker A":
                        identified_speaker = "Speaker B"
                    elif self.current_speaker == "Speaker B":
                        identified_speaker = "Speaker A"
                    else:
                        # First speaker assignment
                        identified_speaker = "Speaker A"
                    
                    self.processing_stats["speaker_changes"] += 1
            
            # Update segment with identified speaker
            segment.speaker = identified_speaker
            
            # Update speaker tracking
            if identified_speaker not in self.speakers:
                self.speakers[identified_speaker] = {
                    "first_seen": segment.timestamp,
                    "total_segments": 0,
                    "total_duration": 0.0,
                    "average_confidence": 0.0,
                    "speaking_patterns": [],
                }
            
            # Update speaker statistics
            speaker_info = self.speakers[identified_speaker]
            speaker_info["total_segments"] += 1
            speaker_info["total_duration"] += segment.duration
            speaker_info["average_confidence"] = (
                (speaker_info["average_confidence"] * (speaker_info["total_segments"] - 1) + segment.confidence) /
                speaker_info["total_segments"]
            )
            
            self.current_speaker = identified_speaker
            identified_segments.append(segment)
        
        return identified_segments
    
    def _should_change_speaker(self, segment: TranscriptSegment, previous_segments: List[TranscriptSegment]) -> bool:
        """
        Determine if speaker should change based on various indicators.
        
        Args:
            segment: Current segment to analyze
            previous_segments: Previous segments for context
            
        Returns:
            True if speaker should change
        """
        if not previous_segments:
            return False  # Keep current speaker for first segment
        
        last_segment = previous_segments[-1]
        
        # Check for significant silence gap (potential speaker change)
        silence_gap = segment.start_time - last_segment.end_time
        if silence_gap > 2.0:  # 2+ seconds of silence
            return True
        
        # Check for audio characteristics change (simplified heuristic)
        if (segment.no_speech_prob < 0.1 and last_segment.no_speech_prob > 0.3):
            return True
        
        # Check for speaking pattern changes
        if self._detect_speaking_pattern_change(segment, previous_segments[-3:]):
            return True
        
        # Check for confidence score patterns
        if (segment.confidence > 0.9 and 
            len(previous_segments) >= 2 and
            all(seg.confidence < 0.7 for seg in previous_segments[-2:])):
            return True
        
        return False
    
    def _detect_speaking_pattern_change(self, segment: TranscriptSegment, recent_segments: List[TranscriptSegment]) -> bool:
        """
        Detect changes in speaking patterns that might indicate speaker change.
        
        Args:
            segment: Current segment
            recent_segments: Recent segments for pattern analysis
            
        Returns:
            True if speaking pattern suggests speaker change
        """
        if len(recent_segments) < 2:
            return False
        
        # Analyze speech rate (words per second)
        current_rate = segment.word_count / max(segment.duration, 0.1)
        recent_rates = [seg.word_count / max(seg.duration, 0.1) for seg in recent_segments]
        avg_recent_rate = sum(recent_rates) / len(recent_rates)
        
        # Significant change in speech rate
        if abs(current_rate - avg_recent_rate) > avg_recent_rate * 0.5:
            return True
        
        # Analyze text complexity (average word length)
        current_complexity = sum(len(word) for word in segment.text.split()) / max(segment.word_count, 1)
        recent_complexities = []
        for seg in recent_segments:
            if seg.word_count > 0:
                complexity = sum(len(word) for word in seg.text.split()) / seg.word_count
                recent_complexities.append(complexity)
        
        if recent_complexities:
            avg_recent_complexity = sum(recent_complexities) / len(recent_complexities)
            if abs(current_complexity - avg_recent_complexity) > 1.5:
                return True
        
        return False
    
    def getTranscriptHistory(
        self,
        max_segments: Optional[int] = None,
        time_window: Optional[float] = None,
        speaker_filter: Optional[str] = None,
        confidence_threshold: Optional[float] = None
    ) -> List[TranscriptSegment]:
        """
        Retrieve transcript history with flexible filtering options.
        
        Args:
            max_segments: Maximum number of segments to return
            time_window: Time window in seconds (from now backwards)
            speaker_filter: Filter by specific speaker
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            Filtered list of transcript segments
        """
        current_time = time.time()
        filtered_segments = []
        
        for segment in reversed(self.segments):
            # Apply time window filter
            if time_window and (current_time - segment.timestamp) > time_window:
                break
            
            # Apply speaker filter
            if speaker_filter and segment.speaker != speaker_filter:
                continue
            
            # Apply confidence filter
            if confidence_threshold and segment.confidence < confidence_threshold:
                continue
            
            filtered_segments.append(segment)
            
            # Apply max segments limit
            if max_segments and len(filtered_segments) >= max_segments:
                break
        
        # Return in chronological order
        return list(reversed(filtered_segments))
    
    def get_conversation_context(self, max_words: int = 500) -> str:
        """
        Get recent conversation context as a single string.
        
        Args:
            max_words: Maximum number of words to include
            
        Returns:
            Conversation context string
        """
        recent_segments = self.getTranscriptHistory(max_segments=20)
        
        context_parts = []
        word_count = 0
        
        for segment in recent_segments:
            segment_words = segment.word_count
            if word_count + segment_words > max_words:
                break
            
            if segment.speaker:
                context_parts.append(f"{segment.speaker}: {segment.text}")
            else:
                context_parts.append(segment.text)
            
            word_count += segment_words
        
        return " ".join(context_parts)
    
    def get_speaker_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive statistics about identified speakers.
        
        Returns:
            Dictionary with speaker statistics
        """
        stats = {}
        
        for speaker_id, speaker_info in self.speakers.items():
            stats[speaker_id] = {
                "total_segments": speaker_info["total_segments"],
                "total_duration": round(speaker_info["total_duration"], 2),
                "average_confidence": round(speaker_info["average_confidence"], 3),
                "first_seen": speaker_info["first_seen"],
                "percentage_of_conversation": round(
                    (speaker_info["total_duration"] / max(self.total_duration, 0.1)) * 100, 1
                ),
                "words_per_minute": round(
                    sum(self.segment_index[seg_id].word_count 
                        for seg_id in self.speaker_segments[speaker_id] 
                        if seg_id in self.segment_index) / 
                    max(speaker_info["total_duration"] / 60, 0.1), 1
                ) if speaker_info["total_duration"] > 0 else 0,
            }
        
        return stats
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        current_time = time.time()
        
        # Calculate average confidence
        if self.segments:
            avg_confidence = sum(seg.confidence for seg in self.segments) / len(self.segments)
        else:
            avg_confidence = 0.0
        
        return {
            **self.processing_stats,
            "buffer_size": len(self.segments),
            "pending_buffer_size": len(self.pending_buffer),
            "total_duration": round(self.total_duration, 2),
            "unique_speakers": len(self.speakers),
            "average_confidence": round(avg_confidence, 3),
            "segments_per_minute": round(
                len(self.segments) / max((current_time - self.last_processed_time) / 60, 0.1), 1
            ) if self.segments else 0,
            "deduplication_rate": round(
                (self.processing_stats["duplicate_segments"] / 
                 max(self.processing_stats["total_segments"] + self.processing_stats["duplicate_segments"], 1)) * 100, 1
            ),
            "filter_rate": round(
                (self.processing_stats["filtered_segments"] / 
                 max(self.processing_stats["total_segments"] + self.processing_stats["filtered_segments"], 1)) * 100, 1
            ),
        }
    
    def clear_buffer(self):
        """Clear all segments and reset buffer state."""
        self.segments.clear()
        self.segment_index.clear()
        self.audio_hashes.clear()
        self.text_hashes.clear()
        self.speakers.clear()
        self.speaker_segments.clear()
        self.pending_buffer.clear()
        
        self.current_speaker = None
        self.total_duration = 0.0
        self.last_processed_time = 0.0
        self.sentence_buffer = ""
        self.last_sentence_end = 0.0
        
        # Reset stats
        self.processing_stats = {
            "total_segments": 0,
            "filtered_segments": 0,
            "duplicate_segments": 0,
            "speaker_changes": 0,
            "average_confidence": 0.0,
            "processing_time": 0.0,
        }
        
        # Reset quality monitor if enabled
        if self.quality_monitor:
            self.quality_monitor.reset_session_metrics()
    
    def get_quality_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get current quality metrics from the quality monitor.
        
        Returns:
            Quality metrics dictionary or None if monitoring is disabled
        """
        if not self.quality_monitor:
            return None
        
        return self.quality_monitor.get_current_metrics().to_dict()
    
    def get_session_quality_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get session quality metrics from the quality monitor.
        
        Returns:
            Session quality metrics dictionary or None if monitoring is disabled
        """
        if not self.quality_monitor:
            return None
        
        return self.quality_monitor.get_session_metrics().to_dict()
    
    def get_quality_alerts(self) -> List[Dict[str, Any]]:
        """
        Get active quality alerts.
        
        Returns:
            List of active quality alerts or empty list if monitoring is disabled
        """
        if not self.quality_monitor:
            return []
        
        return [alert.to_dict() for alert in self.quality_monitor.get_active_alerts()]
    
    def get_quality_report(self) -> Optional[Dict[str, Any]]:
        """
        Generate comprehensive quality report.
        
        Returns:
            Quality report dictionary or None if monitoring is disabled
        """
        if not self.quality_monitor:
            return None
        
        return self.quality_monitor.generate_quality_report()
    
    def validate_transcript_completeness(
        self, 
        expected_duration: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate transcript completeness.
        
        Args:
            expected_duration: Expected audio duration in seconds
            
        Returns:
            Validation results or None if monitoring is disabled
        """
        if not self.quality_monitor:
            return None
        
        return self.quality_monitor.validate_transcript_completeness(
            list(self.segments), 
            expected_duration
        )
    
    def export_segments(self, format: str = "json") -> str:
        """
        Export segments in various formats.
        
        Args:
            format: Export format ("json", "csv", "txt")
            
        Returns:
            Exported data as string
        """
        if format == "json":
            import json
            segments_data = [seg.to_dict() for seg in self.segments]
            return json.dumps({
                "segments": segments_data,
                "statistics": self.get_processing_statistics(),
                "speakers": self.get_speaker_statistics(),
                "export_timestamp": time.time(),
            }, indent=2)
        
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "id", "text", "speaker", "timestamp", "start_time", "end_time",
                "confidence", "duration", "word_count"
            ])
            
            # Write segments
            for seg in self.segments:
                writer.writerow([
                    seg.id, seg.text, seg.speaker or "", seg.timestamp,
                    seg.start_time, seg.end_time, seg.confidence,
                    seg.duration, seg.word_count
                ])
            
            return output.getvalue()
        
        elif format == "txt":
            lines = []
            current_speaker = None
            
            for seg in self.segments:
                if seg.speaker != current_speaker:
                    if current_speaker is not None:
                        lines.append("")  # Add blank line between speakers
                    lines.append(f"{seg.speaker or 'Unknown'}:")
                    current_speaker = seg.speaker
                
                timestamp = datetime.fromtimestamp(seg.timestamp).strftime("%H:%M:%S")
                lines.append(f"[{timestamp}] {seg.text}")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Factory function for creating TranscriptBuffer instances
def create_transcript_buffer(**kwargs) -> TranscriptBuffer:
    """
    Factory function to create TranscriptBuffer with default production settings.
    
    Args:
        **kwargs: Override default configuration parameters
        
    Returns:
        Configured TranscriptBuffer instance
    """
    default_config = {
        "max_segments": 1000,
        "max_history_duration": 3600.0,  # 1 hour
        "confidence_threshold": 0.7,
        "enable_speaker_identification": True,
        "enable_intelligent_buffering": True,
        "deduplication_window": 10,
        "speaker_change_threshold": 0.5,
        "enable_quality_monitoring": True,
        "quality_monitor_config": {
            "quality_window_size": 50,
            "enable_auto_adjustment": True,
            "alert_thresholds": {
                "confidence_drop": 0.1,
                "latency_spike": 2.0,
                "accuracy_degradation": 0.15,
                "completion_rate_drop": 0.2
            }
        }
    }
    
    # Override defaults with provided kwargs
    config = {**default_config, **kwargs}
    
    return TranscriptBuffer(**config)