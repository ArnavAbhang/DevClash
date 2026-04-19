"""
tests/test_detected_tasks_enhanced.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Comprehensive tests for enhanced detected tasks API endpoints.
Tests bulk operations, templates, analytics, export functionality, and notifications.
"""

import pytest
import json
import io
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app
from models.detected_task import DetectedTask
from models.user import User
from routers.detected_tasks import (
    BulkTaskOperation, TaskTemplate, TaskPattern, TaskAnalyticsRequest,
    TaskExportRequest, TaskNotification, TaskReminder
)


class TestBulkOperations:
    """Test bulk task operations endpoints."""
    
    def test_bulk_approve_tasks(self, test_client, mock_user: User, mock_tasks: list):
        """Test bulk approval of tasks."""
        # Mock task retrieval and updates
        with patch('routers.detected_tasks.DetectedTask.get') as mock_get, \
             patch('routers.detected_tasks.manager.send_to_user') as mock_send:
            
            # Setup mocks
            mock_task = Mock()
            mock_task.id = "task_123"
            mock_task.user_id = str(mock_user.id)
            mock_task.update = AsyncMock()
            mock_get.return_value = mock_task
            
            operation = BulkTaskOperation(
                task_ids=["task_123"],
                operation="approve"
            )
            
            response = test_client.post(
                "/api/detected-tasks/bulk-operations",
                json=operation.dict(),
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Bulk approve completed successfully"
            assert data["processed_count"] == 1
            assert len(data["results"]) == 1
            assert data["results"][0]["status"] == "approved"
    
    @pytest.mark.asyncio
    async def test_bulk_modify_tasks(self, test_client: AsyncClient, mock_user: User):
        """Test bulk modification of tasks."""
        with patch('routers.detected_tasks.DetectedTask.get') as mock_get, \
             patch('routers.detected_tasks.manager.send_to_user') as mock_send:
            
            mock_task = Mock()
            mock_task.id = "task_123"
            mock_task.user_id = str(mock_user.id)
            mock_task.update = AsyncMock()
            mock_get.return_value = mock_task
            
            operation = BulkTaskOperation(
                task_ids=["task_123"],
                operation="modify",
                updates={"priority": "high", "assignee": "John Doe"}
            )
            
            response = await test_client.post(
                "/api/detected-tasks/bulk-operations",
                json=operation.dict(),
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["processed_count"] == 1
            
            # Verify updates were applied
            mock_task.update.assert_called_once()
            update_call = mock_task.update.call_args[0][0]
            assert update_call["$set"]["priority"] == "high"
            assert update_call["$set"]["assignee"] == "John Doe"
    
    @pytest.mark.asyncio
    async def test_bulk_operation_unauthorized_task(self, test_client: AsyncClient, mock_user: User):
        """Test bulk operation on unauthorized task."""
        with patch('routers.detected_tasks.DetectedTask.get') as mock_get:
            # Mock task belonging to different user
            mock_task = Mock()
            mock_task.user_id = "different_user_id"
            mock_get.return_value = mock_task
            
            operation = BulkTaskOperation(
                task_ids=["task_123"],
                operation="approve"
            )
            
            response = await test_client.post(
                "/api/detected-tasks/bulk-operations",
                json=operation.dict(),
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]


class TestTaskTemplates:
    """Test task template management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_task_templates(self, test_client: AsyncClient, mock_user: User):
        """Test listing task templates."""
        response = await test_client.get(
            "/api/detected-tasks/templates",
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) == 2  # Mock templates
        assert templates[0]["name"] == "Bug Fix Template"
        assert templates[1]["name"] == "Feature Implementation"
    
    @pytest.mark.asyncio
    async def test_create_task_template(self, test_client: AsyncClient, mock_user: User):
        """Test creating a new task template."""
        template_data = {
            "name": "Test Template",
            "title_pattern": "Test {item}",
            "priority_default": "medium",
            "description_template": "Test description",
            "tags": ["test"]
        }
        
        response = await test_client.post(
            "/api/detected-tasks/templates",
            json=template_data,
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 200
        template = response.json()
        assert template["name"] == "Test Template"
        assert template["user_id"] == str(mock_user.id)
        assert template["id"] is not None
    
    @pytest.mark.asyncio
    async def test_get_task_template(self, test_client: AsyncClient, mock_user: User):
        """Test retrieving a specific task template."""
        response = await test_client.get(
            "/api/detected-tasks/templates/template_123",
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 200
        template = response.json()
        assert template["id"] == "template_123"
        assert template["name"] == "Sample Template"
    
    @pytest.mark.asyncio
    async def test_update_task_template(self, test_client: AsyncClient, mock_user: User):
        """Test updating a task template."""
        template_data = {
            "name": "Updated Template",
            "title_pattern": "Updated {item}",
            "priority_default": "high"
        }
        
        response = await test_client.put(
            "/api/detected-tasks/templates/template_123",
            json=template_data,
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 200
        template = response.json()
        assert template["name"] == "Updated Template"
        assert template["priority_default"] == "high"
    
    @pytest.mark.asyncio
    async def test_delete_task_template(self, test_client: AsyncClient, mock_user: User):
        """Test deleting a task template."""
        response = await test_client.delete(
            "/api/detected-tasks/templates/template_123",
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]


class TestTaskPatterns:
    """Test task pattern management endpoints."""
    
    @pytest.mark.asyncio
    async def test_add_task_pattern(self, test_client: AsyncClient, mock_user: User):
        """Test adding a custom task detection pattern."""
        pattern_data = {
            "pattern": "schedule meeting",
            "confidence_boost": 0.15,
            "auto_priority": "medium",
            "auto_tags": ["meeting", "scheduling"]
        }
        
        response = await test_client.post(
            "/api/detected-tasks/patterns",
            json=pattern_data,
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 200
        assert "added successfully" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_list_task_patterns(self, test_client: AsyncClient, mock_user: User):
        """Test listing task detection patterns."""
        response = await test_client.get(
            "/api/detected-tasks/patterns",
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "patterns" in data
        assert len(data["patterns"]) == 2  # Mock patterns
        assert data["patterns"][0]["pattern"] == "deploy to production"


class TestTaskAnalytics:
    """Test task analytics and reporting endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_task_analytics(self, test_client: AsyncClient, mock_user: User, mock_tasks: list):
        """Test comprehensive task analytics."""
        with patch('routers.detected_tasks.DetectedTask.find') as mock_find:
            # Mock task data
            mock_find.return_value.to_list.return_value = mock_tasks
            
            analytics_request = {
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-12-31T23:59:59"
            }
            
            response = await test_client.post(
                "/api/detected-tasks/analytics",
                json=analytics_request,
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check analytics structure
            assert "summary" in data
            assert "distributions" in data
            assert "trends" in data
            assert "insights" in data
            
            # Check summary fields
            summary = data["summary"]
            assert "total_tasks" in summary
            assert "completion_rate" in summary
            assert "average_confidence" in summary
            
            # Check distributions
            distributions = data["distributions"]
            assert "status" in distributions
            assert "priority" in distributions
            assert "assignee" in distributions
    
    @pytest.mark.asyncio
    async def test_get_task_statistics(self, test_client: AsyncClient, mock_user: User):
        """Test real-time task detection statistics."""
        with patch('routers.detected_tasks.task_detector.get_task_statistics') as mock_stats, \
             patch('routers.detected_tasks.DetectedTask.find') as mock_find:
            
            # Mock detector statistics
            mock_stats.return_value = {
                "total_chunks_processed": 100,
                "total_tasks_detected": 25,
                "average_confidence": 0.85,
                "cache_hit_rate": 0.75
            }
            
            # Mock user tasks
            mock_find.return_value.to_list.return_value = []
            
            response = await test_client.get(
                "/api/detected-tasks/statistics",
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "detection_stats" in data
            assert "user_stats" in data
            assert "system_health" in data
            
            # Check detection stats
            detection_stats = data["detection_stats"]
            assert detection_stats["total_chunks_processed"] == 100
            assert detection_stats["total_tasks_detected"] == 25


class TestTaskExport:
    """Test task export functionality."""
    
    @pytest.mark.asyncio
    async def test_export_tasks_json(self, test_client: AsyncClient, mock_user: User, mock_tasks: list):
        """Test exporting tasks as JSON."""
        with patch('routers.detected_tasks.DetectedTask.find') as mock_find:
            mock_find.return_value.to_list.return_value = mock_tasks
            
            export_request = {
                "format": "json",
                "include_metadata": True,
                "include_analytics": True
            }
            
            response = await test_client.post(
                "/api/detected-tasks/export",
                json=export_request,
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "tasks" in data
            assert "export_info" in data
            assert "metadata" in data
            assert "analytics" in data
            
            # Check export info
            export_info = data["export_info"]
            assert export_info["format"] == "json"
            assert "exported_at" in export_info
    
    @pytest.mark.asyncio
    async def test_export_tasks_csv(self, test_client: AsyncClient, mock_user: User, mock_tasks: list):
        """Test exporting tasks as CSV."""
        with patch('routers.detected_tasks.DetectedTask.find') as mock_find:
            mock_find.return_value.to_list.return_value = mock_tasks
            
            export_request = {
                "format": "csv",
                "include_metadata": True
            }
            
            response = await test_client.post(
                "/api/detected-tasks/export",
                json=export_request,
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv; charset=utf-8"
            assert "attachment" in response.headers["content-disposition"]
            
            # Check CSV content
            csv_content = response.content.decode()
            assert "ID,Title,Assignee" in csv_content
    
    @pytest.mark.asyncio
    async def test_export_tasks_pdf(self, test_client: AsyncClient, mock_user: User, mock_tasks: list):
        """Test exporting tasks as PDF."""
        with patch('routers.detected_tasks.DetectedTask.find') as mock_find:
            mock_find.return_value.to_list.return_value = mock_tasks
            
            export_request = {
                "format": "pdf",
                "include_metadata": True
            }
            
            response = await test_client.post(
                "/api/detected-tasks/export",
                json=export_request,
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"
            assert "attachment" in response.headers["content-disposition"]
    
    @pytest.mark.asyncio
    async def test_export_tasks_invalid_format(self, test_client: AsyncClient, mock_user: User):
        """Test exporting tasks with invalid format."""
        export_request = {
            "format": "invalid",
            "include_metadata": True
        }
        
        response = await test_client.post(
            "/api/detected-tasks/export",
            json=export_request,
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 422  # Validation error


class TestTaskNotifications:
    """Test task notification and reminder system."""
    
    @pytest.mark.asyncio
    async def test_create_task_notification(self, test_client: AsyncClient, mock_user: User):
        """Test creating a task notification."""
        with patch('routers.detected_tasks.DetectedTask.get') as mock_get:
            # Mock task
            mock_task = Mock()
            mock_task.user_id = str(mock_user.id)
            mock_task.title = "Test Task"
            mock_get.return_value = mock_task
            
            notification_data = {
                "task_id": "task_123",
                "notification_type": "deadline",
                "scheduled_time": (datetime.now() + timedelta(hours=2)).isoformat(),
                "message": "Task deadline approaching"
            }
            
            response = await test_client.post(
                "/api/detected-tasks/notifications",
                json=notification_data,
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "scheduled successfully" in data["message"]
            assert "notification_id" in data
            assert "scheduled_time" in data
    
    @pytest.mark.asyncio
    async def test_create_task_reminder(self, test_client: AsyncClient, mock_user: User):
        """Test creating a task reminder."""
        with patch('routers.detected_tasks.DetectedTask.get') as mock_get:
            # Mock task
            mock_task = Mock()
            mock_task.user_id = str(mock_user.id)
            mock_task.title = "Test Task"
            mock_get.return_value = mock_task
            
            reminder_data = {
                "task_id": "task_123",
                "reminder_time": (datetime.now() + timedelta(days=1)).isoformat(),
                "message": "Don't forget this task",
                "notification_method": "websocket"
            }
            
            response = await test_client.post(
                "/api/detected-tasks/reminders",
                json=reminder_data,
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "scheduled successfully" in data["message"]
            assert "reminder_id" in data
    
    @pytest.mark.asyncio
    async def test_list_task_notifications(self, test_client: AsyncClient, mock_user: User):
        """Test listing task notifications."""
        response = await test_client.get(
            "/api/detected-tasks/notifications",
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert len(data["notifications"]) == 2  # Mock notifications
    
    @pytest.mark.asyncio
    async def test_cancel_notification(self, test_client: AsyncClient, mock_user: User):
        """Test cancelling a scheduled notification."""
        response = await test_client.delete(
            "/api/detected-tasks/notifications/notif_123",
            headers={"Authorization": f"Bearer {mock_user.id}"}
        )
        
        assert response.status_code == 200
        assert "cancelled successfully" in response.json()["message"]


class TestAdvancedTaskManagement:
    """Test advanced task management endpoints."""
    
    @pytest.mark.asyncio
    async def test_duplicate_task(self, test_client: AsyncClient, mock_user: User):
        """Test duplicating an existing task."""
        with patch('routers.detected_tasks.DetectedTask.get') as mock_get, \
             patch('routers.detected_tasks.DetectedTask') as mock_task_class:
            
            # Mock original task
            original_task = Mock()
            original_task.user_id = str(mock_user.id)
            original_task.to_dict.return_value = {
                "id": "original_123",
                "title": "Original Task",
                "status": "done",
                "priority": "high",
                "assignee": "John",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            mock_get.return_value = original_task
            
            # Mock duplicate task creation
            duplicate_task = Mock()
            duplicate_task.to_dict.return_value = {
                "id": "duplicate_123",
                "title": "Copy of Original Task",
                "status": "pending",
                "priority": "high",
                "assignee": "John",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            duplicate_task.insert = AsyncMock()
            mock_task_class.return_value = duplicate_task
            
            response = await test_client.post(
                "/api/detected-tasks/tasks/original_123/duplicate",
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "Copy of" in data["title"]
            assert data["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_convert_task_to_template(self, test_client: AsyncClient, mock_user: User):
        """Test converting a task to a template."""
        with patch('routers.detected_tasks.DetectedTask.get') as mock_get:
            # Mock task
            mock_task = Mock()
            mock_task.user_id = str(mock_user.id)
            mock_task.title = "Fix bug in component"
            mock_task.assignee = "Developer"
            mock_task.priority = "high"
            mock_task.description = "Fix the reported bug"
            mock_get.return_value = mock_task
            
            response = await test_client.post(
                "/api/detected-tasks/tasks/task_123/convert-to-template?template_name=Bug Fix Template",
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            template = response.json()
            assert template["name"] == "Bug Fix Template"
            assert template["title_pattern"] == "Fix bug in component"
            assert template["assignee_default"] == "Developer"
            assert template["priority_default"] == "high"
    
    @pytest.mark.asyncio
    async def test_search_tasks(self, test_client: AsyncClient, mock_user: User, mock_tasks: list):
        """Test searching tasks by query."""
        with patch('routers.detected_tasks.DetectedTask.find') as mock_find:
            mock_find.return_value.limit.return_value.to_list.return_value = mock_tasks[:1]
            
            response = await test_client.get(
                "/api/detected-tasks/tasks/search?q=bug",
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "bug"
            assert "total_results" in data
            assert "tasks" in data
    
    @pytest.mark.asyncio
    async def test_get_overdue_tasks(self, test_client: AsyncClient, mock_user: User):
        """Test getting overdue tasks."""
        with patch('routers.detected_tasks.DetectedTask.find') as mock_find:
            # Mock overdue task
            overdue_task = Mock()
            overdue_task.to_dict.return_value = {
                "id": "overdue_123",
                "title": "Overdue Task",
                "deadline": "2024-01-01",
                "status": "pending"
            }
            mock_find.return_value.to_list.return_value = [overdue_task]
            
            response = await test_client.get(
                "/api/detected-tasks/tasks/overdue",
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "overdue_count" in data
            assert "tasks" in data
    
    @pytest.mark.asyncio
    async def test_get_upcoming_tasks(self, test_client: AsyncClient, mock_user: User):
        """Test getting upcoming tasks."""
        with patch('routers.detected_tasks.DetectedTask.find') as mock_find:
            # Mock upcoming task
            upcoming_task = Mock()
            upcoming_task.to_dict.return_value = {
                "id": "upcoming_123",
                "title": "Upcoming Task",
                "deadline": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                "status": "pending"
            }
            mock_find.return_value.sort.return_value.to_list.return_value = [upcoming_task]
            
            response = await test_client.get(
                "/api/detected-tasks/tasks/upcoming?days=7",
                headers={"Authorization": f"Bearer {mock_user.id}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 7
            assert "upcoming_count" in data
            assert "tasks" in data


# Test fixtures
@pytest.fixture
def mock_user():
    """Mock user for testing."""
    user = Mock()
    user.id = "user_123"
    user.email = "test@example.com"
    return user

@pytest.fixture
def mock_tasks():
    """Mock tasks for testing."""
    tasks = []
    for i in range(3):
        task = Mock()
        task.id = f"task_{i}"
        task.title = f"Test Task {i}"
        task.status = "pending" if i < 2 else "done"
        task.priority = "medium"
        task.assignee = "John Doe" if i % 2 == 0 else "Jane Smith"
        task.confidence = 0.8 + (i * 0.05)
        task.created_at = datetime.now() - timedelta(days=i)
        task.to_dict.return_value = {
            "id": str(task.id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "assignee": task.assignee,
            "confidence": task.confidence,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.created_at.isoformat()
        }
        tasks.append(task)
    return tasks

@pytest.fixture
async def test_client():
    """Test client for API testing."""
    from httpx import AsyncClient
    from fastapi.testclient import TestClient
    
    # Use TestClient for synchronous testing
    client = TestClient(app)
    return client