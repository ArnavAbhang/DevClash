"""
transcript_quality.py
~~~~~~~~~~~~~~~~~~~~~

API endpoints for transcript quality monitoring and reporting.

This module provides REST endpoints for accessing quality metrics,
alerts, and reports from the transcript quality monitoring system.
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from services.transcript_buffer import create_transcript_buffer
from services.transcript_quality import create_quality_monitor

router = APIRouter(prefix="/api/transcript-quality", tags=["transcript-quality"])

# Global quality monitor instance (in production, this would be session-based)
_quality_monitor = None
_transcript_buffer = None


def get_quality_monitor():
    """Get or create quality monitor instance."""
    global _quality_monitor, _transcript_buffer
    if _quality_monitor is None:
        _transcript_buffer = create_transcript_buffer(enable_quality_monitoring=True)
        _quality_monitor = _transcript_buffer.quality_monitor
    return _quality_monitor


def get_transcript_buffer():
    """Get or create transcript buffer instance."""
    global _transcript_buffer
    if _transcript_buffer is None:
        _transcript_buffer = create_transcript_buffer(enable_quality_monitoring=True)
    return _transcript_buffer


# Response models
class QualityMetricsResponse(BaseModel):
    """Response model for quality metrics."""
    confidence: Dict[str, Any] = Field(..., description="Confidence-related metrics")
    completeness: Dict[str, Any] = Field(..., description="Completeness metrics")
    accuracy: Dict[str, Any] = Field(..., description="Accuracy metrics")
    latency: Dict[str, Any] = Field(..., description="Latency metrics")
    coverage: Dict[str, Any] = Field(..., description="Coverage metrics")
    overall: Dict[str, Any] = Field(..., description="Overall quality metrics")


class QualityAlertResponse(BaseModel):
    """Response model for quality alerts."""
    timestamp: float = Field(..., description="Alert timestamp")
    type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    message: str = Field(..., description="Alert message")
    metrics: Dict[str, Any] = Field(..., description="Related metrics")
    suggested_actions: List[str] = Field(..., description="Suggested actions")


class QualityReportResponse(BaseModel):
    """Response model for comprehensive quality report."""
    timestamp: float = Field(..., description="Report timestamp")
    session_metrics: Dict[str, Any] = Field(..., description="Session metrics")
    current_metrics: Dict[str, Any] = Field(..., description="Current metrics")
    active_alerts: List[Dict[str, Any]] = Field(..., description="Active alerts")
    quality_history: List[Dict[str, Any]] = Field(..., description="Quality history")
    adjustment_history: List[Dict[str, Any]] = Field(..., description="Adjustment history")
    configuration: Dict[str, Any] = Field(..., description="Monitor configuration")
    recommendations: List[str] = Field(..., description="Quality recommendations")


class CompletenessValidationResponse(BaseModel):
    """Response model for transcript completeness validation."""
    is_complete: bool = Field(..., description="Whether transcript is complete")
    completeness_score: float = Field(..., description="Completeness score (0-1)")
    total_segments: int = Field(..., description="Total number of segments")
    time_gaps: int = Field(..., description="Number of time gaps found")
    low_confidence_segments: int = Field(..., description="Number of low confidence segments")
    short_segments: int = Field(..., description="Number of short segments")
    coverage_score: float = Field(..., description="Duration coverage score")
    issues: List[str] = Field(..., description="Identified issues")
    recommendations: List[str] = Field(..., description="Improvement recommendations")


@router.get("/metrics/current", response_model=QualityMetricsResponse)
async def get_current_quality_metrics():
    """
    Get current quality metrics based on recent transcript segments.
    
    Returns:
        Current quality metrics including confidence, completeness, accuracy, and latency
    """
    buffer = get_transcript_buffer()
    metrics = buffer.get_quality_metrics()
    
    if metrics is None:
        raise HTTPException(
            status_code=503, 
            detail="Quality monitoring is not enabled"
        )
    
    return QualityMetricsResponse(**metrics)


@router.get("/metrics/session", response_model=QualityMetricsResponse)
async def get_session_quality_metrics():
    """
    Get cumulative session quality metrics.
    
    Returns:
        Session-wide quality metrics since the session started
    """
    buffer = get_transcript_buffer()
    metrics = buffer.get_session_quality_metrics()
    
    if metrics is None:
        raise HTTPException(
            status_code=503, 
            detail="Quality monitoring is not enabled"
        )
    
    return QualityMetricsResponse(**metrics)


@router.get("/alerts", response_model=List[QualityAlertResponse])
async def get_quality_alerts():
    """
    Get currently active quality alerts.
    
    Returns:
        List of active quality alerts with severity and suggested actions
    """
    buffer = get_transcript_buffer()
    alerts = buffer.get_quality_alerts()
    
    return [QualityAlertResponse(**alert) for alert in alerts]


@router.get("/report", response_model=QualityReportResponse)
async def get_quality_report():
    """
    Generate comprehensive quality report.
    
    Returns:
        Comprehensive quality report with metrics, alerts, history, and recommendations
    """
    buffer = get_transcript_buffer()
    report = buffer.get_quality_report()
    
    if report is None:
        raise HTTPException(
            status_code=503, 
            detail="Quality monitoring is not enabled"
        )
    
    return QualityReportResponse(**report)


@router.get("/history")
async def get_quality_history(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of history entries")
):
    """
    Get quality history for trend analysis.
    
    Args:
        limit: Maximum number of history entries to return
        
    Returns:
        List of quality history entries with timestamps and scores
    """
    monitor = get_quality_monitor()
    history = monitor.get_quality_history(limit)
    
    return {
        "history": history,
        "count": len(history),
        "limit": limit
    }


@router.get("/adjustments")
async def get_adjustment_history(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of adjustment entries")
):
    """
    Get history of automatic quality adjustments.
    
    Args:
        limit: Maximum number of adjustment entries to return
        
    Returns:
        List of automatic adjustment entries with details and reasons
    """
    monitor = get_quality_monitor()
    adjustments = monitor.get_adjustment_history(limit)
    
    return {
        "adjustments": adjustments,
        "count": len(adjustments),
        "limit": limit
    }


@router.post("/validate-completeness", response_model=CompletenessValidationResponse)
async def validate_transcript_completeness(
    expected_duration: Optional[float] = Query(
        None, 
        ge=0, 
        description="Expected audio duration in seconds"
    )
):
    """
    Validate transcript completeness against expected criteria.
    
    Args:
        expected_duration: Expected audio duration in seconds for coverage validation
        
    Returns:
        Completeness validation results with issues and recommendations
    """
    buffer = get_transcript_buffer()
    validation = buffer.validate_transcript_completeness(expected_duration)
    
    if validation is None:
        raise HTTPException(
            status_code=503, 
            detail="Quality monitoring is not enabled"
        )
    
    # Ensure all required fields are present for the response model
    validation_response = {
        "is_complete": validation.get("is_complete", False),
        "completeness_score": validation.get("completeness_score", 0.0),
        "total_segments": validation.get("total_segments", 0),
        "time_gaps": validation.get("time_gaps", 0),
        "low_confidence_segments": validation.get("low_confidence_segments", 0),
        "short_segments": validation.get("short_segments", 0),
        "coverage_score": validation.get("coverage_score", 1.0),
        "issues": validation.get("issues", []),
        "recommendations": validation.get("recommendations", [])
    }
    
    return CompletenessValidationResponse(**validation_response)


@router.get("/statistics")
async def get_quality_statistics():
    """
    Get comprehensive quality statistics and processing information.
    
    Returns:
        Combined quality and processing statistics
    """
    buffer = get_transcript_buffer()
    monitor = get_quality_monitor()
    
    processing_stats = buffer.get_processing_statistics()
    quality_metrics = buffer.get_quality_metrics()
    active_alerts = buffer.get_quality_alerts()
    
    return {
        "processing_statistics": processing_stats,
        "quality_metrics": quality_metrics,
        "active_alerts_count": len(active_alerts),
        "quality_monitoring_enabled": quality_metrics is not None,
        "configuration": {
            "confidence_threshold": buffer.confidence_threshold,
            "enable_speaker_identification": buffer.enable_speaker_identification,
            "enable_intelligent_buffering": buffer.enable_intelligent_buffering,
            "enable_quality_monitoring": buffer.enable_quality_monitoring
        }
    }


@router.post("/reset")
async def reset_quality_monitoring():
    """
    Reset quality monitoring for a new session.
    
    Returns:
        Confirmation of reset operation
    """
    buffer = get_transcript_buffer()
    buffer.clear_buffer()  # This will also reset quality monitor
    
    return {
        "message": "Quality monitoring reset successfully",
        "timestamp": buffer.last_processed_time
    }


@router.get("/health")
async def quality_monitoring_health():
    """
    Check health status of quality monitoring system.
    
    Returns:
        Health status and system information
    """
    buffer = get_transcript_buffer()
    monitor = get_quality_monitor()
    
    return {
        "status": "healthy",
        "quality_monitoring_enabled": buffer.enable_quality_monitoring,
        "buffer_size": len(buffer.segments),
        "processing_stats": buffer.get_processing_statistics(),
        "active_alerts": len(buffer.get_quality_alerts()) if buffer.enable_quality_monitoring else 0,
        "timestamp": buffer.last_processed_time
    }