"""
tests/test_task_validation_properties.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Property-based tests for TaskValidation service using Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timedelta
import re

from services.task_validation import TaskValidation, ValidationResult, ParticipantMatch


class TestTaskValidationProperties:
    """Property-based tests for TaskValidation service."""
    
    @given(
        title=st.text(min_size=1, max_size=200),
        confidence=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_validate_task_structure_confidence_bounds(self, title, confidence):
        """
        **Validates: Requirements 3.4, 3.5**
        Property: Validation should always return confidence scores within [0.0, 1.0] bounds.
        """
        task_validation = TaskValidation()
        task_data = {"title": title, "confidence": confidence}
        result = task_validation.validateTaskStructure(task_data)
        
        assert isinstance(result, ValidationResult)
        assert 0.0 <= result.confidence_score <= 1.0
        assert 0.0 <= result.normalized_data.get("confidence", 0.0) <= 1.0
    
    @given(
        title=st.text(min_size=3, max_size=100),
        assignee=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        deadline=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        confidence=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=50)
    def test_validate_task_structure_consistency(self, title, assignee, deadline, confidence):
        """
        **Validates: Requirements 3.4**
        Property: Validation should be consistent - same input should produce same output.
        """
        task_validation = TaskValidation()
        task_data = {
            "title": title,
            "assignee": assignee,
            "deadline": deadline,
            "confidence": confidence
        }
        
        result1 = task_validation.validateTaskStructure(task_data)
        result2 = task_validation.validateTaskStructure(task_data)
        
        assert result1.is_valid == result2.is_valid
        assert result1.confidence_score == result2.confidence_score
        assert len(result1.issues) == len(result2.issues)
        assert len(result1.warnings) == len(result2.warnings)
    
    @given(
        assignee_input=st.text(min_size=1, max_size=50),
        context_participants=st.one_of(
            st.none(),
            st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10)
        )
    )
    @settings(max_examples=100)
    def test_normalize_assignee_confidence_bounds(self, assignee_input, context_participants):
        """
        **Validates: Requirements 3.5**
        Property: Assignee normalization should always return confidence within [0.0, 1.0].
        """
        task_validation = TaskValidation()
        result = task_validation.normalizeAssignee(assignee_input, context_participants)
        
        assert isinstance(result, ParticipantMatch)
        assert 0.0 <= result.confidence <= 1.0
        assert result.original_input == assignee_input
        assert result.match_type in ["exact", "fuzzy", "alias", "partial", "pronoun", "unknown", "variation"]
    
    @given(
        assignee_input=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=50)
    def test_normalize_assignee_deterministic(self, assignee_input):
        """
        **Validates: Requirements 3.5**
        Property: Assignee normalization should be deterministic for the same input.
        """
        task_validation = TaskValidation()
        result1 = task_validation.normalizeAssignee(assignee_input)
        result2 = task_validation.normalizeAssignee(assignee_input)
        
        assert result1.matched_name == result2.matched_name
        assert result1.confidence == result2.confidence
        assert result1.match_type == result2.match_type
    
    @given(
        deadline_input=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100)
    def test_parse_deadline_confidence_bounds(self, deadline_input):
        """
        **Validates: Requirements 3.6**
        Property: Deadline parsing should always return confidence within [0.0, 1.0].
        """
        task_validation = TaskValidation()
        result = task_validation.parseDeadline(deadline_input)
        
        assert 0.0 <= result.confidence <= 1.0
        assert result.original_input == deadline_input
        assert result.parse_method in ["pattern", "explicit", "month_day", "numeric_day", "failed", "none"]
        
        # If parsed successfully, should have valid date format
        if result.parsed_date:
            # Should be valid ISO date format
            assert re.match(r'\d{4}-\d{2}-\d{2}', result.parsed_date)
            # Should be parseable as date
            datetime.strptime(result.parsed_date, "%Y-%m-%d")
    
    @given(
        task_data=st.fixed_dictionaries({
            "title": st.text(min_size=3, max_size=100),
            "confidence": st.floats(min_value=0.0, max_value=1.0),
            "assignee": st.one_of(st.none(), st.text(min_size=1, max_size=30)),
            "deadline": st.one_of(st.none(), st.text(min_size=1, max_size=30)),
            "description": st.text(max_size=200)
        })
    )
    @settings(max_examples=50)
    def test_calculate_confidence_bounds(self, task_data):
        """
        **Validates: Requirements 3.8**
        Property: Confidence calculation should always return values within [0.0, 1.0].
        """
        task_validation = TaskValidation()
        confidence = task_validation.calculateConfidence(task_data)
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
    
    @given(
        tasks=st.lists(
            st.fixed_dictionaries({
                "title": st.text(min_size=3, max_size=50),
                "confidence": st.floats(min_value=0.0, max_value=1.0),
                "assignee": st.one_of(st.none(), st.text(min_size=1, max_size=20))
            }),
            min_size=0, max_size=20
        )
    )
    @settings(max_examples=30)
    def test_deduplicate_tasks_properties(self, tasks):
        """
        **Validates: Requirements 3.9**
        Property: Task deduplication should maintain important invariants.
        """
        task_validation = TaskValidation()
        result = task_validation.deduplicateTasks(tasks)
        
        # Result should not be longer than input
        assert len(result) <= len(tasks)
        
        # All tasks in result should be from original input
        result_titles = {task["title"] for task in result}
        original_titles = {task["title"] for task in tasks}
        assert result_titles.issubset(original_titles)
        
        # If input is empty, result should be empty
        if not tasks:
            assert not result
        
        # Deduplication should be idempotent
        result2 = task_validation.deduplicateTasks(result)
        assert len(result) == len(result2)
    
    
    @given(
        task_data=st.fixed_dictionaries({
            "title": st.text(min_size=3, max_size=100),
            "confidence": st.floats(min_value=0.0, max_value=1.0),
            "assignee": st.one_of(st.none(), st.text(min_size=1, max_size=30)),
            "description": st.text(max_size=200)
        }),
        context=st.one_of(
            st.none(),
            st.fixed_dictionaries({
                "participants": st.lists(st.text(min_size=1, max_size=20), max_size=5),
                "meeting_id": st.text(min_size=1, max_size=50)
            })
        )
    )
    @settings(max_examples=30)
    def test_enrich_task_data_properties(self, task_data, context):
        """
        **Validates: Requirements 3.9**
        Property: Task enrichment should preserve original data and add new fields.
        """
        task_validation = TaskValidation()
        enriched = task_validation.enrichTaskData(task_data, context)
        
        # Original fields should be preserved or improved
        assert enriched["title"] == task_data["title"]
        assert enriched.get("description", "") == task_data.get("description", "")
        
        # New fields should be added
        assert "id" in enriched
        assert "created_at" in enriched
        assert "tags" in enriched
        assert "estimated_effort" in enriched
        assert "complexity_score" in enriched
        
        # Confidence should be recalculated and within bounds
        assert 0.0 <= enriched["confidence"] <= 1.0
        
        # Tags should be a list
        assert isinstance(enriched["tags"], list)
        
        # Complexity score should be within bounds
        assert 0.0 <= enriched["complexity_score"] <= 1.0
    
    @given(
        tasks=st.lists(
            st.fixed_dictionaries({
                "title": st.text(min_size=3, max_size=50),
                "confidence": st.floats(min_value=0.0, max_value=1.0)
            }),
            min_size=0, max_size=10
        )
    )
    @settings(max_examples=20)
    def test_validate_task_batch_properties(self, tasks):
        """
        **Validates: Requirements 3.4**
        Property: Batch validation should return one result per input task.
        """
        task_validation = TaskValidation()
        results = task_validation.validateTaskBatch(tasks)
        
        # Should have same number of results as input tasks
        assert len(results) == len(tasks)
        
        # All results should be ValidationResult instances
        assert all(isinstance(r, ValidationResult) for r in results)
        
        # All confidence scores should be within bounds
        assert all(0.0 <= r.confidence_score <= 1.0 for r in results)
    
    @given(
        title1=st.text(min_size=3, max_size=50),
        title2=st.text(min_size=3, max_size=50),
        assignee1=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
        assignee2=st.one_of(st.none(), st.text(min_size=1, max_size=20))
    )
    @settings(max_examples=50)
    def test_calculate_task_similarity_properties(self, title1, title2, assignee1, assignee2):
        """
        **Validates: Requirements 3.9**
        Property: Task similarity calculation should be symmetric and bounded.
        """
        task_validation = TaskValidation()
        task1 = {"title": title1, "assignee": assignee1}
        task2 = {"title": title2, "assignee": assignee2}
        
        similarity1 = task_validation._calculateTaskSimilarity(task1, task2)
        similarity2 = task_validation._calculateTaskSimilarity(task2, task1)
        
        # Similarity should be symmetric
        assert similarity1.similarity_score == similarity2.similarity_score
        assert similarity1.title_similarity == similarity2.title_similarity
        assert similarity1.assignee_match == similarity2.assignee_match
        
        # Similarity scores should be bounded
        assert 0.0 <= similarity1.similarity_score <= 1.0
        assert 0.0 <= similarity1.title_similarity <= 1.0
        assert 0.0 <= similarity1.context_similarity <= 1.0
        
        # Identical tasks should have high similarity
        if title1 == title2 and assignee1 == assignee2:
            assert similarity1.similarity_score >= 0.6  # Adjusted for edge cases
            assert similarity1.title_similarity == 1.0
    
    @given(
        participant_name=st.text(min_size=1, max_size=30, alphabet=st.characters(blacklist_characters='\r\n\t')),
        aliases=st.lists(st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_characters='\r\n\t')), max_size=5)
    )
    @settings(max_examples=20)
    def test_add_participant_properties(self, participant_name, aliases):
        """
        **Validates: Requirements 3.5**
        Property: Adding participants should increase known participants count.
        """
        task_validation = TaskValidation()
        assume(participant_name.strip())  # Non-empty after stripping
        assume(participant_name.lower() not in task_validation.known_participants)
        
        initial_count = len(task_validation.known_participants)
        initial_aliases_count = len(task_validation.participant_aliases)
        
        task_validation.addParticipant(participant_name, aliases)
        
        # Should increase participant count
        assert len(task_validation.known_participants) == initial_count + 1
        assert participant_name.lower() in task_validation.known_participants
        
        # Should add aliases
        valid_aliases = [a for a in aliases if a.strip()]
        # Account for duplicate aliases - only unique ones are added
        unique_aliases = set(valid_aliases)
        expected_aliases_count = initial_aliases_count + len(unique_aliases)
        assert len(task_validation.participant_aliases) == expected_aliases_count
    
    @given(
        text=st.text(max_size=200)
    )
    @settings(max_examples=50)
    def test_assess_task_quality_bounds(self, text):
        """
        **Validates: Requirements 3.8**
        Property: Task quality assessment should return bounded scores.
        """
        task_validation = TaskValidation()
        quality_score = task_validation._assess_task_quality(text.lower(), "")
        
        assert isinstance(quality_score, float)
        assert 0.0 <= quality_score <= 1.0
    
    @given(
        title=st.text(min_size=1, max_size=100),
        description=st.text(max_size=200)
    )
    @settings(max_examples=30)
    def test_categorize_task_properties(self, title, description):
        """
        **Validates: Requirements 3.9**
        Property: Task categorization should always return non-empty list.
        """
        task_validation = TaskValidation()
        categories = task_validation._categorizeTask(title, description)
        
        assert isinstance(categories, list)
        assert len(categories) > 0  # Should always have at least one category
        assert all(isinstance(cat, str) for cat in categories)
        
        # Should contain 'general' if no specific category found
        if not any(keyword in (title + " " + description).lower() 
                  for keywords in task_validation.task_categories.values() 
                  for keyword in keywords):
            assert "general" in categories
    
    @given(
        title=st.text(min_size=1, max_size=100),
        description=st.text(max_size=200)
    )
    @settings(max_examples=30)
    def test_estimate_task_effort_format(self, title, description):
        """
        **Validates: Requirements 3.9**
        Property: Task effort estimation should return valid time format.
        """
        task_validation = TaskValidation()
        effort = task_validation._estimateTaskEffort(title, description)
        
        assert isinstance(effort, str)
        assert len(effort) > 0
        
        # Should match expected effort patterns
        valid_patterns = [
            r'\d+-\d+ hours?',
            r'\d+-\d+ days?',
            r'\d+ hours?',
            r'\d+ days?'
        ]
        assert any(re.search(pattern, effort) for pattern in valid_patterns)
    
    @given(
        text=st.text(max_size=500)
    )
    @settings(max_examples=30)
    def test_extract_urgency_indicators_properties(self, text):
        """
        **Validates: Requirements 3.9**
        Property: Urgency indicator extraction should return valid list.
        """
        task_validation = TaskValidation()
        indicators = task_validation._extractUrgencyIndicators(text)
        
        assert isinstance(indicators, list)
        assert all(isinstance(indicator, str) for indicator in indicators)
        
        # Should not contain duplicates
        assert len(indicators) == len(set(indicators))
        
        # All indicators should actually be in the text
        text_lower = text.lower()
        assert all(indicator in text_lower for indicator in indicators)
    
    @given(
        task_data=st.fixed_dictionaries({
            "title": st.text(min_size=3, max_size=100),
            "confidence": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    @settings(max_examples=20)
    def test_process_task_pipeline_completeness(self, task_data):
        """
        **Validates: Requirements 3.4, 3.5, 3.6, 3.8, 3.9**
        Property: Task pipeline should produce complete, valid output.
        """
        task_validation = TaskValidation()
        result = task_validation.processTaskPipeline(task_data)
        
        # Should have validation result
        assert "validation_result" in result
        validation_result = result["validation_result"]
        assert "is_valid" in validation_result
        assert "confidence_score" in validation_result
        assert 0.0 <= validation_result["confidence_score"] <= 1.0
        
        # Should be enriched with required fields
        required_fields = ["id", "created_at", "tags", "estimated_effort", "confidence"]
        assert all(field in result for field in required_fields)
        
        # Confidence should be within bounds
        assert 0.0 <= result["confidence"] <= 1.0
        
        # Tags should be non-empty list
        assert isinstance(result["tags"], list)
        assert len(result["tags"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])