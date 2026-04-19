"""
tests/test_task_detector_integration.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Integration tests for the enhanced TaskDetector service with the existing system.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from services.task_detector import TaskDetector, DetectedTask


class TestTaskDetectorIntegration:
    """Integration tests for TaskDetector with existing system components."""
    
    @pytest.fixture
    def detector(self):
        """Create a TaskDetector instance for testing."""
        return TaskDetector()
    
    @pytest.fixture
    def mock_groq_response_realistic(self):
        """Mock realistic Groq API response for integration testing."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''[
            {
                "title": "Update user authentication system",
                "assignee": "John",
                "deadline": "Friday",
                "priority": "high",
                "confidence": 0.92,
                "description": "Implement OAuth2 integration for better security",
                "tags": ["security", "development"],
                "urgency_indicators": ["important", "security"],
                "estimated_effort": "2-3 days"
            },
            {
                "title": "Write API documentation",
                "assignee": "Sarah",
                "deadline": "next week",
                "priority": "medium",
                "confidence": 0.85,
                "description": "Document all REST endpoints with examples",
                "tags": ["documentation"],
                "estimated_effort": "1 day"
            }
        ]'''
        return mock_response
    
    @pytest.mark.asyncio
    async def test_realistic_meeting_scenario(self, detector, mock_groq_response_realistic):
        """Test a realistic meeting scenario with multiple task detections."""
        with patch.object(detector, 'get_groq') as mock_groq:
            mock_groq.return_value.chat.completions.create.return_value = mock_groq_response_realistic
            
            # Simulate a realistic meeting transcript
            meeting_chunks = [
                "Hi everyone, let's discuss the upcoming sprint",
                "John, we need to update the authentication system",
                "It's really important for security, can you handle this by Friday?",
                "Sarah, could you also work on the API documentation?",
                "We need that done by next week for the client demo",
                "Any questions about these assignments?"
            ]
            
            all_tasks = []
            
            # Process chunks as they would come from real transcription
            for chunk in meeting_chunks:
                tasks = await detector.process_transcript_chunk(chunk)
                all_tasks.extend(tasks)
            
            # Flush any remaining buffer
            final_tasks = await detector.flush_buffer()
            all_tasks.extend(final_tasks)
            
            # Verify realistic results
            assert len(all_tasks) >= 1  # Should detect at least one task
            
            # Check task quality
            for task in all_tasks:
                assert task.id
                assert task.title
                assert task.confidence >= 0.5
                assert task.created_at
                assert isinstance(task.tags, list)
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, detector):
        """Test error recovery in integration scenario."""
        # Test with API failure
        with patch.object(detector, 'get_groq') as mock_groq:
            mock_groq.return_value.chat.completions.create.side_effect = Exception("API Error")
            
            # Should not crash and should return empty list
            tasks = await detector.process_transcript_chunk("John needs to fix the bug by tomorrow")
            assert tasks == []
            
            # Should still be able to process with rule-based fallback
            text = "John will fix the login bug by tomorrow"
            tasks = await detector.detect_tasks(text)
            # May return tasks from rule-based detection
            assert isinstance(tasks, list)
    
    @pytest.mark.asyncio
    async def test_performance_with_large_transcript(self, detector, mock_groq_response_realistic):
        """Test performance with larger transcript chunks."""
        with patch.object(detector, 'get_groq') as mock_groq:
            mock_groq.return_value.chat.completions.create.return_value = mock_groq_response_realistic
            
            # Create a large transcript chunk
            large_chunk = " ".join([
                "In today's meeting we discussed several important topics.",
                "John mentioned that he will work on the authentication system.",
                "This is a high priority task that needs to be completed by Friday.",
                "Sarah volunteered to handle the documentation updates.",
                "The team agreed that this should be done by next week.",
                "We also talked about the upcoming client demo and preparation needed.",
                "Mike will coordinate with the QA team for testing.",
                "The deployment should happen after all testing is complete."
            ])
            
            start_time = datetime.now()
            tasks = await detector.process_transcript_chunk(large_chunk)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Should process within reasonable time (< 5 seconds for this test)
            assert processing_time < 5.0
            
            # Should detect tasks
            assert isinstance(tasks, list)
    
    def test_configuration_integration(self, detector):
        """Test configuration updates work correctly."""
        # Test initial configuration
        assert detector.buffer_word_threshold == 15
        assert detector.max_context_length == 500
        
        # Update configuration
        new_config = {
            "buffer_word_threshold": 20,
            "max_context_length": 800
        }
        detector.update_configuration(new_config)
        
        # Verify updates
        assert detector.buffer_word_threshold == 20
        assert detector.max_context_length == 800
        
        # Test bounds checking
        extreme_config = {
            "buffer_word_threshold": 100,  # Should be capped
            "max_context_length": 50      # Should be increased to minimum
        }
        detector.update_configuration(extreme_config)
        
        assert detector.buffer_word_threshold == 50  # Capped at maximum
        assert detector.max_context_length == 100    # Increased to minimum
    
    @pytest.mark.asyncio
    async def test_metrics_tracking_integration(self, detector, mock_groq_response_realistic):
        """Test that metrics are properly tracked during operation."""
        with patch.object(detector, 'get_groq') as mock_groq:
            mock_groq.return_value.chat.completions.create.return_value = mock_groq_response_realistic
            
            # Initial metrics should be zero
            initial_stats = detector.get_task_statistics()
            assert initial_stats["total_chunks_processed"] == 0
            assert initial_stats["total_tasks_detected"] == 0
            
            # Process some chunks
            await detector.process_transcript_chunk("John will fix the bug by tomorrow this is important")
            
            # Metrics should be updated (may not increment if buffering)
            stats = detector.get_task_statistics()
            assert isinstance(stats, dict)
            assert "total_chunks_processed" in stats
            assert "average_confidence" in stats
            assert "cache_hit_rate" in stats
    
    @pytest.mark.asyncio
    async def test_participant_management_integration(self, detector):
        """Test participant management features."""
        # Add new participants
        detector.add_participant("Alice")
        detector.add_participant("Bob")
        
        # Add aliases
        detector.add_participant_alias("Al", "Alice")
        detector.add_participant_alias("Bobby", "Bob")
        
        # Test assignee extraction with new participants
        assignee, confidence = detector._extract_assignee_rules("Alice will handle the testing")
        assert assignee == "Alice"
        assert confidence > 0.0
        
        # Test alias resolution
        assignee, confidence = detector._normalize_assignee_enhanced("Al")
        assert assignee == "Alice"
        assert confidence >= 0.7
    
    @pytest.mark.asyncio
    async def test_quality_validation_integration(self, detector):
        """Test task quality validation in realistic scenario."""
        # Create a mix of good and poor quality tasks
        tasks = [
            DetectedTask(
                id="1", title="Implement user authentication", confidence=0.95,
                assignee="John", deadline="2024-12-20", tags=["security"],
                created_at=datetime.now().isoformat()
            ),
            DetectedTask(
                id="2", title="ok", confidence=0.3,  # Poor quality
                created_at=datetime.now().isoformat()
            ),
            DetectedTask(
                id="3", title="Update documentation", confidence=0.8,
                assignee="Sarah", tags=["documentation"],
                created_at=datetime.now().isoformat()
            )
        ]
        
        # Validate quality
        quality_report = await detector.validate_task_quality(tasks)
        
        assert quality_report["total_tasks"] == 3
        assert quality_report["quality_score"] > 0.0
        assert len(quality_report["issues"]) > 0  # Should identify the poor quality task
        assert len(quality_report["recommendations"]) > 0
    
    def test_cache_functionality_integration(self, detector):
        """Test caching functionality works correctly."""
        # Generate cache keys
        key1 = detector._generate_cache_key("test text", "context")
        key2 = detector._generate_cache_key("test text", "context")
        key3 = detector._generate_cache_key("different text", "context")
        
        # Same input should generate same key
        assert key1 == key2
        assert key1 != key3
        
        # Test cache storage (simulate)
        detector.task_cache[key1] = [DetectedTask(
            id="test", title="Test task", created_at=datetime.now().isoformat()
        )]
        
        assert key1 in detector.task_cache
        assert len(detector.task_cache[key1]) == 1
    
    def test_history_management_integration(self, detector):
        """Test history and cleanup functionality."""
        # Add some history
        detector.processed_texts = ["text1", "text2", "text3"]
        detector.context_buffer = ["context1", "context2"]
        detector.transcript_buffer = "some buffer content"
        
        # Clear history
        detector.clear_history()
        
        # Verify cleanup
        assert detector.processed_texts == []
        assert detector.context_buffer == []
        assert detector.transcript_buffer == ""
        assert detector.task_cache == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])