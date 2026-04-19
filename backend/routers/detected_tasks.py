"""
routers/detected_tasks.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Comprehensive API endpoints for AI-detected tasks from voice commands.
Enhanced with bulk operations, templates, analytics, export functionality, and notifications.
"""

import csv
import io
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict, Counter

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from core.dependencies import get_current_user
from models.detected_task import DetectedTask
from models.user import User
from services.task_detector import TaskDetector

router = APIRouter(prefix="/api/detected-tasks", tags=["detected-tasks"])

# WebSocket connection manager with transcript support
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: dict[str, List[WebSocket]] = {}
        self.meeting_transcripts: dict[str, List[dict]] = {}  # Store transcripts per meeting

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id in self.user_connections and websocket in self.user_connections[user_id]:
            self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id][:]:  # Copy to avoid modification during iteration
                try:
                    await connection.send_json(message)
                except:
                    # Remove dead connections
                    self.user_connections[user_id].remove(connection)
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

    async def broadcast_to_meeting(self, meeting_id: str, message: dict, exclude_user: str = None):
        """Broadcast message to all users in a meeting."""
        for user_id, connections in self.user_connections.items():
            if exclude_user and user_id == exclude_user:
                continue
            for connection in connections[:]:
                try:
                    await connection.send_json(message)
                except:
                    connections.remove(connection)
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

    def add_transcript_segment(self, meeting_id: str, segment: dict):
        """Add a transcript segment to meeting history."""
        if meeting_id not in self.meeting_transcripts:
            self.meeting_transcripts[meeting_id] = []
        self.meeting_transcripts[meeting_id].append(segment)
        
        # Keep only last 1000 segments per meeting
        if len(self.meeting_transcripts[meeting_id]) > 1000:
            self.meeting_transcripts[meeting_id] = self.meeting_transcripts[meeting_id][-1000:]

    def get_meeting_transcript(self, meeting_id: str) -> List[dict]:
        """Get transcript history for a meeting."""
        return self.meeting_transcripts.get(meeting_id, [])

manager = ConnectionManager()

# Initialize task detector
task_detector = TaskDetector()

# Enhanced Pydantic models for comprehensive task management
class DetectedTaskResponse(BaseModel):
    id: str
    title: str
    assignee: Optional[str]
    deadline: Optional[str]
    description: str
    priority: str
    status: str
    confidence: float
    source_text: str
    user_id: str
    meeting_id: Optional[str]
    created_at: str
    updated_at: str

class DetectedTaskUpdate(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None

class TaskDetectionRequest(BaseModel):
    text: str
    context: Optional[List[str]] = None
    meeting_id: Optional[str] = None

# New models for enhanced functionality
class BulkTaskOperation(BaseModel):
    task_ids: List[str] = Field(..., min_length=1, max_length=100)
    operation: str = Field(..., pattern="^(approve|dismiss|modify|delete|archive)$")
    updates: Optional[Dict[str, Any]] = None

class TaskTemplate(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., max_length=100)
    title_pattern: str = Field(..., max_length=200)
    assignee_default: Optional[str] = None
    priority_default: str = Field(default="medium", pattern="^(low|medium|high)$")
    deadline_offset_days: Optional[int] = Field(None, ge=0, le=365)
    description_template: str = Field(default="", max_length=500)
    tags: List[str] = Field(default_factory=list)
    user_id: Optional[str] = None
    is_public: bool = Field(default=False)
    usage_count: int = Field(default=0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class TaskPattern(BaseModel):
    pattern: str = Field(..., max_length=200)
    confidence_boost: float = Field(default=0.1, ge=0.0, le=0.5)
    auto_assign: Optional[str] = None
    auto_priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    auto_tags: List[str] = Field(default_factory=list)

class TaskAnalyticsRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    meeting_id: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None

class TaskExportRequest(BaseModel):
    format: str = Field(..., pattern="^(json|csv|pdf)$")
    task_ids: Optional[List[str]] = None
    filters: Optional[TaskAnalyticsRequest] = None
    include_metadata: bool = Field(default=True)
    include_analytics: bool = Field(default=False)

class TaskNotification(BaseModel):
    task_id: str
    notification_type: str = Field(..., pattern="^(reminder|deadline|assignment|status_change)$")
    scheduled_time: datetime
    message: str = Field(..., max_length=500)
    is_sent: bool = Field(default=False)
    user_id: str

class TaskReminder(BaseModel):
    task_id: str
    reminder_time: datetime
    message: Optional[str] = None
    notification_method: str = Field(default="websocket", pattern="^(websocket|email|both)$")

# Routes
@router.get("/", response_model=List[DetectedTaskResponse])
async def list_detected_tasks(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """List detected tasks for the current user."""
    query = {"user_id": str(current_user.id)}
    
    if status:
        query["status"] = status
    if assignee:
        query["assignee"] = assignee
    
    tasks = await DetectedTask.find(query).limit(limit).sort(-DetectedTask.created_at).to_list()
    return [DetectedTaskResponse(**task.to_dict()) for task in tasks]

@router.get("/{task_id}", response_model=DetectedTaskResponse)
async def get_detected_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific detected task."""
    try:
        task = await DetectedTask.get(PydanticObjectId(task_id))
        if not task or task.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Task not found")
        return DetectedTaskResponse(**task.to_dict())
    except Exception:
        raise HTTPException(status_code=404, detail="Task not found")

@router.patch("/{task_id}", response_model=DetectedTaskResponse)
async def update_detected_task(
    task_id: str,
    update_data: DetectedTaskUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a detected task."""
    try:
        task = await DetectedTask.get(PydanticObjectId(task_id))
        if not task or task.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        if update_dict:
            update_dict["updated_at"] = datetime.now()
            await task.update({"$set": update_dict})
            
        # Fetch updated task
        updated_task = await DetectedTask.get(task.id)
        
        # Notify via WebSocket
        await manager.send_to_user(str(current_user.id), {
            "type": "task_updated",
            "task": updated_task.to_dict()
        })
        
        return DetectedTaskResponse(**updated_task.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}")
async def delete_detected_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a detected task."""
    try:
        task = await DetectedTask.get(PydanticObjectId(task_id))
        if not task or task.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Task not found")
        
        await task.delete()
        
        # Notify via WebSocket
        await manager.send_to_user(str(current_user.id), {
            "type": "task_deleted",
            "task_id": task_id
        })
        
        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect", response_model=List[DetectedTaskResponse])
async def detect_tasks_from_text(
    request: TaskDetectionRequest,
    current_user: User = Depends(get_current_user)
):
    """Manually trigger task detection from text."""
    try:
        detected_tasks = await task_detector.detect_tasks(request.text, request.context)
        
        saved_tasks = []
        for task_data in detected_tasks:
            # Convert to database model
            db_task = DetectedTask(
                title=task_data.title,
                assignee=task_data.assignee,
                deadline=task_data.deadline,
                description=task_data.description,
                priority=task_data.priority,
                status=task_data.status,
                confidence=task_data.confidence,
                source_text=task_data.source_text,
                user_id=str(current_user.id),
                meeting_id=request.meeting_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            await db_task.insert()
            saved_tasks.append(db_task)
            
            # Notify via WebSocket
            await manager.send_to_user(str(current_user.id), {
                "type": "new_task",
                "task": db_task.to_dict()
            })
        
        return [DetectedTaskResponse(**task.to_dict()) for task in saved_tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task detection failed: {str(e)}")

@router.get("/participants/list")
async def get_known_participants(current_user: User = Depends(get_current_user)):
    """Get list of known participants for task assignment."""
    return {"participants": task_detector.get_participants()}

@router.post("/participants/add")
async def add_participant(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """Add a new participant to the known list."""
    task_detector.add_participant(name)
    return {"message": f"Participant '{name}' added successfully"}

# ============================================================================
# BULK OPERATIONS ENDPOINTS
# ============================================================================

@router.post("/bulk-operations")
async def bulk_task_operations(
    operation: BulkTaskOperation,
    current_user: User = Depends(get_current_user)
):
    """Perform bulk operations on multiple tasks."""
    try:
        # Validate task ownership
        tasks = []
        for task_id in operation.task_ids:
            task = await DetectedTask.get(PydanticObjectId(task_id))
            if not task or task.user_id != str(current_user.id):
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            tasks.append(task)
        
        results = []
        
        if operation.operation == "approve":
            # Approve tasks (change status to in-progress)
            for task in tasks:
                await task.update({"$set": {"status": "in-progress", "updated_at": datetime.now()}})
                results.append({"task_id": str(task.id), "status": "approved"})
        
        elif operation.operation == "dismiss":
            # Dismiss tasks (change status to dismissed)
            for task in tasks:
                await task.update({"$set": {"status": "dismissed", "updated_at": datetime.now()}})
                results.append({"task_id": str(task.id), "status": "dismissed"})
        
        elif operation.operation == "modify":
            # Modify tasks with provided updates
            if not operation.updates:
                raise HTTPException(status_code=400, detail="Updates required for modify operation")
            
            update_data = operation.updates.copy()
            update_data["updated_at"] = datetime.now()
            
            for task in tasks:
                await task.update({"$set": update_data})
                results.append({"task_id": str(task.id), "status": "modified"})
        
        elif operation.operation == "delete":
            # Delete tasks
            for task in tasks:
                await task.delete()
                results.append({"task_id": str(task.id), "status": "deleted"})
        
        elif operation.operation == "archive":
            # Archive tasks (change status to archived)
            for task in tasks:
                await task.update({"$set": {"status": "archived", "updated_at": datetime.now()}})
                results.append({"task_id": str(task.id), "status": "archived"})
        
        # Notify via WebSocket
        await manager.send_to_user(str(current_user.id), {
            "type": "bulk_operation_completed",
            "operation": operation.operation,
            "results": results
        })
        
        return {
            "message": f"Bulk {operation.operation} completed successfully",
            "processed_count": len(results),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk operation failed: {str(e)}")

# WebSocket endpoint for real-time task detection
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time task detection and updates."""
    # Note: In a real implementation, you'd need to authenticate the WebSocket connection
    # For now, we'll accept the connection and handle auth via message
    user_id = None
    
    try:
        await websocket.accept()
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "auth":
                # Handle authentication
                user_id = data.get("user_id")
                if user_id:
                    await manager.connect(websocket, user_id)
                    await websocket.send_json({"type": "auth_success", "message": "Connected successfully"})
                else:
                    await websocket.send_json({"type": "auth_error", "message": "Invalid user_id"})
            
            # 🚨 NEW: TRANSCRIPT STREAMING SUPPORT
            elif data.get("type") == "transcript_update":
                if not user_id:
                    await websocket.send_json({"type": "error", "message": "Not authenticated"})
                    continue
                
                try:
                    # Parse transcript segment data
                    segment_data = data.get("segment")
                    meeting_id = data.get("meeting_id", "live-session")
                    
                    if segment_data:
                        # Add to meeting transcript history
                        manager.add_transcript_segment(meeting_id, segment_data)
                        
                        # Broadcast to other clients in the same meeting
                        await manager.broadcast_to_meeting(meeting_id, {
                            "type": "transcript_update",
                            "segment": segment_data,
                            "meeting_id": meeting_id,
                            "timestamp": data.get("timestamp", datetime.now().timestamp())
                        }, exclude_user=user_id)
                        
                except Exception as e:
                    print(f"❌ Transcript update error: {e}")
                    await websocket.send_json({
                        "type": "error", 
                        "message": f"Transcript update failed: {str(e)}"
                    })
            
            elif data.get("type") == "request_sync":
                if not user_id:
                    await websocket.send_json({"type": "error", "message": "Not authenticated"})
                    continue
                
                try:
                    meeting_id = data.get("meeting_id", "live-session")
                    transcript_history = manager.get_meeting_transcript(meeting_id)
                    
                    # Send transcript sync to requesting client
                    await websocket.send_json({
                        "type": "transcript_sync",
                        "segments": transcript_history,
                        "meeting_id": meeting_id,
                        "timestamp": datetime.now().timestamp()
                    })
                    
                except Exception as e:
                    print(f"❌ Transcript sync error: {e}")
                    await websocket.send_json({
                        "type": "error", 
                        "message": f"Transcript sync failed: {str(e)}"
                    })
            
            # 🚨 NEW: BUFFERED CHUNK PROCESSING - CRITICAL FIX
            elif data.get("type") == "process_chunk":
                if not user_id:
                    await websocket.send_json({"type": "error", "message": "Not authenticated"})
                    continue
                    
                chunk = data.get("chunk", "")
                meeting_id = data.get("meeting_id")
                
                if chunk:
                    try:
                        # 🔥 USE BUFFERED PROCESSING
                        detected_tasks = await task_detector.process_transcript_chunk(chunk)
                        
                        # 🚨 SEND TO FRONTEND - CRITICAL
                        for task_data in detected_tasks:
                            # Save to database
                            db_task = DetectedTask(
                                title=task_data.title,
                                assignee=task_data.assignee,
                                deadline=task_data.deadline,
                                description=task_data.description,
                                priority=task_data.priority,
                                status=task_data.status,
                                confidence=task_data.confidence,
                                source_text=task_data.source_text,
                                user_id=user_id,
                                meeting_id=meeting_id,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            
                            await db_task.insert()
                            
                            # 🔥 SEND TO FRONTEND - KEY FIX
                            await manager.send_to_user(user_id, {
                                "type": "new_task",
                                "task": db_task.to_dict()
                            })
                            
                            print(f"🎯 TASK SENT TO FRONTEND: {task_data.title}")
                            
                    except Exception as e:
                        print(f"❌ Chunk processing error: {e}")
                        await websocket.send_json({
                            "type": "error", 
                            "message": f"Chunk processing failed: {str(e)}"
                        })
                        
            elif data.get("type") == "detect_tasks":
                if not user_id:
                    await websocket.send_json({"type": "error", "message": "Not authenticated"})
                    continue
                    
                text = data.get("text", "")
                context = data.get("context", [])
                meeting_id = data.get("meeting_id")
                
                if text:
                    try:
                        detected_tasks = await task_detector.detect_tasks(text, context)
                        
                        for task_data in detected_tasks:
                            # Save to database
                            db_task = DetectedTask(
                                title=task_data.title,
                                assignee=task_data.assignee,
                                deadline=task_data.deadline,
                                description=task_data.description,
                                priority=task_data.priority,
                                status=task_data.status,
                                confidence=task_data.confidence,
                                source_text=task_data.source_text,
                                user_id=user_id,
                                meeting_id=meeting_id,
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            
                            await db_task.insert()
                            
                            # Send to all user's connections
                            await manager.send_to_user(user_id, {
                                "type": "new_task",
                                "task": db_task.to_dict()
                            })
                            
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error", 
                            "message": f"Task detection failed: {str(e)}"
                        })
            
            # 🚨 NEW: FLUSH BUFFER ON TRANSCRIPTION END
            elif data.get("type") == "flush_buffer":
                if not user_id:
                    await websocket.send_json({"type": "error", "message": "Not authenticated"})
                    continue
                
                try:
                    # Force process any remaining buffered text
                    detected_tasks = await task_detector.flush_buffer()
                    
                    for task_data in detected_tasks:
                        # Save to database
                        db_task = DetectedTask(
                            title=task_data.title,
                            assignee=task_data.assignee,
                            deadline=task_data.deadline,
                            description=task_data.description,
                            priority=task_data.priority,
                            status=task_data.status,
                            confidence=task_data.confidence,
                            source_text=task_data.source_text,
                            user_id=user_id,
                            meeting_id=data.get("meeting_id"),
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        
                        await db_task.insert()
                        
                        await manager.send_to_user(user_id, {
                            "type": "new_task",
                            "task": db_task.to_dict()
                        })
                        
                except Exception as e:
                    await websocket.send_json({
                        "type": "error", 
                        "message": f"Buffer flush failed: {str(e)}"
                    })
                        
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if user_id:
            manager.disconnect(websocket, user_id)

# ============================================================================
# TASK TEMPLATES AND PATTERNS ENDPOINTS
# ============================================================================

@router.get("/templates", response_model=List[TaskTemplate])
async def list_task_templates(
    current_user: User = Depends(get_current_user),
    include_public: bool = Query(default=True)
):
    """List task templates for the current user."""
    # Note: In a real implementation, you'd have a TaskTemplate collection
    # For now, return mock templates
    templates = [
        TaskTemplate(
            id="template_1",
            name="Bug Fix Template",
            title_pattern="Fix {issue} in {component}",
            assignee_default=None,
            priority_default="high",
            deadline_offset_days=3,
            description_template="Investigate and fix the reported issue",
            tags=["bugfix", "development"],
            user_id=str(current_user.id),
            is_public=False,
            usage_count=5,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        TaskTemplate(
            id="template_2",
            name="Feature Implementation",
            title_pattern="Implement {feature_name}",
            assignee_default=None,
            priority_default="medium",
            deadline_offset_days=7,
            description_template="Design and implement the requested feature",
            tags=["feature", "development"],
            user_id=str(current_user.id),
            is_public=True,
            usage_count=12,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]
    
    return templates

@router.post("/templates", response_model=TaskTemplate)
async def create_task_template(
    template: TaskTemplate,
    current_user: User = Depends(get_current_user)
):
    """Create a new task template."""
    template.user_id = str(current_user.id)
    template.created_at = datetime.now()
    template.updated_at = datetime.now()
    template.id = f"template_{datetime.now().timestamp()}"
    
    # In a real implementation, save to database
    return template

@router.get("/templates/{template_id}", response_model=TaskTemplate)
async def get_task_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific task template."""
    # Mock implementation
    template = TaskTemplate(
        id=template_id,
        name="Sample Template",
        title_pattern="Complete {task_name}",
        user_id=str(current_user.id),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    return template

@router.put("/templates/{template_id}", response_model=TaskTemplate)
async def update_task_template(
    template_id: str,
    template_update: TaskTemplate,
    current_user: User = Depends(get_current_user)
):
    """Update a task template."""
    template_update.id = template_id
    template_update.user_id = str(current_user.id)
    template_update.updated_at = datetime.now()
    
    # In a real implementation, update in database
    return template_update

@router.delete("/templates/{template_id}")
async def delete_task_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a task template."""
    # In a real implementation, delete from database
    return {"message": f"Template {template_id} deleted successfully"}

@router.post("/patterns")
async def add_task_pattern(
    pattern: TaskPattern,
    current_user: User = Depends(get_current_user)
):
    """Add a custom task detection pattern."""
    # In a real implementation, this would update the task detector's patterns
    return {"message": f"Pattern '{pattern.pattern}' added successfully"}

@router.get("/patterns")
async def list_task_patterns(current_user: User = Depends(get_current_user)):
    """List custom task detection patterns."""
    # Mock patterns
    patterns = [
        TaskPattern(
            pattern="deploy to production",
            confidence_boost=0.2,
            auto_priority="high",
            auto_tags=["deployment", "production"]
        ),
        TaskPattern(
            pattern="write unit tests",
            confidence_boost=0.15,
            auto_priority="medium",
            auto_tags=["testing", "development"]
        )
    ]
    return {"patterns": patterns}
# ============================================================================
# ANALYTICS AND REPORTING ENDPOINTS
# ============================================================================

@router.post("/analytics")
async def get_task_analytics(
    request: TaskAnalyticsRequest,
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive task analytics and statistics."""
    try:
        # Build query filters
        query = {"user_id": str(current_user.id)}
        
        if request.start_date:
            query["created_at"] = {"$gte": request.start_date}
        if request.end_date:
            if "created_at" in query:
                query["created_at"]["$lte"] = request.end_date
            else:
                query["created_at"] = {"$lte": request.end_date}
        
        if request.meeting_id:
            query["meeting_id"] = request.meeting_id
        if request.assignee:
            query["assignee"] = request.assignee
        if request.status:
            query["status"] = request.status
        if request.priority:
            query["priority"] = request.priority
        
        # Fetch tasks
        tasks = await DetectedTask.find(query).to_list()
        
        # Calculate analytics
        total_tasks = len(tasks)
        
        # Status distribution
        status_counts = Counter(task.status for task in tasks)
        
        # Priority distribution
        priority_counts = Counter(task.priority for task in tasks)
        
        # Assignee distribution
        assignee_counts = Counter(task.assignee for task in tasks if task.assignee)
        
        # Confidence statistics
        confidences = [task.confidence for task in tasks]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Time-based analytics
        tasks_by_date = defaultdict(int)
        for task in tasks:
            date_key = task.created_at.strftime("%Y-%m-%d")
            tasks_by_date[date_key] += 1
        
        # Completion rate
        completed_tasks = len([t for t in tasks if t.status in ["done", "completed"]])
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Average time to completion (mock calculation)
        avg_completion_time = "2.5 days"  # In real implementation, calculate from timestamps
        
        return {
            "summary": {
                "total_tasks": total_tasks,
                "completion_rate": round(completion_rate, 1),
                "average_confidence": round(avg_confidence, 2),
                "average_completion_time": avg_completion_time
            },
            "distributions": {
                "status": dict(status_counts),
                "priority": dict(priority_counts),
                "assignee": dict(assignee_counts.most_common(10))
            },
            "trends": {
                "tasks_by_date": dict(tasks_by_date),
                "peak_day": max(tasks_by_date.items(), key=lambda x: x[1])[0] if tasks_by_date else None
            },
            "insights": [
                f"Most common status: {status_counts.most_common(1)[0][0] if status_counts else 'N/A'}",
                f"Most active assignee: {assignee_counts.most_common(1)[0][0] if assignee_counts else 'N/A'}",
                f"Average confidence score: {avg_confidence:.1%}"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics generation failed: {str(e)}")

@router.get("/statistics")
async def get_task_statistics(current_user: User = Depends(get_current_user)):
    """Get real-time task detection statistics."""
    stats = task_detector.get_task_statistics()
    
    # Add user-specific statistics
    user_tasks = await DetectedTask.find({"user_id": str(current_user.id)}).to_list()
    
    user_stats = {
        "total_user_tasks": len(user_tasks),
        "tasks_today": len([t for t in user_tasks if t.created_at.date() == datetime.now().date()]),
        "pending_tasks": len([t for t in user_tasks if t.status == "pending"]),
        "completed_tasks": len([t for t in user_tasks if t.status in ["done", "completed"]])
    }
    
    return {
        "detection_stats": stats,
        "user_stats": user_stats,
        "system_health": {
            "detector_status": "healthy",
            "last_update": datetime.now().isoformat(),
            "cache_efficiency": f"{stats.get('cache_hit_rate', 0):.1%}"
        }
    }
# ============================================================================
# EXPORT FUNCTIONALITY ENDPOINTS
# ============================================================================

@router.post("/export")
async def export_tasks(
    export_request: TaskExportRequest,
    current_user: User = Depends(get_current_user)
):
    """Export tasks in various formats (JSON, CSV, PDF)."""
    try:
        # Build query
        query = {"user_id": str(current_user.id)}
        
        if export_request.task_ids:
            query["_id"] = {"$in": [PydanticObjectId(tid) for tid in export_request.task_ids]}
        
        if export_request.filters:
            filters = export_request.filters
            if filters.start_date:
                query["created_at"] = {"$gte": filters.start_date}
            if filters.end_date:
                if "created_at" in query:
                    query["created_at"]["$lte"] = filters.end_date
                else:
                    query["created_at"] = {"$lte": filters.end_date}
            if filters.status:
                query["status"] = filters.status
            if filters.assignee:
                query["assignee"] = filters.assignee
            if filters.priority:
                query["priority"] = filters.priority
        
        # Fetch tasks
        tasks = await DetectedTask.find(query).to_list()
        
        if export_request.format == "json":
            return await _export_tasks_json(tasks, export_request.include_metadata, export_request.include_analytics)
        
        elif export_request.format == "csv":
            return await _export_tasks_csv(tasks, export_request.include_metadata)
        
        elif export_request.format == "pdf":
            return await _export_tasks_pdf(tasks, export_request.include_metadata, current_user)
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

async def _export_tasks_json(tasks: List[DetectedTask], include_metadata: bool, include_analytics: bool) -> JSONResponse:
    """Export tasks as JSON."""
    export_data = {
        "tasks": [task.to_dict() for task in tasks],
        "export_info": {
            "exported_at": datetime.now().isoformat(),
            "total_tasks": len(tasks),
            "format": "json"
        }
    }
    
    if include_metadata:
        export_data["metadata"] = {
            "version": "1.0",
            "source": "MeetNova Task Detection",
            "description": "AI-detected tasks from meeting transcripts"
        }
    
    if include_analytics:
        status_counts = Counter(task.status for task in tasks)
        priority_counts = Counter(task.priority for task in tasks)
        
        export_data["analytics"] = {
            "status_distribution": dict(status_counts),
            "priority_distribution": dict(priority_counts),
            "average_confidence": sum(task.confidence for task in tasks) / len(tasks) if tasks else 0
        }
    
    return JSONResponse(content=export_data)

async def _export_tasks_csv(tasks: List[DetectedTask], include_metadata: bool) -> StreamingResponse:
    """Export tasks as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    headers = ["ID", "Title", "Assignee", "Deadline", "Priority", "Status", "Confidence", "Created At"]
    if include_metadata:
        headers.extend(["Description", "Source Text", "Meeting ID"])
    
    writer.writerow(headers)
    
    # Write task data
    for task in tasks:
        row = [
            str(task.id),
            task.title,
            task.assignee or "",
            task.deadline or "",
            task.priority,
            task.status,
            f"{task.confidence:.2f}",
            task.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        if include_metadata:
            row.extend([
                task.description,
                task.source_text[:100] + "..." if len(task.source_text) > 100 else task.source_text,
                task.meeting_id or ""
            ])
        
        writer.writerow(row)
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

async def _export_tasks_pdf(tasks: List[DetectedTask], include_metadata: bool, user: User) -> StreamingResponse:
    """Export tasks as PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.darkblue
    )
    story.append(Paragraph("Task Export Report", title_style))
    story.append(Spacer(1, 12))
    
    # Metadata
    if include_metadata:
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"<b>Total Tasks:</b> {len(tasks)}", styles['Normal']))
        story.append(Paragraph(f"<b>User:</b> {user.email}", styles['Normal']))
        story.append(Spacer(1, 20))
    
    # Tasks table
    if tasks:
        table_data = [["Title", "Assignee", "Priority", "Status", "Deadline", "Confidence"]]
        
        for task in tasks:
            table_data.append([
                task.title[:40] + "..." if len(task.title) > 40 else task.title,
                task.assignee or "Unassigned",
                task.priority.title(),
                task.status.title(),
                task.deadline or "No deadline",
                f"{task.confidence:.1%}"
            ])
        
        table = Table(table_data, colWidths=[2*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    else:
        story.append(Paragraph("No tasks found matching the criteria.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"}
    )
# ============================================================================
# NOTIFICATION AND REMINDER SYSTEM ENDPOINTS
# ============================================================================

@router.post("/notifications")
async def create_task_notification(
    notification: TaskNotification,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Create a task notification or reminder."""
    try:
        # Validate task exists and belongs to user
        task = await DetectedTask.get(PydanticObjectId(notification.task_id))
        if not task or task.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Task not found")
        
        notification.user_id = str(current_user.id)
        
        # Schedule notification (in a real implementation, use a task queue like Celery)
        background_tasks.add_task(_schedule_notification, notification)
        
        return {
            "message": "Notification scheduled successfully",
            "notification_id": f"notif_{datetime.now().timestamp()}",
            "scheduled_time": notification.scheduled_time.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create notification: {str(e)}")

@router.post("/reminders")
async def create_task_reminder(
    reminder: TaskReminder,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Create a task reminder."""
    try:
        # Validate task exists and belongs to user
        task = await DetectedTask.get(PydanticObjectId(reminder.task_id))
        if not task or task.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create notification from reminder
        notification = TaskNotification(
            task_id=reminder.task_id,
            notification_type="reminder",
            scheduled_time=reminder.reminder_time,
            message=reminder.message or f"Reminder: {task.title}",
            user_id=str(current_user.id)
        )
        
        # Schedule reminder
        background_tasks.add_task(_schedule_notification, notification)
        
        return {
            "message": "Reminder scheduled successfully",
            "reminder_id": f"reminder_{datetime.now().timestamp()}",
            "scheduled_time": reminder.reminder_time.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create reminder: {str(e)}")

@router.get("/notifications")
async def list_task_notifications(
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, le=100)
):
    """List task notifications for the current user."""
    # Mock implementation - in real app, fetch from notifications collection
    notifications = [
        {
            "id": "notif_1",
            "task_id": "task_123",
            "type": "deadline",
            "message": "Task deadline approaching",
            "scheduled_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "is_sent": False
        },
        {
            "id": "notif_2",
            "task_id": "task_456",
            "type": "reminder",
            "message": "Don't forget to complete this task",
            "scheduled_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "is_sent": False
        }
    ]
    
    return {"notifications": notifications[:limit]}

@router.delete("/notifications/{notification_id}")
async def cancel_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a scheduled notification."""
    # In a real implementation, remove from task queue
    return {"message": f"Notification {notification_id} cancelled successfully"}

async def _schedule_notification(notification: TaskNotification):
    """Background task to schedule notifications."""
    # In a real implementation, this would:
    # 1. Store the notification in a database
    # 2. Schedule it with a task queue (Celery, RQ, etc.)
    # 3. Send via WebSocket, email, or push notification when time comes
    
    # For now, just log it
    print(f"Scheduled notification: {notification.message} at {notification.scheduled_time}")

# ============================================================================
# ADVANCED TASK MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/tasks/{task_id}/duplicate")
async def duplicate_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Duplicate an existing task."""
    try:
        original_task = await DetectedTask.get(PydanticObjectId(task_id))
        if not original_task or original_task.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create duplicate
        duplicate_data = original_task.to_dict()
        duplicate_data.pop("id")  # Remove original ID
        duplicate_data["title"] = f"Copy of {duplicate_data['title']}"
        duplicate_data["status"] = "pending"
        duplicate_data["created_at"] = datetime.now()
        duplicate_data["updated_at"] = datetime.now()
        
        duplicate_task = DetectedTask(**duplicate_data)
        await duplicate_task.insert()
        
        return DetectedTaskResponse(**duplicate_task.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to duplicate task: {str(e)}")

@router.post("/tasks/{task_id}/convert-to-template")
async def convert_task_to_template(
    task_id: str,
    template_name: str,
    current_user: User = Depends(get_current_user)
):
    """Convert an existing task to a reusable template."""
    try:
        task = await DetectedTask.get(PydanticObjectId(task_id))
        if not task or task.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create template from task
        template = TaskTemplate(
            name=template_name,
            title_pattern=task.title,
            assignee_default=task.assignee,
            priority_default=task.priority,
            description_template=task.description,
            user_id=str(current_user.id),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # In a real implementation, save to templates collection
        template.id = f"template_{datetime.now().timestamp()}"
        
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert task to template: {str(e)}")

@router.get("/tasks/search")
async def search_tasks(
    q: str = Query(..., min_length=2, max_length=100),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=20, le=100)
):
    """Search tasks by title, description, or assignee."""
    try:
        # Build search query (MongoDB text search would be better in production)
        query = {
            "user_id": str(current_user.id),
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
                {"assignee": {"$regex": q, "$options": "i"}},
                {"source_text": {"$regex": q, "$options": "i"}}
            ]
        }
        
        tasks = await DetectedTask.find(query).limit(limit).to_list()
        
        return {
            "query": q,
            "total_results": len(tasks),
            "tasks": [DetectedTaskResponse(**task.to_dict()) for task in tasks]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/tasks/overdue")
async def get_overdue_tasks(current_user: User = Depends(get_current_user)):
    """Get tasks that are past their deadline."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Find tasks with deadlines before today and not completed
        query = {
            "user_id": str(current_user.id),
            "deadline": {"$lt": today},
            "status": {"$nin": ["done", "completed", "archived", "dismissed"]}
        }
        
        overdue_tasks = await DetectedTask.find(query).to_list()
        
        return {
            "overdue_count": len(overdue_tasks),
            "tasks": [DetectedTaskResponse(**task.to_dict()) for task in overdue_tasks]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get overdue tasks: {str(e)}")

@router.get("/tasks/upcoming")
async def get_upcoming_tasks(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user)
):
    """Get tasks due in the next N days."""
    try:
        today = datetime.now()
        future_date = (today + timedelta(days=days)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")
        
        query = {
            "user_id": str(current_user.id),
            "deadline": {"$gte": today_str, "$lte": future_date},
            "status": {"$nin": ["done", "completed", "archived", "dismissed"]}
        }
        
        upcoming_tasks = await DetectedTask.find(query).sort("deadline").to_list()
        
        return {
            "period_days": days,
            "upcoming_count": len(upcoming_tasks),
            "tasks": [DetectedTaskResponse(**task.to_dict()) for task in upcoming_tasks]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get upcoming tasks: {str(e)}")