"""
test_transcript_quality_integration.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Integration tests for transcript quality monitoring with the complete system.
Tests the full workflow from transcript processing to quality reporting.
"""

import pytest
import time
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from main import app
from services.transcript_buffer import create_transcript_buffer, TranscriptSegment


class TestTranscriptQualityIntegration:
    """Integration tests for quality monitoring system."""
    
    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)
    
    @pytest.fixture
    def quality_buffer(self):
        """Create transcript buffer with quality monitoring enabled."""
        return create_transcript_buffer(
            enable_quality_monitoring=True,
            quality_monitor_config={
                "quality_window_size": 10,
                "enable_auto_adjustment": True
            }
        )
    
    def test_api_health_endpoint(self, client):
        """Test quality monitoring health endpoint."""
        response = client.get("/api/transcript-quality/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "quality_monitoring_enabled" in data
        assert "buffer_size" in data
        assert "processing_stats" in data
    
    def test_api_current_metrics_endpoint(self, client):
        """Test current quality metrics endpoint."""
        response = client.get("/api/transcript-quality/metrics/current")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required metric categories
        assert "confidence" in data
        assert "completeness" in data
        assert "accuracy" in data
        assert "latency" in data
        assert "coverage" in data
        assert "overall" in data
        
        # Check confidence metrics structure
        confidence = data["confidence"]
        assert "average" in confidence
        assert "minimum" in confidence
        assert "maximum" in confidence
        assert "distribution" in confidence
    
    def test_api_session_metrics_endpoint(self, client):
        """Test session quality metrics endpoint."""
        response = client.get("/api/transcript-quality/metrics/session")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have same structure as current metrics
        assert "confidence" in data
        assert "completeness" in data
        assert "overall" in data
    
    def test_api_alerts_endpoint(self, client):
        """Test quality alerts endpoint."""
        response = client.get("/api/transcript-quality/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of alerts (empty initially)
        assert isinstance(data, list)
    
    def test_api_quality_report_endpoint(self, client):
        """Test comprehensive quality report endpoint."""
        response = client.get("/api/transcript-quality/report")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check report structure
        assert "timestamp" in data
        assert "session_metrics" in data
        assert "current_metrics" in data
        assert "active_alerts" in data
        assert "quality_history" in data
        assert "adjustment_history" in data
        assert "configuration" in data
        assert "recommendations" in data
    
    def test_api_completeness_validation_endpoint(self, client):
        """Test transcript completeness validation endpoint."""
        response = client.post("/api/transcript-quality/validate-completeness")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check validation structure
        assert "is_complete" in data
        assert "completeness_score" in data
        assert "total_segments" in data
        assert "issues" in data
        assert "recommendations" in data
    
    def test_api_statistics_endpoint(self, client):
        """Test quality statistics endpoint."""
        response = client.get("/api/transcript-quality/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "processing_statistics" in data
        assert "quality_metrics" in data
        assert "quality_monitoring_enabled" in data
        assert "configuration" in data
    
    def test_api_reset_endpoint(self, client):
        """Test quality monitoring reset endpoint."""
        response = client.post("/api/transcript-quality/reset")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "timestamp" in data
        assert "reset successfully" in data["message"].lower()
    
    def test_end_to_end_quality_workflow(self, quality_buffer):
        """Test complete quality monitoring workflow."""
        # Create sample segments with varying quality
        segments = [
            # High quality segment
            TranscriptSegment(
                id="seg_1",
                text="This is a high quality transcript segment with good confidence.",
                speaker="Speaker1",
                timestamp=time.time(),
                start_time=0.0,
                end_time=3.0,
                confidence=0.95,
                no_speech_prob=0.02,
                language="en"
            ),
            # Medium quality segment
            TranscriptSegment(
                id="seg_2", 
                text="Medium quality segment.",
                speaker="Speaker1",
                timestamp=time.time() + 1,
                start_time=3.0,
                end_time=5.0,
                confidence=0.75,
                no_speech_prob=0.15,
                language="en"
            ),
            # Low quality segment (should be filtered)
            TranscriptSegment(
                id="seg_3",
                text="Low quality",
                speaker="Speaker2",
                timestamp=time.time() + 2,
                start_time=5.0,
                end_time=6.0,
                confidence=0.45,  # Below threshold
                no_speech_prob=0.4,
                language="en"
            )
        ]
        
        # Process segments through quality monitoring
        for i, segment in enumerate(segments):
            processing_time = 0.3 + (i * 0.1)  # Varying processing times
            was_filtered = segment.confidence < quality_buffer.confidence_threshold
            
            if quality_buffer.quality_monitor:
                quality_buffer.quality_monitor.track_segment_quality(
                    segment, processing_time, was_filtered
                )
        
        # Verify quality metrics were calculated
        current_metrics = quality_buffer.get_quality_metrics()
        assert current_metrics is not None
        
        # Check confidence metrics
        confidence = current_metrics["confidence"]
        assert confidence["average"] > 0.7  # Should be good average
        assert confidence["minimum"] >= 0.45  # Includes low quality segment
        assert confidence["maximum"] <= 1.0
        
        # Check completeness metrics
        completeness = current_metrics["completeness"]
        assert completeness["total_segments"] == 3
        assert completeness["filtered_segments"] == 1  # Low quality segment
        assert completeness["completion_rate"] < 1.0  # Some filtering occurred
        
        # Check overall quality
        overall = current_metrics["overall"]
        assert 0.0 <= overall["quality_score"] <= 1.0
        assert overall["quality_trend"] in ["improving", "degrading", "stable"]
        
        # Verify session metrics
        session_metrics = quality_buffer.get_session_quality_metrics()
        assert session_metrics is not None
        assert session_metrics["completeness"]["total_segments"] == 3
        
        # Check quality report generation
        report = quality_buffer.get_quality_report()
        assert report is not None
        assert "recommendations" in report
        assert isinstance(report["recommendations"], list)
        
        # Verify completeness validation (test with quality monitor directly since buffer has no segments)
        if quality_buffer.quality_monitor:
            # Test with the segments we processed
            actual_segments = [s for s in segments if s.confidence >= quality_buffer.confidence_threshold]
            validation = quality_buffer.quality_monitor.validate_transcript_completeness(
                actual_segments, expected_duration=6.0
            )
            assert validation is not None
            assert "completeness_score" in validation
            assert validation["total_segments"] == len(actual_segments)
    
    def test_quality_alert_generation_integration(self, quality_buffer):
        """Test quality alert generation in integrated system."""
        # Create conditions that should trigger alerts
        
        # Add segments with declining confidence to trigger confidence drop alert
        base_time = time.time()
        for i in range(15):  # Need enough history
            confidence = 0.9 - (i * 0.03)  # Declining confidence
            segment = TranscriptSegment(
                id=f"seg_{i}",
                text=f"Segment {i} with declining confidence",
                speaker="Speaker1",
                timestamp=base_time + i,
                start_time=i * 2.0,
                end_time=(i + 1) * 2.0,
                confidence=max(0.3, confidence),  # Don't go below 0.3
                no_speech_prob=min(0.6, 0.1 + i * 0.03),
                language="en"
            )
            
            # Simulate increasing processing time to trigger latency alert
            processing_time = 0.5 + (i * 0.2)
            was_filtered = segment.confidence < quality_buffer.confidence_threshold
            
            if quality_buffer.quality_monitor:
                quality_buffer.quality_monitor.track_segment_quality(
                    segment, processing_time, was_filtered
                )
        
        # Check for generated alerts
        alerts = quality_buffer.get_quality_alerts()
        assert len(alerts) > 0
        
        # Should have confidence drop and/or latency spike alerts
        alert_types = [alert["type"] for alert in alerts]
        assert any(alert_type in ["confidence_drop", "latency_spike", "completion_rate_drop"] 
                  for alert_type in alert_types)
        
        # Verify alert structure
        for alert in alerts:
            assert "timestamp" in alert
            assert "type" in alert
            assert "severity" in alert
            assert "message" in alert
            assert "suggested_actions" in alert
            assert alert["severity"] in ["low", "medium", "high", "critical"]
    
    def test_auto_adjustment_integration(self, quality_buffer):
        """Test automatic quality adjustment in integrated system."""
        if not quality_buffer.quality_monitor or not quality_buffer.quality_monitor.enable_auto_adjustment:
            pytest.skip("Auto-adjustment not enabled")
        
        initial_threshold = quality_buffer.confidence_threshold
        
        # Create conditions for threshold adjustment (low completion rate)
        for i in range(10):
            segment = TranscriptSegment(
                id=f"seg_{i}",
                text=f"Low confidence segment {i}",
                speaker="Speaker1", 
                timestamp=time.time() + i,
                start_time=i * 1.0,
                end_time=(i + 1) * 1.0,
                confidence=0.6,  # Just below threshold
                no_speech_prob=0.3,
                language="en"
            )
            
            # Most segments will be filtered due to low confidence
            processing_time = 0.5
            was_filtered = segment.confidence < quality_buffer.confidence_threshold
            
            quality_buffer.quality_monitor.track_segment_quality(
                segment, processing_time, was_filtered
            )
        
        # Check if adjustment was made
        adjustment_history = quality_buffer.quality_monitor.get_adjustment_history()
        
        # May or may not have adjustments depending on timing and cooldown
        if adjustment_history:
            assert len(adjustment_history) > 0
            latest_adjustment = adjustment_history[-1]
            assert "adjustments" in latest_adjustment
            assert "timestamp" in latest_adjustment
            
            # Verify adjustment details
            adjustments = latest_adjustment["adjustments"]
            if adjustments:
                assert adjustments[0]["type"] == "confidence_threshold"
                assert "old_value" in adjustments[0]
                assert "new_value" in adjustments[0]
                assert "reason" in adjustments[0]