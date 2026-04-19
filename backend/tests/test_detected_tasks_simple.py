"""
tests/test_detected_tasks_simple.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Simple tests to verify the enhanced detected tasks API endpoints work.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from main import app
from routers.detected_tasks import BulkTaskOperation, TaskTemplate


def test_bulk_operations_endpoint_exists():
    """Test that the bulk operations endpoint exists and accepts requests."""
    client = TestClient(app)
    
    # Test with invalid auth to check endpoint exists
    response = client.post("/api/detected-tasks/bulk-operations", json={})
    
    # Should get 403 (forbidden) not 404 (not found) - endpoint exists
    assert response.status_code == 403


def test_templates_endpoint_exists():
    """Test that the templates endpoint exists."""
    client = TestClient(app)
    
    # Test with invalid auth to check endpoint exists
    response = client.get("/api/detected-tasks/templates")
    
    # Should get 403 (forbidden) not 404 (not found) - endpoint exists
    assert response.status_code == 403


def test_analytics_endpoint_exists():
    """Test that the analytics endpoint exists."""
    client = TestClient(app)
    
    # Test with invalid auth to check endpoint exists
    response = client.post("/api/detected-tasks/analytics", json={})
    
    # Should get 403 (forbidden) not 404 (not found) - endpoint exists
    assert response.status_code == 403


def test_export_endpoint_exists():
    """Test that the export endpoint exists."""
    client = TestClient(app)
    
    # Test with invalid auth to check endpoint exists
    response = client.post("/api/detected-tasks/export", json={"format": "json"})
    
    # Should get 403 (forbidden) not 404 (not found) - endpoint exists
    assert response.status_code == 403


def test_notifications_endpoint_exists():
    """Test that the notifications endpoint exists."""
    client = TestClient(app)
    
    # Test with invalid auth to check endpoint exists
    response = client.get("/api/detected-tasks/notifications")
    
    # Should get 403 (forbidden) not 404 (not found) - endpoint exists
    assert response.status_code == 403


def test_search_endpoint_exists():
    """Test that the search endpoint exists."""
    client = TestClient(app)
    
    # Test with invalid auth to check endpoint exists
    response = client.get("/api/detected-tasks/tasks/search?q=test")
    
    # Should get 403 (forbidden) not 404 (not found) - endpoint exists
    assert response.status_code == 403


def test_overdue_tasks_endpoint_exists():
    """Test that the overdue tasks endpoint exists."""
    client = TestClient(app)
    
    # Test with invalid auth to check endpoint exists
    response = client.get("/api/detected-tasks/tasks/overdue")
    
    # Should get 403 (forbidden) not 404 (not found) - endpoint exists
    assert response.status_code == 403


def test_upcoming_tasks_endpoint_exists():
    """Test that the upcoming tasks endpoint exists."""
    client = TestClient(app)
    
    # Test with invalid auth to check endpoint exists
    response = client.get("/api/detected-tasks/tasks/upcoming")
    
    # Should get 403 (forbidden) not 404 (not found) - endpoint exists
    assert response.status_code == 403


def test_pydantic_models_work():
    """Test that the new Pydantic models work correctly."""
    
    # Test BulkTaskOperation
    bulk_op = BulkTaskOperation(
        task_ids=["task1", "task2"],
        operation="approve"
    )
    assert bulk_op.task_ids == ["task1", "task2"]
    assert bulk_op.operation == "approve"
    
    # Test TaskTemplate
    template = TaskTemplate(
        name="Test Template",
        title_pattern="Test {item}",
        priority_default="high"
    )
    assert template.name == "Test Template"
    assert template.priority_default == "high"


def test_invalid_bulk_operation():
    """Test that invalid bulk operations are rejected."""
    with pytest.raises(ValueError):
        BulkTaskOperation(
            task_ids=["task1"],
            operation="invalid_operation"  # Should fail validation
        )


def test_invalid_template_priority():
    """Test that invalid template priorities are rejected."""
    with pytest.raises(ValueError):
        TaskTemplate(
            name="Test Template",
            title_pattern="Test {item}",
            priority_default="invalid_priority"  # Should fail validation
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])