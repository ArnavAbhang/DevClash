"""
examples/task_validation_example.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Example demonstrating the TaskValidation service integration with TaskDetector.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.task_validation import TaskValidation


async def main():
    """Demonstrate TaskValidation service capabilities."""
    print("🔍 TaskValidation Service Demo")
    print("=" * 50)
    
    # Initialize the validation service
    validator = TaskValidation()
    
    # Example 1: Basic task validation
    print("\n1. Basic Task Validation")
    print("-" * 30)
    
    sample_task = {
        "title": "Fix authentication bug in login system",
        "assignee": "john",
        "deadline": "tomorrow",
        "description": "Users are unable to login with valid credentials",
        "priority": "high",
        "confidence": 0.85,
        "source_text": "John needs to fix the authentication bug by tomorrow"
    }
    
    validation_result = validator.validateTaskStructure(sample_task)
    print(f"Task: {sample_task['title']}")
    print(f"Valid: {validation_result.is_valid}")
    print(f"Confidence: {validation_result.confidence_score:.2f}")
    print(f"Issues: {validation_result.issues}")
    print(f"Warnings: {validation_result.warnings}")
    
    # Example 2: Assignee normalization
    print("\n2. Assignee Normalization")
    print("-" * 30)
    
    test_assignees = ["john", "johnny", "johnn", "I", "unknown_person"]
    
    for assignee in test_assignees:
        match = validator.normalizeAssignee(assignee)
        print(f"'{assignee}' -> '{match.matched_name}' (confidence: {match.confidence:.2f}, type: {match.match_type})")
    
    # Example 3: Deadline parsing
    print("\n3. Deadline Parsing")
    print("-" * 30)
    
    test_deadlines = ["today", "tomorrow", "next week", "2024-12-25", "December 15", "invalid"]
    
    for deadline in test_deadlines:
        result = validator.parseDeadline(deadline)
        print(f"'{deadline}' -> {result.parsed_date} (confidence: {result.confidence:.2f}, method: {result.parse_method})")
    
    # Example 4: Task deduplication
    print("\n4. Task Deduplication")
    print("-" * 30)
    
    duplicate_tasks = [
        {"title": "Fix authentication bug", "assignee": "john", "confidence": 0.8},
        {"title": "Fix auth bug", "assignee": "john", "confidence": 0.9},  # Similar
        {"title": "Deploy new feature", "confidence": 0.7},
        {"title": "Fix authentication bug", "assignee": "john", "confidence": 0.6}  # Exact duplicate
    ]
    
    print(f"Original tasks: {len(duplicate_tasks)}")
    unique_tasks = validator.deduplicateTasks(duplicate_tasks)
    print(f"After deduplication: {len(unique_tasks)}")
    
    for task in unique_tasks:
        print(f"  - {task['title']} (confidence: {task['confidence']})")
    
    # Example 5: Task enrichment
    print("\n5. Task Enrichment")
    print("-" * 30)
    
    basic_task = {
        "title": "Implement user registration feature",
        "confidence": 0.8
    }
    
    context = {
        "participants": ["alice", "bob", "charlie"],
        "meeting_id": "meeting_123",
        "meeting_title": "Sprint Planning"
    }
    
    enriched_task = validator.enrichTaskData(basic_task, context)
    
    print(f"Original fields: {len(basic_task)}")
    print(f"Enriched fields: {len(enriched_task)}")
    print(f"Added fields: {set(enriched_task.keys()) - set(basic_task.keys())}")
    print(f"Tags: {enriched_task['tags']}")
    print(f"Estimated effort: {enriched_task['estimated_effort']}")
    print(f"Complexity score: {enriched_task['complexity_score']:.2f}")
    
    # Example 6: Complete pipeline
    print("\n6. Complete Processing Pipeline")
    print("-" * 30)
    
    raw_task = {
        "title": "urgent: fix the login bug asap",
        "assignee": "johnny",
        "deadline": "by friday",
        "confidence": 0.75,
        "source_text": "Johnny needs to urgently fix the login bug by Friday"
    }
    
    processed_task = validator.processTaskPipeline(raw_task, context)
    
    print(f"Original: {raw_task['title']}")
    print(f"Processed: {processed_task['title']}")
    print(f"Normalized assignee: {processed_task['assignee']}")
    print(f"Parsed deadline: {processed_task['deadline']}")
    print(f"Final confidence: {processed_task['confidence']:.2f}")
    print(f"Urgency indicators: {processed_task['urgency_indicators']}")
    print(f"Validation valid: {processed_task['validation_result']['is_valid']}")
    
    # Example 7: Batch validation
    print("\n7. Batch Validation")
    print("-" * 30)
    
    task_batch = [
        {"title": "Valid task 1", "confidence": 0.8},
        {"title": "Valid task 2", "confidence": 0.7},
        {"title": "", "confidence": 0.5},  # Invalid
        {"title": "Another valid task", "confidence": 0.9}
    ]
    
    batch_results = validator.validateTaskBatch(task_batch)
    
    for i, result in enumerate(batch_results):
        print(f"Task {i+1}: Valid={result.is_valid}, Confidence={result.confidence_score:.2f}")
    
    # Example 8: Statistics
    print("\n8. Validation Statistics")
    print("-" * 30)
    
    stats = validator.getValidationStatistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\n✅ TaskValidation Demo Complete!")


if __name__ == "__main__":
    asyncio.run(main())