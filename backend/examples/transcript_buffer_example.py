#!/usr/bin/env python3
"""
transcript_buffer_example.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Example demonstrating the TranscriptBuffer service integration with the existing MeetNova system.

This example shows how to:
1. Create and configure a TranscriptBuffer
2. Process audio chunks with intelligent buffering
3. Manage speaker identification
4. Export transcript data
5. Integrate with existing AI services
"""

import asyncio
import time
from typing import List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the new TranscriptBuffer service
from services.transcript_buffer import (
    TranscriptBuffer,
    TranscriptSegment,
    create_transcript_buffer
)


async def demonstrate_transcript_buffer():
    """Demonstrate TranscriptBuffer functionality."""
    print("=== TranscriptBuffer Service Demonstration ===\n")
    
    # 1. Create a production-configured TranscriptBuffer
    print("1. Creating TranscriptBuffer with production settings...")
    buffer = create_transcript_buffer(
        max_segments=500,
        confidence_threshold=0.75,
        enable_speaker_identification=True,
        enable_intelligent_buffering=True
    )
    print(f"   Buffer created with {buffer.max_segments} max segments")
    print(f"   Confidence threshold: {buffer.confidence_threshold}")
    print(f"   Speaker identification: {buffer.enable_speaker_identification}")
    print()
    
    # 2. Simulate processing audio chunks (in real usage, these would come from the frontend)
    print("2. Simulating audio chunk processing...")
    
    # Create sample transcript segments (normally these would come from Groq Whisper)
    sample_segments = [
        TranscriptSegment(
            id="seg_1",
            text="Hello everyone, welcome to today's meeting",
            speaker="Speaker A",
            timestamp=time.time(),
            start_time=0.0,
            end_time=3.0,
            confidence=0.95,
            processing_metadata={"source": "example"}
        ),
        TranscriptSegment(
            id="seg_2", 
            text="Thank you for having me, I'm excited to be here",
            speaker="Speaker B",
            timestamp=time.time() + 1,
            start_time=4.0,
            end_time=7.5,
            confidence=0.88,
            processing_metadata={"source": "example"}
        ),
        TranscriptSegment(
            id="seg_3",
            text="Let's start with the quarterly review",
            speaker="Speaker A", 
            timestamp=time.time() + 2,
            start_time=8.0,
            end_time=11.0,
            confidence=0.92,
            processing_metadata={"source": "example"}
        ),
        TranscriptSegment(
            id="seg_4",
            text="I have all the numbers ready to present",
            speaker="Speaker B",
            timestamp=time.time() + 3,
            start_time=12.0,
            end_time=15.0,
            confidence=0.90,
            processing_metadata={"source": "example"}
        )
    ]
    
    # Add segments to buffer (simulating real-time processing)
    for i, segment in enumerate(sample_segments):
        print(f"   Processing segment {i+1}: '{segment.text[:30]}...'")
        buffer._add_segment_to_main_buffer(segment)
        await asyncio.sleep(0.1)  # Simulate processing delay
    
    print(f"   Processed {len(sample_segments)} segments")
    print()
    
    # 3. Demonstrate deduplication
    print("3. Testing deduplication functionality...")
    
    # Create a duplicate segment
    duplicate_segment = TranscriptSegment(
        id="seg_dup",
        text="Hello everyone, welcome to today's meeting",  # Same as seg_1
        speaker="Speaker A",
        timestamp=time.time(),
        start_time=16.0,
        end_time=19.0,
        confidence=0.85
    )
    
    segments_with_duplicate = sample_segments + [duplicate_segment]
    deduplicated = buffer.deduplicateSegments(segments_with_duplicate)
    
    print(f"   Original segments: {len(segments_with_duplicate)}")
    print(f"   After deduplication: {len(deduplicated)}")
    print(f"   Duplicates removed: {len(segments_with_duplicate) - len(deduplicated)}")
    print()
    
    # 4. Demonstrate speaker identification
    print("4. Testing speaker identification...")
    
    # Create segments without speaker info
    segments_no_speaker = []
    for i, seg in enumerate(sample_segments[:2]):
        new_seg = TranscriptSegment(
            id=f"no_speaker_{i}",
            text=seg.text,
            speaker=None,  # No speaker assigned
            timestamp=seg.timestamp,
            start_time=seg.start_time,
            end_time=seg.end_time,
            confidence=seg.confidence
        )
        segments_no_speaker.append(new_seg)
    
    identified_segments = buffer.identifySpeakers(segments_no_speaker)
    
    print("   Segments before speaker identification:")
    for seg in segments_no_speaker:
        print(f"     '{seg.text[:30]}...' -> Speaker: {seg.speaker}")
    
    print("   Segments after speaker identification:")
    for seg in identified_segments:
        print(f"     '{seg.text[:30]}...' -> Speaker: {seg.speaker}")
    print()
    
    # 5. Demonstrate conversation history retrieval
    print("5. Testing conversation history retrieval...")
    
    # Get full history
    full_history = buffer.getTranscriptHistory()
    print(f"   Full history: {len(full_history)} segments")
    
    # Get limited history
    recent_history = buffer.getTranscriptHistory(max_segments=2)
    print(f"   Recent history (max 2): {len(recent_history)} segments")
    
    # Get speaker-specific history
    speaker_a_history = buffer.getTranscriptHistory(speaker_filter="Speaker A")
    print(f"   Speaker A history: {len(speaker_a_history)} segments")
    
    # Get high-confidence history
    high_conf_history = buffer.getTranscriptHistory(confidence_threshold=0.9)
    print(f"   High confidence history (>0.9): {len(high_conf_history)} segments")
    print()
    
    # 6. Demonstrate conversation context generation
    print("6. Testing conversation context generation...")
    
    context = buffer.get_conversation_context(max_words=50)
    print(f"   Conversation context (50 words max):")
    print(f"   '{context}'")
    print()
    
    # 7. Demonstrate statistics collection
    print("7. Testing statistics collection...")
    
    processing_stats = buffer.get_processing_statistics()
    print("   Processing Statistics:")
    for key, value in processing_stats.items():
        print(f"     {key}: {value}")
    print()
    
    speaker_stats = buffer.get_speaker_statistics()
    print("   Speaker Statistics:")
    for speaker, stats in speaker_stats.items():
        print(f"     {speaker}:")
        for key, value in stats.items():
            print(f"       {key}: {value}")
    print()
    
    # 8. Demonstrate export functionality
    print("8. Testing export functionality...")
    
    # Export as JSON
    json_export = buffer.export_segments("json")
    print(f"   JSON export length: {len(json_export)} characters")
    
    # Export as CSV
    csv_export = buffer.export_segments("csv")
    csv_lines = csv_export.strip().split('\n')
    print(f"   CSV export: {len(csv_lines)} lines (including header)")
    
    # Export as TXT
    txt_export = buffer.export_segments("txt")
    print(f"   TXT export length: {len(txt_export)} characters")
    print("   TXT export preview:")
    print("   " + txt_export[:200] + "..." if len(txt_export) > 200 else txt_export)
    print()
    
    # 9. Integration with existing AI services example
    print("9. Integration example with existing AI services...")
    
    # Get conversation context for AI processing
    ai_context = buffer.get_conversation_context(max_words=200)
    print(f"   Context for AI processing: {len(ai_context.split())} words")
    
    # This context could be used with:
    # - TaskDetector for enhanced task detection
    # - Summary generation for better context
    # - Real-time WebSocket updates
    print("   This context can be used for:")
    print("     - Enhanced task detection with conversation history")
    print("     - Better AI summary generation")
    print("     - Real-time WebSocket updates to frontend")
    print("     - Context-aware speaker identification")
    print()
    
    print("=== TranscriptBuffer Demonstration Complete ===")


def demonstrate_integration_patterns():
    """Demonstrate integration patterns with existing MeetNova services."""
    print("\n=== Integration Patterns with Existing Services ===\n")
    
    print("1. Integration with AI Router (/api/transcribe):")
    print("   - Replace simple transcription with TranscriptBuffer.processAudioChunk()")
    print("   - Use intelligent buffering for better sentence completion")
    print("   - Apply advanced deduplication to reduce ASR hallucinations")
    print("   - Add speaker identification to transcript segments")
    print()
    
    print("2. Integration with TaskDetector service:")
    print("   - Use buffer.get_conversation_context() for better task detection")
    print("   - Leverage speaker information for assignee identification")
    print("   - Use segment confidence scores for task confidence calculation")
    print()
    
    print("3. Integration with WebSocket system:")
    print("   - Stream TranscriptSegments in real-time to connected clients")
    print("   - Include speaker information and confidence scores")
    print("   - Send processing statistics for UI indicators")
    print()
    
    print("4. Integration with Database (MongoDB):")
    print("   - Store TranscriptSegments with full metadata")
    print("   - Index by speaker, timestamp, and confidence for efficient queries")
    print("   - Export conversation history for report generation")
    print()
    
    print("5. Performance Considerations:")
    print("   - Buffer automatically manages memory with configurable limits")
    print("   - Intelligent cleanup of old segments")
    print("   - Efficient deduplication with multiple strategies")
    print("   - Optimized for real-time processing with <500ms latency")
    print()


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_transcript_buffer())
    
    # Show integration patterns
    demonstrate_integration_patterns()
    
    print("\nFor more details, see:")
    print("- services/transcript_buffer.py - Main implementation")
    print("- tests/test_transcript_buffer.py - Comprehensive test suite")
    print("- Task 2.2 requirements in .kiro/specs/meetnova-production-upgrade/")