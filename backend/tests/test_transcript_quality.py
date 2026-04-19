"""
test_transcript_quality.py
~~~~~~~~~~~~~~~~~~~~~~~~~~

Unit tests for the transcript quality monitoring service.

Tests cover:
- Quality metrics calculation and tracking
- Alert generation and management
- Automatic quality adjustments
- Completeness validation
- Integration with transcript buffer
"""

import pytest
import time
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from services.transcript_quality import (
    QualityMetrics,
    QualityAlert,
    TranscriptQualityMonitor,
    create_quality_monitor
)
from services.transcript_buffer import TranscriptSegment


class TestQualityMetrics:
    """Test QualityMetrics dataclass functionality."""
    
    def test_quality_metrics_creation(self):
        """Test QualityMetrics creation with default values."""
        metrics = QualityMetrics()
        
        assert metrics.avg_confidence == 0.0
        assert metrics.min_confidence == 1.0
        assert metrics.max_confidence == 0.0
        assert metrics.total_segments == 0
        assert metrics.completion_rate == 1.0
        assert metrics.overall_quality_score == 1.0
        assert metrics.quality_trend == "stable"
    
    def test_quality_metrics_to_dict(self):
        """Test QualityMetrics serialization to dictionary."""
        metrics = QualityMetrics(
            avg_confidence=0.85,
            total_segments=10,
            completion_rate=0.9,
            overall_quality_score=0.8
        )
        
        result = metrics.to_dict()
        
        assert "confidence" in result
        assert "completeness" in result
        assert "accuracy" in result
        assert "latency" in result
        assert "coverage" in result
        assert "overall" in result
        
        assert result["confidence"]["average"] == 0.85
        assert result["completeness"]["total_segments"] == 10
        assert result["completeness"]["completion_rate"] == 0.9
        assert result["overall"]["quality_score"] == 0.8


class TestQualityAlert:
    """Test QualityAlert dataclass functionality."""
    
    def test_quality_alert_creation(self):
        """Test QualityAlert creation."""
        alert = QualityAlert(
            timestamp=time.time(),
            alert_type="confidence_drop",
            severity="medium",
            message="Confidence dropped significantly",
            metrics={"old_confidence": 0.9, "new_confidence": 0.7},
            suggested_actions=["Check audio quality"]
        )
        
        assert alert.alert_type == "confidence_drop"
        assert alert.severity == "medium"
        assert "confidence dropped" in alert.message.lower()
        assert len(alert.suggested_actions) == 1
    
    def test_quality_alert_to_dict(self):
        """Test QualityAlert serialization to dictionary."""
        alert = QualityAlert(
            timestamp=123456789.0,
            alert_type="latency_spike",
            severity="high",
            message="Processing time exceeded threshold",
            metrics={"processing_time": 3.5},
            suggested_actions=["Check system resources", "Verify API connectivity"]
        )
        
        result = alert.to_dict()
        
        assert result["timestamp"] == 123456789.0
        assert result["type"] == "latency_spike"
        assert result["severity"] == "high"
        assert "processing time" in result["message"].lower()
        assert len(result["suggested_actions"]) == 2


class TestTranscriptQualityMonitor:
    """Test TranscriptQualityMonitor functionality."""
    
    @pytest.fixture
    def monitor(self):
        """Create a quality monitor for testing."""
        return TranscriptQualityMonitor(
            confidence_threshold=0.7,
            quality_window_size=10,
            enable_auto_adjustment=True
        )
    
    @pytest.fixture
    def sample_segment(self):
        """Create a sample transcript segment for testing."""
        return TranscriptSegment(
            id="test_segment_1",
            text="This is a test transcript segment.",
            speaker="Speaker1",
            timestamp=time.time(),
            start_time=0.0,
            end_time=2.0,
            confidence=0.85,
            no_speech_prob=0.1,
            language="en"
        )
    
    def test_monitor_initialization(self, monitor):
        """Test quality monitor initialization."""
        assert monitor.confidence_threshold == 0.7
        assert monitor.quality_window_size == 10
        assert monitor.enable_auto_adjustment is True
        assert len(monitor.recent_segments) == 0
        assert len(monitor.active_alerts) == 0
        assert monitor.session_metrics.total_segments == 0
    
    def test_track_segment_quality_accepted(self, monitor, sample_segment):
        """Test tracking quality for an accepted segment."""
        processing_time = 0.5
        
        monitor.track_segment_quality(sample_segment, processing_time, was_filtered=False)
        
        # Check session metrics updated
        assert monitor.session_metrics.total_segments == 1
        assert monitor.session_metrics.filtered_segments == 0
        assert monitor.session_metrics.avg_confidence == 0.85
        assert monitor.session_metrics.completion_rate == 1.0
        
        # Check recent segments tracking
        assert len(monitor.recent_segments) == 1
        assert len(monitor.processing_times) == 1
        assert monitor.processing_times[0] == processing_time
    
    def test_track_segment_quality_filtered(self, monitor, sample_segment):
        """Test tracking quality for a filtered segment."""
        low_confidence_segment = TranscriptSegment(
            id="test_segment_low",
            text="Low confidence segment",
            speaker="Speaker1",
            timestamp=time.time(),
            start_time=0.0,
            end_time=1.0,
            confidence=0.5,  # Below threshold
            no_speech_prob=0.4,
            language="en"
        )
        
        processing_time = 0.3
        monitor.track_segment_quality(low_confidence_segment, processing_time, was_filtered=True)
        
        # Check session metrics
        assert monitor.session_metrics.total_segments == 1
        assert monitor.session_metrics.filtered_segments == 1
        assert monitor.session_metrics.completion_rate == 0.0
    
    def test_confidence_bucket_classification(self, monitor):
        """Test confidence bucket classification."""
        assert monitor._get_confidence_bucket(0.95) == "high (0.9-1.0)"
        assert monitor._get_confidence_bucket(0.85) == "good (0.8-0.9)"
        assert monitor._get_confidence_bucket(0.75) == "medium (0.7-0.8)"
        assert monitor._get_confidence_bucket(0.65) == "low (0.6-0.7)"
        assert monitor._get_confidence_bucket(0.5) == "very_low (<0.6)"
    
    def test_repetition_rate_calculation(self, monitor):
        """Test repetition rate calculation."""
        segments = [
            {"segment": TranscriptSegment(id="1", text="Hello world", speaker="A", timestamp=1.0, start_time=0, end_time=1, confidence=0.8)},
            {"segment": TranscriptSegment(id="2", text="Hello world", speaker="A", timestamp=2.0, start_time=1, end_time=2, confidence=0.8)},  # Exact repetition
            {"segment": TranscriptSegment(id="3", text="Different text", speaker="A", timestamp=3.0, start_time=2, end_time=3, confidence=0.8)},
        ]
        
        repetition_rate = monitor._calculate_repetition_rate(segments)
        assert repetition_rate == 0.5  # 1 repetition out of 2 comparisons
    
    def test_fragmentation_rate_calculation(self, monitor):
        """Test fragmentation rate calculation."""
        segments = [
            {"segment": TranscriptSegment(id="1", text="Complete sentence.", speaker="A", timestamp=1.0, start_time=0, end_time=1, confidence=0.8)},
            {"segment": TranscriptSegment(id="2", text="Fragment", speaker="A", timestamp=2.0, start_time=1, end_time=2, confidence=0.8)},  # Fragment
            {"segment": TranscriptSegment(id="3", text="Another complete sentence!", speaker="A", timestamp=3.0, start_time=2, end_time=3, confidence=0.8)},
        ]
        
        fragmentation_rate = monitor._calculate_fragmentation_rate(segments)
        assert fragmentation_rate == pytest.approx(0.333, abs=0.01)  # 1 fragment out of 3
    
    def test_sentence_completeness_calculation(self, monitor):
        """Test sentence completeness calculation."""
        segments = [
            {"segment": TranscriptSegment(id="1", text="Complete sentence.", speaker="A", timestamp=1.0, start_time=0, end_time=1, confidence=0.8)},
            {"segment": TranscriptSegment(id="2", text="Another complete sentence!", speaker="A", timestamp=2.0, start_time=1, end_time=2, confidence=0.8)},
            {"segment": TranscriptSegment(id="3", text="Fragment", speaker="A", timestamp=3.0, start_time=2, end_time=3, confidence=0.8)},  # Incomplete
        ]
        
        completeness = monitor._calculate_sentence_completeness(segments)
        assert completeness == pytest.approx(0.667, abs=0.01)  # 2 complete out of 3
    
    def test_overall_quality_score_calculation(self, monitor):
        """Test overall quality score calculation."""
        metrics = QualityMetrics(
            avg_confidence=0.8,
            completion_rate=0.9,
            repetition_rate=0.1,
            fragmentation_rate=0.2,
            sentence_completeness=0.8,
            avg_processing_time=1.0
        )
        
        score = monitor._calculate_overall_quality_score(metrics)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be reasonably good with these metrics
    
    def test_quality_trend_determination(self, monitor):
        """Test quality trend determination."""
        # Add some quality history
        for i, score in enumerate([0.6, 0.65, 0.7, 0.75, 0.8]):  # Improving trend
            monitor.quality_history.append({
                "timestamp": time.time() + i,
                "quality_score": score,
                "confidence": 0.8,
                "completion_rate": 0.9
            })
        
        trend = monitor._determine_quality_trend()
        assert trend == "improving"
        
        # Add declining scores
        for i, score in enumerate([0.8, 0.75, 0.7, 0.65, 0.6]):  # Declining trend
            monitor.quality_history.append({
                "timestamp": time.time() + i + 10,
                "quality_score": score,
                "confidence": 0.8,
                "completion_rate": 0.9
            })
        
        trend = monitor._determine_quality_trend()
        assert trend == "degrading"
    
    def test_alert_generation_confidence_drop(self, monitor):
        """Test alert generation for confidence drop."""
        # Add quality history with declining confidence
        base_time = time.time()
        for i in range(10):
            confidence = 0.9 - (i * 0.01)  # Gradual decline from 0.9 to 0.8
            monitor.quality_history.append({
                "timestamp": base_time + i,
                "quality_score": 0.8,
                "confidence": confidence,
                "completion_rate": 0.9
            })
        
        # Add more recent entries with significant drop
        for i in range(5):
            confidence = 0.7 - (i * 0.01)  # Drop to 0.66, creating >0.1 difference
            monitor.quality_history.append({
                "timestamp": base_time + 10 + i,
                "quality_score": 0.7,
                "confidence": confidence,
                "completion_rate": 0.9
            })
        
        # Update current metrics to trigger alert check
        monitor.current_metrics.avg_confidence = 0.66  # Significant drop
        monitor._check_quality_alerts()
        
        # Should generate confidence drop alert
        confidence_alerts = [a for a in monitor.active_alerts if a.alert_type == "confidence_drop"]
        assert len(confidence_alerts) > 0
        assert confidence_alerts[0].severity in ["medium", "high"]
    
    def test_alert_generation_latency_spike(self, monitor):
        """Test alert generation for latency spike."""
        monitor.current_metrics.avg_processing_time = 3.0  # Above threshold
        monitor._check_quality_alerts()
        
        latency_alerts = [a for a in monitor.active_alerts if a.alert_type == "latency_spike"]
        assert len(latency_alerts) > 0
        assert latency_alerts[0].severity in ["medium", "high"]
    
    def test_alert_generation_completion_rate_drop(self, monitor):
        """Test alert generation for completion rate drop."""
        monitor.current_metrics.completion_rate = 0.6  # Below threshold
        monitor._check_quality_alerts()
        
        completion_alerts = [a for a in monitor.active_alerts if a.alert_type == "completion_rate_drop"]
        assert len(completion_alerts) > 0
        assert completion_alerts[0].severity == "high"
    
    def test_auto_adjustment_confidence_threshold(self, monitor):
        """Test automatic confidence threshold adjustment."""
        # Set up conditions for threshold reduction
        monitor.current_metrics.completion_rate = 0.6  # Low completion rate
        monitor.confidence_threshold = 0.7
        monitor.last_adjustment_time = 0  # Allow adjustment
        
        monitor._apply_auto_adjustments()
        
        # Should reduce confidence threshold
        assert monitor.confidence_threshold < 0.7
        assert len(monitor.adjustment_history) > 0
        assert monitor.adjustment_history[-1]["adjustments"][0]["type"] == "confidence_threshold"
    
    def test_auto_adjustment_cooldown(self, monitor):
        """Test auto-adjustment cooldown period."""
        monitor.current_metrics.completion_rate = 0.6
        monitor.confidence_threshold = 0.7
        monitor.last_adjustment_time = time.time()  # Recent adjustment
        
        initial_threshold = monitor.confidence_threshold
        monitor._apply_auto_adjustments()
        
        # Should not adjust due to cooldown
        assert monitor.confidence_threshold == initial_threshold
    
    def test_validate_transcript_completeness_empty(self, monitor):
        """Test completeness validation with empty segments."""
        result = monitor.validate_transcript_completeness([])
        
        assert result["is_complete"] is False
        assert result["completeness_score"] == 0.0
        assert "No transcript segments found" in result["issues"]
    
    def test_validate_transcript_completeness_good(self, monitor):
        """Test completeness validation with good quality segments."""
        segments = [
            TranscriptSegment(
                id=f"seg_{i}",
                text=f"This is segment {i} with good quality.",
                speaker="Speaker1",
                timestamp=time.time() + i,
                start_time=i * 2.0,
                end_time=(i + 1) * 2.0,
                confidence=0.9,
                no_speech_prob=0.05,
                language="en"
            )
            for i in range(5)
        ]
        
        result = monitor.validate_transcript_completeness(segments, expected_duration=10.0)
        
        assert result["is_complete"] is True
        assert result["completeness_score"] > 0.8
        assert result["total_segments"] == 5
        assert len(result["issues"]) == 0
    
    def test_validate_transcript_completeness_issues(self, monitor):
        """Test completeness validation with quality issues."""
        segments = [
            # Low confidence segment
            TranscriptSegment(id="seg_1", text="Low confidence", speaker="A", timestamp=1.0, start_time=0, end_time=1, confidence=0.5),
            # Very short segment
            TranscriptSegment(id="seg_2", text="Hi", speaker="A", timestamp=2.0, start_time=1, end_time=2, confidence=0.8),
            # Good segment with time gap
            TranscriptSegment(id="seg_3", text="Good segment after gap.", speaker="A", timestamp=10.0, start_time=8, end_time=10, confidence=0.9),
        ]
        
        result = monitor.validate_transcript_completeness(segments, expected_duration=10.0)
        
        assert result["is_complete"] is False
        assert result["completeness_score"] < 0.8
        assert result["low_confidence_segments"] > 0
        assert result["short_segments"] > 0
        assert result["time_gaps"] > 0
        assert len(result["issues"]) > 0
    
    def test_generate_quality_report(self, monitor, sample_segment):
        """Test comprehensive quality report generation."""
        # Add some data
        monitor.track_segment_quality(sample_segment, 0.5, was_filtered=False)
        
        report = monitor.generate_quality_report()
        
        assert "timestamp" in report
        assert "session_metrics" in report
        assert "current_metrics" in report
        assert "active_alerts" in report
        assert "quality_history" in report
        assert "adjustment_history" in report
        assert "configuration" in report
        assert "recommendations" in report
        
        assert isinstance(report["recommendations"], list)
    
    def test_reset_session_metrics(self, monitor, sample_segment):
        """Test session metrics reset."""
        # Add some data
        monitor.track_segment_quality(sample_segment, 0.5, was_filtered=False)
        
        assert monitor.session_metrics.total_segments == 1
        assert len(monitor.recent_segments) == 1
        
        monitor.reset_session_metrics()
        
        assert monitor.session_metrics.total_segments == 0
        assert len(monitor.recent_segments) == 0
        assert len(monitor.quality_history) == 0
        assert len(monitor.active_alerts) == 0


class TestQualityMonitorFactory:
    """Test quality monitor factory function."""
    
    def test_create_quality_monitor_defaults(self):
        """Test creating quality monitor with default settings."""
        monitor = create_quality_monitor()
        
        assert monitor.confidence_threshold == 0.7
        assert monitor.quality_window_size == 50
        assert monitor.enable_auto_adjustment is True
        assert isinstance(monitor.alert_thresholds, dict)
    
    def test_create_quality_monitor_custom(self):
        """Test creating quality monitor with custom settings."""
        custom_thresholds = {
            "confidence_drop": 0.15,
            "latency_spike": 3.0
        }
        
        monitor = create_quality_monitor(
            confidence_threshold=0.8,
            quality_window_size=30,
            alert_thresholds=custom_thresholds,
            enable_auto_adjustment=False
        )
        
        assert monitor.confidence_threshold == 0.8
        assert monitor.quality_window_size == 30
        assert monitor.enable_auto_adjustment is False
        assert monitor.alert_thresholds["confidence_drop"] == 0.15
        assert monitor.alert_thresholds["latency_spike"] == 3.0


class TestQualityMonitorIntegration:
    """Integration tests for quality monitor with transcript buffer."""
    
    @pytest.fixture
    def mock_transcript_buffer(self):
        """Create a mock transcript buffer for integration testing."""
        from services.transcript_buffer import TranscriptBuffer
        
        buffer = TranscriptBuffer(
            enable_quality_monitoring=True,
            quality_monitor_config={
                "quality_window_size": 10,
                "enable_auto_adjustment": True
            }
        )
        return buffer
    
    def test_quality_monitor_integration(self, mock_transcript_buffer):
        """Test quality monitor integration with transcript buffer."""
        buffer = mock_transcript_buffer
        
        # Should have quality monitor enabled
        assert buffer.enable_quality_monitoring is True
        assert buffer.quality_monitor is not None
        
        # Test quality metrics access
        metrics = buffer.get_quality_metrics()
        assert metrics is not None
        assert "confidence" in metrics
        
        # Test quality alerts access
        alerts = buffer.get_quality_alerts()
        assert isinstance(alerts, list)
        
        # Test quality report generation
        report = buffer.get_quality_report()
        assert report is not None
        assert "session_metrics" in report
    
    def test_quality_monitoring_disabled(self):
        """Test transcript buffer with quality monitoring disabled."""
        from services.transcript_buffer import TranscriptBuffer
        
        buffer = TranscriptBuffer(enable_quality_monitoring=False)
        
        assert buffer.enable_quality_monitoring is False
        assert buffer.quality_monitor is None
        
        # Should return None for quality methods
        assert buffer.get_quality_metrics() is None
        assert buffer.get_session_quality_metrics() is None
        assert buffer.get_quality_alerts() == []
        assert buffer.get_quality_report() is None
        assert buffer.validate_transcript_completeness() is None