"""
tests/test_task_validation.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Comprehensive unit tests for TaskValidation service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from services.task_validation import (
    TaskValidation, ValidationResult, ParticipantMatch, 
    DeadlineParseResult, TaskSimilarity
)


class TestTaskValidation:
    """Test suite for TaskValidation service."""
    
    @pytest.fixture
    def task_validation(self):
        """Create TaskValidation instance for testing."""
        return TaskValidation()
    
    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            "title": "Fix authentication bug in login system",
            "assignee": "john",
            "deadline": "tomorrow",
            "description": "Users are unable to login with valid credentials",
            "priority": "high",
            "status": "pending",
            "confidence": 0.85,
            "source_text": "John needs to fix the authentication bug by tomorrow"
        }
    
    def test_validate_task_structure_valid_task(self, task_validation, sample_task_data):
        """Test validation of a valid task structure."""
        result = task_validation.validateTaskStructure(sample_task_data)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert result.confidence_score > 0.7
        assert len(result.issues) == 0
        assert "title" in result.normalized_data
        assert result.normalized_data["title"] == sample_task_data["title"]
    
    def test_validate_task_structure_missing_title(self, task_validation):
        """Test validation with missing title."""
        task_data = {"confidence": 0.8}
        result = task_validation.validateTaskStructure(task_data)
        
        assert not result.is_valid
        assert "Task title is required" in result.issues
        assert result.confidence_score >= 0.0  # Should still have some confidence from base score
    
    def test_validate_task_structure_short_title(self, task_validation):
        """Test validation with too short title."""
        task_data = {"title": "Hi", "confidence": 0.8}
        result = task_validation.validateTaskStructure(task_data)
        
        assert not result.is_valid
        assert "Task title must be at least 3 characters long" in result.issues
    
    def test_validate_task_structure_long_title(self, task_validation):
        """Test validation with very long title."""
        long_title = "A" * 250
        task_data = {"title": long_title, "confidence": 0.8}
        result = task_validation.validateTaskStructure(task_data)
        
        assert result.is_valid  # Should be valid but with warning
        assert any("Task title is very long" in warning for warning in result.warnings)
        assert len(result.normalized_data["title"]) == 200  # Truncated
    
    def test_validate_task_structure_invalid_confidence(self, task_validation):
        """Test validation with invalid confidence score."""
        task_data = {"title": "Valid title", "confidence": 1.5}
        result = task_validation.validateTaskStructure(task_data)
        
        assert "Confidence must be between 0.0 and 1.0" in result.issues
        assert result.normalized_data["confidence"] == 1.0  # Clamped
    
    def test_validate_task_structure_invalid_priority(self, task_validation):
        """Test validation with invalid priority."""
        task_data = {"title": "Valid title", "priority": "super_high", "confidence": 0.8}
        result = task_validation.validateTaskStructure(task_data)
        
        assert any("Invalid priority 'super_high'" in warning for warning in result.warnings)
        assert result.normalized_data["priority"] == "medium"  # Default
    
    def test_normalize_assignee_exact_match(self, task_validation):
        """Test exact assignee matching."""
        result = task_validation.normalizeAssignee("john")
        
        assert isinstance(result, ParticipantMatch)
        assert result.matched_name == "John"
        assert result.confidence == 0.95
        assert result.match_type == "exact"
    
    def test_normalize_assignee_alias_match(self, task_validation):
        """Test assignee alias matching."""
        result = task_validation.normalizeAssignee("johnny")
        
        assert result.matched_name == "John"
        assert result.confidence == 0.9
        assert result.match_type == "alias"
    
    def test_normalize_assignee_fuzzy_match(self, task_validation):
        """Test fuzzy assignee matching."""
        result = task_validation.normalizeAssignee("johnn")  # Typo
        
        assert result.matched_name == "John"
        assert result.match_type == "fuzzy"
        assert 0.6 <= result.confidence <= 0.8
    
    def test_normalize_assignee_pronoun_match(self, task_validation):
        """Test pronoun to speaker conversion."""
        result = task_validation.normalizeAssignee("I")
        
        assert result.matched_name == "Speaker"
        assert result.confidence == 0.6
        assert result.match_type == "pronoun"
    
    def test_normalize_assignee_unknown(self, task_validation):
        """Test unknown assignee handling."""
        result = task_validation.normalizeAssignee("unknown_person")
        
        assert result.matched_name == "Unknown_Person"
        assert result.confidence == 0.3
        assert result.match_type == "unknown"
    
    def test_normalize_assignee_with_context(self, task_validation):
        """Test assignee normalization with context participants."""
        context_participants = ["alice", "bob"]
        result = task_validation.normalizeAssignee("alice", context_participants)
        
        assert result.matched_name == "Alice"
        assert result.confidence == 0.95
        assert result.match_type == "exact"
    
    def test_parse_deadline_immediate(self, task_validation):
        """Test parsing immediate deadlines."""
        result = task_validation.parseDeadline("today")
        
        assert isinstance(result, DeadlineParseResult)
        assert result.parsed_date is not None
        assert result.confidence >= 0.9
        assert result.parse_method == "pattern"
        assert result.relative_days == 0
    
    def test_parse_deadline_tomorrow(self, task_validation):
        """Test parsing tomorrow deadline."""
        result = task_validation.parseDeadline("by tomorrow")
        
        assert result.parsed_date is not None
        assert result.confidence >= 0.8
        assert result.relative_days == 1
        
        # Verify the date is actually tomorrow
        expected_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert result.parsed_date == expected_date
    
    def test_parse_deadline_explicit_date(self, task_validation):
        """Test parsing explicit dates."""
        result = task_validation.parseDeadline("2024-12-25")
        
        assert result.parsed_date == "2024-12-25"
        assert result.confidence >= 0.9
        assert result.parse_method == "explicit"
    
    def test_parse_deadline_month_day(self, task_validation):
        """Test parsing month and day."""
        result = task_validation.parseDeadline("December 15")
        
        assert result.parsed_date is not None
        assert result.confidence >= 0.7
        assert result.parse_method == "month_day"
        assert "12-15" in result.parsed_date  # Should contain month and day
    
    def test_parse_deadline_invalid(self, task_validation):
        """Test parsing invalid deadline."""
        result = task_validation.parseDeadline("sometime maybe")
        
        assert result.parsed_date is None
        assert result.confidence == 0.0
        assert result.parse_method == "failed"
    
    def test_calculate_confidence_high_quality(self, task_validation, sample_task_data):
        """Test confidence calculation for high-quality task."""
        confidence = task_validation.calculateConfidence(sample_task_data)
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.7  # Should be high for good task
    
    def test_calculate_confidence_low_quality(self, task_validation):
        """Test confidence calculation for low-quality task."""
        low_quality_task = {
            "title": "maybe think about something",
            "confidence": 0.3
        }
        confidence = task_validation.calculateConfidence(low_quality_task)
        
        assert confidence < 0.5  # Should be low for poor task
    
    def test_deduplicate_tasks_no_duplicates(self, task_validation):
        """Test deduplication with no duplicates."""
        tasks = [
            {"title": "Fix authentication bug", "confidence": 0.8},
            {"title": "Deploy new feature", "confidence": 0.7},
            {"title": "Update documentation", "confidence": 0.9}
        ]
        
        result = task_validation.deduplicateTasks(tasks)
        
        assert len(result) == 3
        assert result == tasks
    
    def test_deduplicate_tasks_with_duplicates(self, task_validation):
        """Test deduplication with duplicate tasks."""
        tasks = [
            {"title": "Fix authentication bug in login system", "assignee": "john", "confidence": 0.8},
            {"title": "Fix authentication bug in login system", "assignee": "john", "confidence": 0.9},  # Exact duplicate
            {"title": "Deploy new feature to production", "confidence": 0.7}
        ]
        
        result = task_validation.deduplicateTasks(tasks)
        
        assert len(result) == 2  # One duplicate removed
        # Should keep the one with higher confidence
        auth_tasks = [t for t in result if "authentication" in t["title"].lower()]
        assert len(auth_tasks) == 1
        assert auth_tasks[0]["confidence"] == 0.9
    
    def test_enrich_task_data_basic(self, task_validation, sample_task_data):
        """Test basic task data enrichment."""
        enriched = task_validation.enrichTaskData(sample_task_data)
        
        assert "id" in enriched
        assert "created_at" in enriched
        assert "tags" in enriched
        assert "estimated_effort" in enriched
        assert "urgency_indicators" in enriched
        assert "complexity_score" in enriched
        
        # Verify enriched assignee
        assert enriched["assignee"] == "John"  # Normalized
        assert "assignee_confidence" in enriched
        assert "assignee_match_type" in enriched
    
    def test_enrich_task_data_with_context(self, task_validation, sample_task_data):
        """Test task enrichment with context."""
        context = {
            "participants": ["john", "alice"],
            "meeting_id": "meeting_123",
            "meeting_title": "Sprint Planning",
            "full_transcript": "We discussed the authentication issue. John needs to fix the authentication bug by tomorrow."
        }
        
        enriched = task_validation.enrichTaskData(sample_task_data, context)
        
        assert enriched["meeting_id"] == "meeting_123"
        assert enriched["meeting_title"] == "Sprint Planning"
        assert "context_window" in enriched
        assert len(enriched["context_window"]) > len(sample_task_data["source_text"])
    
    def test_add_participant(self, task_validation):
        """Test adding new participants."""
        initial_count = len(task_validation.known_participants)
        
        task_validation.addParticipant("Alice", ["al", "ally"])
        
        assert len(task_validation.known_participants) == initial_count + 1
        assert "alice" in task_validation.known_participants
        assert task_validation.participant_aliases["al"] == "alice"
        assert task_validation.participant_aliases["ally"] == "alice"
    
    def test_add_participant_alias(self, task_validation):
        """Test adding participant aliases."""
        task_validation.addParticipantAlias("mike", "michael")
        
        assert task_validation.participant_aliases["mike"] == "michael"
    
    def test_get_participants(self, task_validation):
        """Test getting participant list."""
        participants = task_validation.getParticipants()
        
        assert isinstance(participants, list)
        assert all(isinstance(p, str) for p in participants)
        assert all(p.istitle() for p in participants)  # Should be title case
    
    def test_validate_task_batch(self, task_validation):
        """Test batch task validation."""
        tasks = [
            {"title": "Valid task 1", "confidence": 0.8},
            {"title": "Valid task 2", "confidence": 0.7},
            {"title": "", "confidence": 0.5},  # Invalid
        ]
        
        results = task_validation.validateTaskBatch(tasks)
        
        assert len(results) == 3
        assert all(isinstance(r, ValidationResult) for r in results)
        assert results[0].is_valid
        assert results[1].is_valid
        assert not results[2].is_valid
    
    def test_process_task_pipeline(self, task_validation, sample_task_data):
        """Test complete task processing pipeline."""
        context = {"participants": ["john", "alice"]}
        
        result = task_validation.processTaskPipeline(sample_task_data, context)
        
        # Should have validation result
        assert "validation_result" in result
        assert "is_valid" in result["validation_result"]
        
        # Should be enriched
        assert "id" in result
        assert "tags" in result
        assert "estimated_effort" in result
        
        # Should have normalized assignee
        assert result["assignee"] == "John"
    
    def test_clear_cache(self, task_validation, sample_task_data):
        """Test cache clearing."""
        # Populate caches
        task_validation.validateTaskStructure(sample_task_data)
        task_validation.deduplicateTasks([sample_task_data, sample_task_data])
        
        assert len(task_validation.validation_cache) > 0
        
        task_validation.clearCache()
        
        assert len(task_validation.validation_cache) == 0
        assert len(task_validation.similarity_cache) == 0
    
    def test_get_validation_statistics(self, task_validation):
        """Test getting validation statistics."""
        stats = task_validation.getValidationStatistics()
        
        assert isinstance(stats, dict)
        assert "validation_cache_size" in stats
        assert "similarity_cache_size" in stats
        assert "known_participants" in stats
        assert "participant_aliases" in stats
        assert "deadline_patterns" in stats
        assert "task_categories" in stats
    
    @pytest.mark.parametrize("title,expected_categories", [
        ("Fix authentication bug", ["development"]),
        ("Test login functionality", ["testing"]),
        ("Deploy to production", ["deployment"]),
        ("Write API documentation", ["documentation"]),
        ("Schedule team meeting", ["meeting"]),
        ("Research new framework", ["research"]),
        ("Design user interface", ["design"]),
        ("Setup CI/CD pipeline", ["infrastructure"]),
        ("Random task", ["general"])
    ])
    def test_categorize_task(self, task_validation, title, expected_categories):
        """Test task categorization."""
        categories = task_validation._categorizeTask(title, "")
        
        assert any(cat in categories for cat in expected_categories)
    
    @pytest.mark.parametrize("title,expected_effort", [
        ("Quick fix for typo", "1-2 hours"),
        ("Complex system refactor", "1-2 days"),
        ("Implement new feature", "4-8 hours"),
        ("Fix critical bug", "2-4 hours"),
        ("Test user registration", "1-3 hours"),
        ("Update documentation", "2-4 hours"),
        ("General task", "2-4 hours")
    ])
    def test_estimate_task_effort(self, task_validation, title, expected_effort):
        """Test task effort estimation."""
        effort = task_validation._estimateTaskEffort(title, "")
        
        assert effort == expected_effort
    
    def test_extract_urgency_indicators(self, task_validation):
        """Test urgency indicator extraction."""
        text = "This is urgent and needs to be done asap today"
        indicators = task_validation._extractUrgencyIndicators(text)
        
        assert "urgent" in indicators
        assert "asap" in indicators
        assert "today" in indicators
        assert len(indicators) >= 3
    
    def test_calculate_task_complexity(self, task_validation):
        """Test task complexity calculation."""
        simple_task = "Fix typo in readme"
        complex_task = "Refactor entire authentication system architecture"
        
        simple_complexity = task_validation._calculateTaskComplexity(simple_task, "")
        complex_complexity = task_validation._calculateTaskComplexity(complex_task, "")
        
        assert 0.0 <= simple_complexity <= 1.0
        assert 0.0 <= complex_complexity <= 1.0
        assert complex_complexity > simple_complexity
    
    def test_days_until_weekday(self):
        """Test weekday calculation utility."""
        # Test Monday (0)
        days = TaskValidation._days_until_weekday(0)
        assert isinstance(days, int)
        assert 1 <= days <= 7
    
    def test_days_until_friday(self):
        """Test Friday calculation utility."""
        days = TaskValidation._days_until_friday()
        assert isinstance(days, int)
        assert 1 <= days <= 7
    
    def test_validation_caching(self, task_validation, sample_task_data):
        """Test that validation results are cached."""
        # First call
        result1 = task_validation.validateTaskStructure(sample_task_data)
        cache_size_after_first = len(task_validation.validation_cache)
        
        # Second call with same data
        result2 = task_validation.validateTaskStructure(sample_task_data)
        cache_size_after_second = len(task_validation.validation_cache)
        
        # Should be cached (same cache size)
        assert cache_size_after_first == cache_size_after_second
        assert result1.is_valid == result2.is_valid
        assert result1.confidence_score == result2.confidence_score
    
    def test_similarity_caching(self, task_validation):
        """Test that similarity calculations are cached."""
        task1 = {"title": "Fix bug A", "assignee": "john"}
        task2 = {"title": "Fix bug B", "assignee": "alice"}
        
        # First calculation
        similarity1 = task_validation._calculateTaskSimilarity(task1, task2)
        cache_size_after_first = len(task_validation.similarity_cache)
        
        # Second calculation with same tasks
        similarity2 = task_validation._calculateTaskSimilarity(task1, task2)
        cache_size_after_second = len(task_validation.similarity_cache)
        
        # Should be cached
        assert cache_size_after_first == cache_size_after_second
        assert similarity1.similarity_score == similarity2.similarity_score


class TestTaskValidationPropertyBased:
    """Property-based tests for TaskValidation service."""
    
    @pytest.fixture
    def task_validation(self):
        """Create TaskValidation instance for testing."""
        return TaskValidation()
    
    def test_confidence_score_bounds(self, task_validation):
        """Property: Confidence scores should always be between 0.0 and 1.0."""
        from hypothesis import given, strategies as st
        
        @given(
            title=st.text(min_size=1, max_size=100),
            confidence=st.floats(min_value=-10.0, max_value=10.0),
            assignee=st.one_of(st.none(), st.text(min_size=1, max_size=50))
        )
        def test_confidence_bounds(title, confidence, assignee):
            task_data = {
                "title": title,
                "confidence": confidence,
                "assignee": assignee
            }
            
            calculated_confidence = task_validation.calculateConfidence(task_data)
            assert 0.0 <= calculated_confidence <= 1.0
        
        test_confidence_bounds()
    
    def test_validation_consistency(self, task_validation):
        """Property: Validation should be consistent for the same input."""
        from hypothesis import given, strategies as st
        
        @given(
            title=st.text(min_size=3, max_size=100),
            confidence=st.floats(min_value=0.0, max_value=1.0)
        )
        def test_consistency(title, confidence):
            task_data = {"title": title, "confidence": confidence}
            
            result1 = task_validation.validateTaskStructure(task_data)
            result2 = task_validation.validateTaskStructure(task_data)
            
            assert result1.is_valid == result2.is_valid
            assert result1.confidence_score == result2.confidence_score
        
        test_consistency()
    
    def test_deduplication_idempotent(self, task_validation):
        """Property: Deduplication should be idempotent."""
        from hypothesis import given, strategies as st
        
        @given(
            tasks=st.lists(
                st.fixed_dictionaries({
                    "title": st.text(min_size=3, max_size=50),
                    "confidence": st.floats(min_value=0.0, max_value=1.0)
                }),
                min_size=1, max_size=10
            )
        )
        def test_idempotent(tasks):
            result1 = task_validation.deduplicateTasks(tasks)
            result2 = task_validation.deduplicateTasks(result1)
            
            # Deduplicating already deduplicated tasks should not change anything
            assert len(result1) == len(result2)
            
            # All tasks in result should be unique
            titles = [task["title"] for task in result1]
            assert len(titles) == len(set(titles)) or len(result1) <= 1
        
        test_idempotent()


if __name__ == "__main__":
    pytest.main([__file__])