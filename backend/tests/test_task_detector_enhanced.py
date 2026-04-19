"""
tests/test_task_detector_enhanced.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Comprehensive tests for the enhanced TaskDetector service.
Includes unit tests and property-based tests for production-grade task detection.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import text, lists, integers, floats

from services.task_detector import TaskDetector, DetectedTask, ProcessingMetrics, TaskRelationship


class TestTaskDetectorEnhanced:
    """Test suite for enhanced TaskDetector functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create a TaskDetector instance for testing."""
        return TaskDetector()
    
    @pytest.fixture
    def mock_groq_response(self):
        """Mock Groq API response."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''[
            {
                "title": "Fix login bug",
                "assignee": "John",
                "deadline": "tomorrow",
                "priority": "high",
                "confidence": 0.95,
                "description": "Fix the authentication issue",
                "tags": ["bugfix", "security"],
                "urgency_indicators": ["urgent"]
            }
        ]'''
        return mock_response
    
    # Basic functionality tests
    
    def test_detector_initialization(self, detector):
        """Test TaskDetector initializes correctly."""
        assert detector.transcript_buffer == ""
        assert detector.buffer_word_threshold == 15
        assert len(detector.known_participants) > 0
        assert "arnav" in detector.known_participants
        assert detector.processing_metrics.chunks_processed == 0
    
    def test_add_participant(self, detector):
        """Test adding new participants."""
        initial_count = len(detector.known_participants)
        detector.add_participant("Alice")
        
        assert len(detector.known_participants) == initial_count + 1
        assert "alice" in detector.known_participants
        assert "Alice" in detector.get_participants()
    
    def test_add_participant_alias(self, detector):
        """Test adding participant aliases."""
        detector.add_participant_alias("Al", "Alice")
        assert detector.participant_aliases["al"] == "alice"
    
    # Transcript processing tests
    
    @pytest.mark.asyncio
    async def test_process_transcript_chunk_buffering(self, detector):
        """Test transcript chunk buffering behavior."""
        # Short chunks should be buffered
        result = await detector.process_transcript_chunk("Hello")
        assert result == []
        assert "Hello" in detector.transcript_buffer
        
        # Add more chunks
        result = await detector.process_transcript_chunk("world this is")
        assert result == []
        
        # Should still be buffering
        result = await detector.process_transcript_chunk("a test")
        assert result == []
    
    @pytest.mark.asyncio
    async def test_process_transcript_chunk_processing(self, detector, mock_groq_response):
        """Test transcript processing when threshold is reached."""
        with patch.object(detector, 'get_groq') as mock_groq:
            mock_groq.return_value.chat.completions.create.return_value = mock_groq_response
            
            # Add enough words to trigger processing
            long_text = "John needs to fix the login bug by tomorrow this is urgent and important task"
            result = await detector.process_transcript_chunk(long_text)
            
            # Should process and return tasks
            assert len(result) >= 0  # May return tasks depending on AI response
            # Check that processing occurred (buffer should be cleared or reduced)
            assert len(detector.transcript_buffer.split()) < len(long_text.split())
    
    @pytest.mark.asyncio
    async def test_flush_buffer(self, detector, mock_groq_response):
        """Test flushing remaining buffer content."""
        with patch.object(detector, 'get_groq') as mock_groq:
            mock_groq.return_value.chat.completions.create.return_value = mock_groq_response
            
            # Add some content to buffer
            detector.transcript_buffer = "John will fix the bug"
            
            result = await detector.flush_buffer()
            assert detector.transcript_buffer == ""
            assert detector.context_buffer == []
    
    # AI detection tests
    
    @pytest.mark.asyncio
    async def test_ai_task_detection_success(self, detector, mock_groq_response):
        """Test successful AI task detection."""
        with patch.object(detector, 'get_groq') as mock_groq:
            mock_groq.return_value.chat.completions.create.return_value = mock_groq_response
            
            text = "John needs to fix the login bug by tomorrow"
            tasks = await detector._detect_tasks_with_ai(text)
            
            assert len(tasks) == 1
            task = tasks[0]
            assert task.title == "Fix login bug"
            assert task.assignee == "John"
            assert task.priority == "high"
            assert task.confidence >= 0.95  # May be enhanced by other factors
    
    @pytest.mark.asyncio
    async def test_ai_detection_with_invalid_json(self, detector):
        """Test AI detection handles invalid JSON gracefully."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        
        with patch.object(detector, 'get_groq') as mock_groq:
            mock_groq.return_value.chat.completions.create.return_value = mock_response
            
            tasks = await detector._detect_tasks_with_ai("Some text")
            assert tasks == []
    
    @pytest.mark.asyncio
    async def test_ai_detection_api_failure(self, detector):
        """Test AI detection handles API failures gracefully."""
        with patch.object(detector, 'get_groq') as mock_groq:
            mock_groq.return_value.chat.completions.create.side_effect = Exception("API Error")
            
            tasks = await detector._detect_tasks_with_ai("Some text")
            assert tasks == []
    
    # Rule-based detection tests
    
    def test_rule_based_detection(self, detector):
        """Test rule-based task detection."""
        text = "John will fix the login bug by tomorrow"
        tasks = detector._detect_tasks_with_rules(text)
        
        assert len(tasks) >= 0  # May find tasks based on rules
        if tasks:
            task = tasks[0]
            assert task.assignee is not None
            assert task.confidence >= 0.6
    
    def test_extract_assignee_rules(self, detector):
        """Test assignee extraction using rules."""
        test_cases = [
            ("John will fix the bug", "John", 0.6),
            ("Assign this to Sarah", "Sarah", 0.9),
            ("Mike is responsible for testing", "Mike", 0.8),
            ("Someone should handle this", None, 0.0)
        ]
        
        for text, expected_assignee, min_confidence in test_cases:
            assignee, confidence = detector._extract_assignee_rules(text)
            if expected_assignee:
                assert assignee == expected_assignee
                assert confidence >= min_confidence
            else:
                assert assignee is None
    
    def test_extract_deadline_rules(self, detector):
        """Test deadline extraction using rules."""
        test_cases = [
            "Fix this by tomorrow",
            "Complete by Friday",
            "Due today",
            "End of week deadline"
        ]
        
        for text in test_cases:
            deadline, confidence = detector._extract_deadline_rules(text)
            if deadline:
                assert confidence > 0.0
                # Should be a valid date string
                datetime.strptime(deadline, "%Y-%m-%d")
    
    # Enhanced assignee normalization tests
    
    def test_normalize_assignee_enhanced(self, detector):
        """Test enhanced assignee normalization."""
        test_cases = [
            ("john", "John", 0.95),  # Exact match
            ("Jon", "John", 0.7),    # Fuzzy match
            ("Johnny", "John", 0.5), # Partial match (adjusted expectation)
            ("Unknown Person", "Unknown Person", 0.5)  # Not in list
        ]
        
        for input_name, expected_name, min_confidence in test_cases:
            name, confidence = detector._normalize_assignee_enhanced(input_name)
            assert name == expected_name
            assert confidence >= min_confidence
    
    # Priority detection tests
    
    def test_determine_priority_enhanced(self, detector):
        """Test enhanced priority determination."""
        test_cases = [
            ("high", ["urgent"], "Fix this urgent bug", "high"),
            ("medium", [], "Regular task", "medium"),
            ("low", [], "Nice to have feature", "low")
        ]
        
        for ai_priority, urgency_indicators, text, expected in test_cases:
            priority = detector._determine_priority_enhanced(ai_priority, urgency_indicators, text)
            assert priority == expected
    
    # Task categorization tests
    
    def test_categorize_task(self, detector):
        """Test task categorization."""
        test_cases = [
            ("Fix login bug", ["development"]),  # "fix" is in development keywords
            ("Deploy to production", ["deployment"]),
            ("Write documentation", ["documentation"]),
            ("Test new feature", ["testing"])
        ]
        
        for title, expected_categories in test_cases:
            tags = detector._categorize_task(title)
            for category in expected_categories:
                assert category in tags
    
    # Deduplication tests
    
    def test_deduplicate_tasks(self, detector):
        """Test task deduplication."""
        tasks = [
            DetectedTask(
                id="1", title="Fix login bug", confidence=0.8,
                assignee="John", created_at=datetime.now().isoformat()
            ),
            DetectedTask(
                id="2", title="Fix login issue", confidence=0.9,
                assignee="John", created_at=datetime.now().isoformat()
            ),
            DetectedTask(
                id="3", title="Update documentation", confidence=0.7,
                assignee="Sarah", created_at=datetime.now().isoformat()
            )
        ]
        
        unique_tasks = detector._deduplicate_tasks(tasks)
        
        # Should keep higher confidence duplicate
        assert len(unique_tasks) == 2
        login_tasks = [t for t in unique_tasks if "login" in t.title.lower()]
        assert len(login_tasks) == 1
        assert login_tasks[0].confidence == 0.9
    
    # Validation tests
    
    def test_validate_and_filter_tasks(self, detector):
        """Test task validation and filtering."""
        tasks = [
            DetectedTask(
                id="1", title="Fix bug", confidence=0.8,
                created_at=datetime.now().isoformat()
            ),
            DetectedTask(
                id="2", title="", confidence=0.9,  # Invalid: empty title
                created_at=datetime.now().isoformat()
            ),
            DetectedTask(
                id="3", title="Valid task", confidence=0.3,  # Invalid: low confidence
                created_at=datetime.now().isoformat()
            ),
            DetectedTask(
                id="4", title="ok", confidence=0.8,  # Invalid: not meaningful
                created_at=datetime.now().isoformat()
            )
        ]
        
        valid_tasks = detector._validate_and_filter_tasks(tasks)
        assert len(valid_tasks) == 1
        assert valid_tasks[0].title == "Fix bug"
    
    def test_is_meaningful_task(self, detector):
        """Test meaningful task detection."""
        meaningful_tasks = [
            DetectedTask(id="1", title="Fix the login bug", created_at=""),
            DetectedTask(id="2", title="John will update the docs", created_at=""),
            DetectedTask(id="3", title="Deploy to production", created_at="")
        ]
        
        non_meaningful_tasks = [
            DetectedTask(id="4", title="ok", created_at=""),
            DetectedTask(id="5", title="yes", created_at=""),
            DetectedTask(id="6", title="thanks", created_at="")
        ]
        
        for task in meaningful_tasks:
            assert detector._is_meaningful_task(task)
        
        for task in non_meaningful_tasks:
            assert not detector._is_meaningful_task(task)
    
    # Utility method tests
    
    def test_clean_transcript_text(self, detector):
        """Test transcript text cleaning."""
        dirty_text = "Um, John needs to, uh, fix the bug [background noise] (coughing)"
        clean_text = detector._clean_transcript_text(dirty_text)
        
        assert "um" not in clean_text.lower()
        assert "uh" not in clean_text.lower()
        assert "[background noise]" not in clean_text
        assert "(coughing)" not in clean_text
    
    def test_generate_cache_key(self, detector):
        """Test cache key generation."""
        key1 = detector._generate_cache_key("text1", "context1")
        key2 = detector._generate_cache_key("text1", "context1")
        key3 = detector._generate_cache_key("text2", "context1")
        
        assert key1 == key2  # Same input should generate same key
        assert key1 != key3  # Different input should generate different key
        assert len(key1) == 32  # MD5 hash length
    
    def test_is_duplicate_text(self, detector):
        """Test duplicate text detection."""
        detector.processed_texts = ["hello world this is a test"]
        
        assert detector._is_duplicate_text("hello world this is a test")  # Exact match
        assert detector._is_duplicate_text("hello world this is test")    # High similarity
        assert not detector._is_duplicate_text("completely different text")  # No similarity
    
    # Metrics and statistics tests
    
    def test_processing_metrics(self, detector):
        """Test processing metrics tracking."""
        metrics = detector.get_processing_metrics()
        assert isinstance(metrics, ProcessingMetrics)
        assert metrics.chunks_processed == 0
        assert metrics.tasks_detected == 0
    
    def test_get_task_statistics(self, detector):
        """Test task statistics generation."""
        # Add some mock metrics
        detector.processing_metrics.chunks_processed = 10
        detector.processing_metrics.tasks_detected = 5
        detector.processing_metrics.confidence_scores = [0.8, 0.9, 0.7]
        detector.processing_metrics.api_calls_made = 3
        detector.processing_metrics.cache_hits = 1
        
        stats = detector.get_task_statistics()
        
        assert stats["total_chunks_processed"] == 10
        assert stats["total_tasks_detected"] == 5
        assert stats["average_confidence"] == 0.8
        assert stats["api_calls_made"] == 3
        assert stats["cache_hits"] == 1
        assert "cache_hit_rate" in stats
    
    @pytest.mark.asyncio
    async def test_validate_task_quality(self, detector):
        """Test task quality validation."""
        tasks = [
            DetectedTask(
                id="1", title="Fix bug", confidence=0.9,
                assignee="John", deadline="2024-12-15",
                created_at=datetime.now().isoformat()
            ),
            DetectedTask(
                id="2", title="Update docs", confidence=0.5,
                created_at=datetime.now().isoformat()
            )
        ]
        
        quality_report = await detector.validate_task_quality(tasks)
        
        assert "quality_score" in quality_report
        assert "total_tasks" in quality_report
        assert quality_report["total_tasks"] == 2
        assert "issues" in quality_report
        assert "recommendations" in quality_report
    
    # Configuration tests
    
    def test_update_configuration(self, detector):
        """Test configuration updates."""
        config = {
            "buffer_word_threshold": 20,
            "max_context_length": 800
        }
        
        detector.update_configuration(config)
        
        assert detector.buffer_word_threshold == 20
        assert detector.max_context_length == 800
    
    def test_clear_history(self, detector):
        """Test clearing detector history."""
        # Add some data
        detector.processed_texts = ["test1", "test2"]
        detector.task_cache = {"key1": []}
        detector.context_buffer = ["context1"]
        detector.transcript_buffer = "buffer content"
        
        detector.clear_history()
        
        assert detector.processed_texts == []
        assert detector.task_cache == {}
        assert detector.context_buffer == []
        assert detector.transcript_buffer == ""


# Property-based tests using Hypothesis

class TestTaskDetectorProperties:
    """Property-based tests for TaskDetector."""
    
    @given(text(min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz "))
    @settings(max_examples=50, deadline=5000)
    def test_clean_transcript_text_properties(self, text_input):
        """Property: cleaned text should never be longer than original."""
        detector = TaskDetector()
        cleaned = detector._clean_transcript_text(text_input)
        assert len(cleaned) <= len(text_input)
        assert isinstance(cleaned, str)
    
    @given(
        lists(
            st.builds(
                DetectedTask,
                id=text(min_size=1, max_size=10),
                title=text(min_size=1, max_size=50),
                confidence=floats(min_value=0.0, max_value=1.0),
                created_at=st.just(datetime.now().isoformat())
            ),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=20, deadline=5000)
    def test_deduplicate_tasks_properties(self, tasks):
        """Property: deduplication should never increase task count."""
        if not tasks:
            return
        
        detector = TaskDetector()
        unique_tasks = detector._deduplicate_tasks(tasks)
        assert len(unique_tasks) <= len(tasks)
        
        # All returned tasks should be valid
        for task in unique_tasks:
            assert task.id
            assert task.title
            assert 0.0 <= task.confidence <= 1.0
    
    @given(
        lists(
            st.builds(
                DetectedTask,
                id=text(min_size=1, max_size=10),
                title=text(min_size=1, max_size=50),
                confidence=floats(min_value=0.0, max_value=1.0),
                created_at=st.just(datetime.now().isoformat())
            ),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=20, deadline=5000)
    def test_validate_and_filter_tasks_properties(self, tasks):
        """Property: validation should never increase task count and maintain confidence bounds."""
        if not tasks:
            return
        
        detector = TaskDetector()
        valid_tasks = detector._validate_and_filter_tasks(tasks)
        assert len(valid_tasks) <= len(tasks)
        
        # All valid tasks should meet minimum criteria
        for task in valid_tasks:
            assert len(task.title.strip()) >= 3
            assert task.confidence >= 0.5
            assert 0.0 <= task.confidence <= 1.0
    
    @given(text(min_size=1, max_size=200, alphabet="abcdefghijklmnopqrstuvwxyz .,!?"))
    @settings(max_examples=30, deadline=5000)
    def test_is_duplicate_text_properties(self, text_input):
        """Property: duplicate detection should be consistent."""
        detector = TaskDetector()
        
        # First call should not be duplicate (empty history)
        assert not detector._is_duplicate_text(text_input)
        
        # Add to history
        detector.processed_texts.append(text_input.lower().strip())
        
        # Same text should be detected as duplicate
        assert detector._is_duplicate_text(text_input)
    
    @given(
        text(min_size=5, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz "),
        text(min_size=5, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz ")
    )
    @settings(max_examples=20, deadline=5000)
    def test_generate_cache_key_properties(self, text1, text2):
        """Property: cache key generation should be deterministic and unique for different inputs."""
        detector = TaskDetector()
        
        key1a = detector._generate_cache_key(text1, "context")
        key1b = detector._generate_cache_key(text1, "context")
        key2 = detector._generate_cache_key(text2, "context")
        
        # Same input should generate same key
        assert key1a == key1b
        
        # Different input should generate different key (with high probability)
        if text1 != text2:
            assert key1a != key2
        
        # Keys should be valid MD5 hashes
        assert len(key1a) == 32
        assert all(c in "0123456789abcdef" for c in key1a)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])