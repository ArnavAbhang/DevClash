"""
transcript_quality.py
~~~~~~~~~~~~~~~~~~~~~

Transcript Quality Monitoring Service for MeetNova Production Upgrade

This service provides comprehensive quality assessment, real-time monitoring, 
and automatic adjustments to ensure optimal transcription performance. It integrates 
with the existing TranscriptBuffer service and provides quality metrics for the UI.

Features:
- Confidence score tracking and reporting
- Transcript completeness validation  
- Quality metrics collection (accuracy, latency, coverage)
- Automatic quality adjustment based on performance
- Real-time quality indicators for the UI
- Performance analytics and reporting

Requirements: 2.5, 2.7, 9.7
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from statistics import mean, median, stdev
import logging

from .transcript_buffer import TranscriptSegment, TranscriptBuffer

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Quality metrics for transcript segments and overall session."""
    
    # Confidence metrics
    avg_confidence: float = 0.0
    min_confidence: float = 1.0
    max_confidence: float = 0.0
    confidence_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Completeness metrics
    total_segments: int = 0
    filtered_segments: int = 0
    completion_rate: float = 1.0
    
    # Accuracy metrics (estimated)
    repetition_rate: float = 0.0
    fragmentation_rate: float = 0.0
    sentence_completeness: float = 1.0
    
    # Latency metrics
    avg_processing_time: float = 0.0
    max_processing_time: float = 0.0
    processing_times: List[float] = field(default_factory=list)
    
    # Coverage metrics
    audio_coverage: float = 1.0  # Percentage of audio successfully transcribed
    silence_detection_accuracy: float = 1.0
    
    # Quality indicators
    overall_quality_score: float = 1.0
    quality_trend: str = "stable"  # "improving", "degrading", "stable"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for API responses."""
        return {
            "confidence": {
                "average": self.avg_confidence,
                "minimum": self.min_confidence,
                "maximum": self.max_confidence,
                "distribution": self.confidence_distribution
            },
            "completeness": {
                "total_segments": self.total_segments,
                "filtered_segments": self.filtered_segments,
                "completion_rate": self.completion_rate
            },
            "accuracy": {
                "repetition_rate": self.repetition_rate,
                "fragmentation_rate": self.fragmentation_rate,
                "sentence_completeness": self.sentence_completeness
            },
            "latency": {
                "average_processing_time": self.avg_processing_time,
                "max_processing_time": self.max_processing_time,
                "processing_count": len(self.processing_times)
            },
            "coverage": {
                "audio_coverage": self.audio_coverage,
                "silence_detection_accuracy": self.silence_detection_accuracy
            },
            "overall": {
                "quality_score": self.overall_quality_score,
                "quality_trend": self.quality_trend
            }
        }


@dataclass
class QualityAlert:
    """Quality alert for significant quality degradation."""
    
    timestamp: float
    alert_type: str  # "confidence_drop", "latency_spike", "accuracy_degradation"
    severity: str  # "low", "medium", "high", "critical"
    message: str
    metrics: Dict[str, Any]
    suggested_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for API responses."""
        return {
            "timestamp": self.timestamp,
            "type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "metrics": self.metrics,
            "suggested_actions": self.suggested_actions
        }


class TranscriptQualityMonitor:
    """
    Comprehensive transcript quality monitoring and adjustment service.
    
    This service monitors transcript quality in real-time, collects metrics,
    detects quality issues, and provides automatic adjustments to maintain
    optimal transcription performance.
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.7,
        quality_window_size: int = 50,
        alert_thresholds: Optional[Dict[str, float]] = None,
        enable_auto_adjustment: bool = True
    ):
        """
        Initialize the quality monitor.
        
        Args:
            confidence_threshold: Minimum confidence threshold for segments
            quality_window_size: Number of recent segments to consider for quality trends
            alert_thresholds: Custom thresholds for quality alerts
            enable_auto_adjustment: Whether to enable automatic quality adjustments
        """
        self.confidence_threshold = confidence_threshold
        self.quality_window_size = quality_window_size
        self.enable_auto_adjustment = enable_auto_adjustment
        
        # Quality tracking
        self.recent_segments: deque = deque(maxlen=quality_window_size)
        self.processing_times: deque = deque(maxlen=quality_window_size)
        self.quality_history: deque = deque(maxlen=100)  # Store quality scores over time
        
        # Metrics tracking
        self.session_metrics = QualityMetrics()
        self.current_metrics = QualityMetrics()
        
        # Alert system
        self.alert_thresholds = alert_thresholds or {
            "confidence_drop": 0.1,  # Alert if avg confidence drops by 10%
            "latency_spike": 2.0,    # Alert if processing time > 2 seconds
            "accuracy_degradation": 0.15,  # Alert if accuracy drops by 15%
            "completion_rate_drop": 0.2   # Alert if completion rate drops by 20%
        }
        self.active_alerts: List[QualityAlert] = []
        
        # Auto-adjustment parameters
        self.adjustment_history: List[Dict[str, Any]] = []
        self.last_adjustment_time = 0.0
        self.adjustment_cooldown = 30.0  # Minimum seconds between adjustments
        
        logger.info(f"TranscriptQualityMonitor initialized with threshold={confidence_threshold}")
    
    def track_segment_quality(
        self, 
        segment: TranscriptSegment, 
        processing_time: float,
        was_filtered: bool = False
    ) -> None:
        """
        Track quality metrics for a processed transcript segment.
        
        Args:
            segment: The transcript segment to analyze
            processing_time: Time taken to process this segment
            was_filtered: Whether the segment was filtered out due to low quality
        """
        current_time = time.time()
        
        # Add to recent segments for trend analysis
        segment_data = {
            "segment": segment,
            "processing_time": processing_time,
            "was_filtered": was_filtered,
            "timestamp": current_time
        }
        self.recent_segments.append(segment_data)
        self.processing_times.append(processing_time)
        
        # Update session metrics
        self._update_session_metrics(segment, processing_time, was_filtered)
        
        # Calculate current quality metrics
        self._calculate_current_metrics()
        
        # Check for quality alerts
        self._check_quality_alerts()
        
        # Apply automatic adjustments if enabled
        if self.enable_auto_adjustment:
            self._apply_auto_adjustments()
    
    def _update_session_metrics(
        self, 
        segment: TranscriptSegment, 
        processing_time: float, 
        was_filtered: bool
    ) -> None:
        """Update cumulative session metrics."""
        metrics = self.session_metrics
        
        # Update segment counts
        metrics.total_segments += 1
        if was_filtered:
            metrics.filtered_segments += 1
        
        # Update confidence metrics
        if not was_filtered:
            confidence = segment.confidence
            if metrics.total_segments == 1:
                metrics.avg_confidence = confidence
                metrics.min_confidence = confidence
                metrics.max_confidence = confidence
            else:
                # Running average
                n = metrics.total_segments - metrics.filtered_segments
                metrics.avg_confidence = ((metrics.avg_confidence * (n - 1)) + confidence) / n
                metrics.min_confidence = min(metrics.min_confidence, confidence)
                metrics.max_confidence = max(metrics.max_confidence, confidence)
        
        # Update processing time metrics
        metrics.processing_times.append(processing_time)
        metrics.avg_processing_time = mean(metrics.processing_times)
        metrics.max_processing_time = max(metrics.max_processing_time, processing_time)
        
        # Update completion rate
        metrics.completion_rate = 1.0 - (metrics.filtered_segments / metrics.total_segments)
        
        # Update confidence distribution
        confidence_bucket = self._get_confidence_bucket(segment.confidence)
        if confidence_bucket not in metrics.confidence_distribution:
            metrics.confidence_distribution[confidence_bucket] = 0
        metrics.confidence_distribution[confidence_bucket] += 1
    
    def _calculate_current_metrics(self) -> None:
        """Calculate current quality metrics based on recent segments."""
        if not self.recent_segments:
            return
        
        recent_data = list(self.recent_segments)
        valid_segments = [d for d in recent_data if not d["was_filtered"]]
        
        metrics = self.current_metrics
        
        # Always calculate completion rate and processing times
        total_recent = len(recent_data)
        filtered_recent = len([d for d in recent_data if d["was_filtered"]])
        metrics.completion_rate = 1.0 - (filtered_recent / total_recent) if total_recent > 0 else 1.0
        metrics.total_segments = total_recent
        metrics.filtered_segments = filtered_recent
        
        # Processing time metrics (for all segments)
        processing_times = [d["processing_time"] for d in recent_data]
        metrics.avg_processing_time = mean(processing_times)
        metrics.max_processing_time = max(processing_times)
        
        # Confidence metrics (only for valid segments)
        if valid_segments:
            confidences = [d["segment"].confidence for d in valid_segments]
            metrics.avg_confidence = mean(confidences)
            metrics.min_confidence = min(confidences)
            metrics.max_confidence = max(confidences)
            
            # Accuracy estimation
            metrics.repetition_rate = self._calculate_repetition_rate(valid_segments)
            metrics.fragmentation_rate = self._calculate_fragmentation_rate(valid_segments)
            metrics.sentence_completeness = self._calculate_sentence_completeness(valid_segments)
        else:
            # No valid segments - set defaults
            metrics.avg_confidence = 0.0
            metrics.min_confidence = 0.0
            metrics.max_confidence = 0.0
            metrics.repetition_rate = 0.0
            metrics.fragmentation_rate = 1.0  # All segments were fragmented/filtered
            metrics.sentence_completeness = 0.0
        
        # Overall quality score
        metrics.overall_quality_score = self._calculate_overall_quality_score(metrics)
        
        # Quality trend
        metrics.quality_trend = self._determine_quality_trend()
        
        # Store quality score in history
        self.quality_history.append({
            "timestamp": time.time(),
            "quality_score": metrics.overall_quality_score,
            "confidence": metrics.avg_confidence,
            "completion_rate": metrics.completion_rate
        })
    
    def _get_confidence_bucket(self, confidence: float) -> str:
        """Get confidence bucket for distribution tracking."""
        if confidence >= 0.9:
            return "high (0.9-1.0)"
        elif confidence >= 0.8:
            return "good (0.8-0.9)"
        elif confidence >= 0.7:
            return "medium (0.7-0.8)"
        elif confidence >= 0.6:
            return "low (0.6-0.7)"
        else:
            return "very_low (<0.6)"
    
    def _calculate_repetition_rate(self, valid_segments: List[Dict]) -> float:
        """Calculate the rate of repetitive content in recent segments."""
        if len(valid_segments) < 2:
            return 0.0
        
        texts = [d["segment"].text.lower().strip() for d in valid_segments]
        repetitions = 0
        
        for i in range(1, len(texts)):
            # Check for exact repetitions
            if texts[i] == texts[i-1]:
                repetitions += 1
            # Check for high similarity (>90%)
            elif self._calculate_text_similarity(texts[i], texts[i-1]) > 0.9:
                repetitions += 1
        
        return repetitions / (len(texts) - 1) if len(texts) > 1 else 0.0
    
    def _calculate_fragmentation_rate(self, valid_segments: List[Dict]) -> float:
        """Calculate the rate of fragmented (incomplete) sentences."""
        if not valid_segments:
            return 0.0
        
        fragments = 0
        for data in valid_segments:
            text = data["segment"].text.strip()
            # Consider it fragmented if it's very short or doesn't end with punctuation
            if len(text) < 10 or not text[-1] in '.!?':
                fragments += 1
        
        return fragments / len(valid_segments)
    
    def _calculate_sentence_completeness(self, valid_segments: List[Dict]) -> float:
        """Calculate the rate of complete sentences in recent segments."""
        if not valid_segments:
            return 1.0
        
        complete_sentences = 0
        for data in valid_segments:
            text = data["segment"].text.strip()
            # Consider complete if it ends with punctuation and has reasonable length
            if len(text) >= 5 and text[-1] in '.!?':
                complete_sentences += 1
        
        return complete_sentences / len(valid_segments)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_overall_quality_score(self, metrics: QualityMetrics) -> float:
        """Calculate overall quality score based on multiple factors."""
        # Weighted combination of different quality factors
        confidence_weight = 0.3
        completion_weight = 0.25
        accuracy_weight = 0.25
        latency_weight = 0.2
        
        # Normalize confidence score (0.7 threshold = 0.5 score, 1.0 = 1.0 score)
        confidence_score = max(0.0, min(1.0, (metrics.avg_confidence - 0.5) / 0.5))
        
        # Completion rate is already 0-1
        completion_score = metrics.completion_rate
        
        # Accuracy score (inverse of problems)
        accuracy_score = 1.0 - (
            (metrics.repetition_rate * 0.4) + 
            (metrics.fragmentation_rate * 0.3) + 
            ((1.0 - metrics.sentence_completeness) * 0.3)
        )
        accuracy_score = max(0.0, min(1.0, accuracy_score))
        
        # Latency score (inverse of processing time, capped at 2 seconds)
        max_acceptable_latency = 2.0
        latency_score = max(0.0, 1.0 - (metrics.avg_processing_time / max_acceptable_latency))
        
        # Calculate weighted score
        overall_score = (
            confidence_score * confidence_weight +
            completion_score * completion_weight +
            accuracy_score * accuracy_weight +
            latency_score * latency_weight
        )
        
        return max(0.0, min(1.0, overall_score))
    
    def _determine_quality_trend(self) -> str:
        """Determine if quality is improving, degrading, or stable."""
        if len(self.quality_history) < 5:
            return "stable"
        
        recent_scores = [entry["quality_score"] for entry in list(self.quality_history)[-5:]]
        
        # Calculate trend using linear regression slope
        n = len(recent_scores)
        x_values = list(range(n))
        
        # Simple slope calculation
        x_mean = mean(x_values)
        y_mean = mean(recent_scores)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, recent_scores))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Classify trend based on slope
        if slope > 0.02:
            return "improving"
        elif slope < -0.02:
            return "degrading"
        else:
            return "stable"
    
    def _check_quality_alerts(self) -> None:
        """Check for quality issues and generate alerts."""
        current_time = time.time()
        metrics = self.current_metrics
        
        # Clear old alerts (older than 5 minutes)
        self.active_alerts = [
            alert for alert in self.active_alerts 
            if current_time - alert.timestamp < 300
        ]
        
        # Check confidence drop
        if len(self.quality_history) >= 10:
            recent_confidence = mean([entry["confidence"] for entry in list(self.quality_history)[-5:]])
            older_confidence = mean([entry["confidence"] for entry in list(self.quality_history)[-10:-5]])
            
            if older_confidence - recent_confidence > self.alert_thresholds["confidence_drop"]:
                self._create_alert(
                    "confidence_drop",
                    "medium",
                    f"Confidence dropped from {older_confidence:.2f} to {recent_confidence:.2f}",
                    {"old_confidence": older_confidence, "new_confidence": recent_confidence},
                    ["Check audio quality", "Verify microphone settings", "Review background noise"]
                )
        
        # Check latency spike
        if metrics.avg_processing_time > self.alert_thresholds["latency_spike"]:
            self._create_alert(
                "latency_spike",
                "high" if metrics.avg_processing_time > 3.0 else "medium",
                f"Processing time increased to {metrics.avg_processing_time:.2f}s",
                {"processing_time": metrics.avg_processing_time, "threshold": self.alert_thresholds["latency_spike"]},
                ["Check system resources", "Verify API connectivity", "Consider reducing audio quality"]
            )
        
        # Check completion rate drop
        if metrics.completion_rate < (1.0 - self.alert_thresholds["completion_rate_drop"]):
            self._create_alert(
                "completion_rate_drop",
                "high",
                f"Completion rate dropped to {metrics.completion_rate:.1%}",
                {"completion_rate": metrics.completion_rate, "filtered_segments": self.session_metrics.filtered_segments},
                ["Check confidence threshold", "Verify audio quality", "Review filtering settings"]
            )
        
        # Check overall quality degradation
        if metrics.overall_quality_score < 0.6:
            severity = "critical" if metrics.overall_quality_score < 0.4 else "high"
            self._create_alert(
                "quality_degradation",
                severity,
                f"Overall quality score dropped to {metrics.overall_quality_score:.2f}",
                {"quality_score": metrics.overall_quality_score, "trend": metrics.quality_trend},
                ["Review all quality metrics", "Check system performance", "Consider manual intervention"]
            )
    
    def _create_alert(
        self, 
        alert_type: str, 
        severity: str, 
        message: str, 
        metrics: Dict[str, Any],
        suggested_actions: List[str]
    ) -> None:
        """Create a new quality alert."""
        # Avoid duplicate alerts of the same type within 1 minute
        current_time = time.time()
        recent_alerts = [
            alert for alert in self.active_alerts 
            if alert.alert_type == alert_type and current_time - alert.timestamp < 60
        ]
        
        if recent_alerts:
            return
        
        alert = QualityAlert(
            timestamp=current_time,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metrics=metrics,
            suggested_actions=suggested_actions
        )
        
        self.active_alerts.append(alert)
        logger.warning(f"Quality alert: {alert_type} - {message}")
    
    def _apply_auto_adjustments(self) -> None:
        """Apply automatic quality adjustments based on current metrics."""
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self.last_adjustment_time < self.adjustment_cooldown:
            return
        
        metrics = self.current_metrics
        adjustments_made = []
        
        # Adjust confidence threshold based on completion rate
        if metrics.completion_rate < 0.7 and self.confidence_threshold > 0.5:
            old_threshold = self.confidence_threshold
            self.confidence_threshold = max(0.5, self.confidence_threshold - 0.05)
            adjustments_made.append({
                "type": "confidence_threshold",
                "old_value": old_threshold,
                "new_value": self.confidence_threshold,
                "reason": "Low completion rate"
            })
        elif metrics.completion_rate > 0.95 and metrics.avg_confidence > 0.85 and self.confidence_threshold < 0.8:
            old_threshold = self.confidence_threshold
            self.confidence_threshold = min(0.8, self.confidence_threshold + 0.02)
            adjustments_made.append({
                "type": "confidence_threshold",
                "old_value": old_threshold,
                "new_value": self.confidence_threshold,
                "reason": "High completion rate and confidence"
            })
        
        # Record adjustments
        if adjustments_made:
            self.adjustment_history.append({
                "timestamp": current_time,
                "adjustments": adjustments_made,
                "metrics_before": {
                    "completion_rate": metrics.completion_rate,
                    "avg_confidence": metrics.avg_confidence,
                    "quality_score": metrics.overall_quality_score
                }
            })
            self.last_adjustment_time = current_time
            
            logger.info(f"Auto-adjustments applied: {adjustments_made}")
    
    def get_current_metrics(self) -> QualityMetrics:
        """Get current quality metrics."""
        return self.current_metrics
    
    def get_session_metrics(self) -> QualityMetrics:
        """Get cumulative session metrics."""
        return self.session_metrics
    
    def get_active_alerts(self) -> List[QualityAlert]:
        """Get currently active quality alerts."""
        return self.active_alerts
    
    def get_quality_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get quality history for trend analysis."""
        history = list(self.quality_history)
        return history[-limit:] if limit > 0 else history
    
    def get_adjustment_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history of automatic adjustments."""
        return self.adjustment_history[-limit:] if limit > 0 else self.adjustment_history
    
    def validate_transcript_completeness(
        self, 
        segments: List[TranscriptSegment],
        expected_duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validate transcript completeness against expected criteria.
        
        Args:
            segments: List of transcript segments to validate
            expected_duration: Expected audio duration in seconds
            
        Returns:
            Validation results with completeness metrics
        """
        if not segments:
            return {
                "is_complete": False,
                "completeness_score": 0.0,
                "issues": ["No transcript segments found"],
                "recommendations": ["Check audio input", "Verify transcription service"]
            }
        
        issues = []
        recommendations = []
        
        # Check segment continuity
        time_gaps = []
        for i in range(1, len(segments)):
            gap = segments[i].start_time - segments[i-1].end_time
            if gap > 2.0:  # Gap larger than 2 seconds
                time_gaps.append(gap)
        
        if time_gaps:
            issues.append(f"Found {len(time_gaps)} time gaps > 2 seconds")
            recommendations.append("Check for audio dropouts or silence detection issues")
        
        # Check confidence distribution
        low_confidence_segments = [s for s in segments if s.confidence < 0.6]
        if len(low_confidence_segments) > len(segments) * 0.3:
            issues.append(f"{len(low_confidence_segments)} segments have low confidence")
            recommendations.append("Improve audio quality or adjust confidence threshold")
        
        # Check for very short segments (potential fragmentation)
        short_segments = [s for s in segments if len(s.text.split()) < 3]
        if len(short_segments) > len(segments) * 0.4:
            issues.append(f"{len(short_segments)} segments are very short")
            recommendations.append("Review buffering settings to reduce fragmentation")
        
        # Check duration coverage if expected duration provided
        coverage_score = 1.0
        if expected_duration and expected_duration > 0:
            total_transcript_duration = sum(s.duration for s in segments)
            coverage_score = min(1.0, total_transcript_duration / expected_duration)
            
            if coverage_score < 0.8:
                issues.append(f"Transcript covers only {coverage_score:.1%} of expected duration")
                recommendations.append("Check for audio processing issues or silence periods")
        
        # Calculate overall completeness score
        completeness_factors = [
            1.0 - (len(time_gaps) / max(1, len(segments) - 1)),  # Continuity
            1.0 - (len(low_confidence_segments) / len(segments)),  # Confidence
            1.0 - (len(short_segments) / len(segments)),  # Fragmentation
            coverage_score  # Duration coverage
        ]
        
        completeness_score = mean(completeness_factors)
        is_complete = completeness_score >= 0.8 and len(issues) == 0
        
        return {
            "is_complete": is_complete,
            "completeness_score": completeness_score,
            "total_segments": len(segments),
            "time_gaps": len(time_gaps),
            "low_confidence_segments": len(low_confidence_segments),
            "short_segments": len(short_segments),
            "coverage_score": coverage_score,
            "issues": issues,
            "recommendations": recommendations
        }
    
    def generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality report for the session."""
        current_time = time.time()
        
        return {
            "timestamp": current_time,
            "session_metrics": self.session_metrics.to_dict(),
            "current_metrics": self.current_metrics.to_dict(),
            "active_alerts": [alert.to_dict() for alert in self.active_alerts],
            "quality_history": self.get_quality_history(20),
            "adjustment_history": self.get_adjustment_history(5),
            "configuration": {
                "confidence_threshold": self.confidence_threshold,
                "quality_window_size": self.quality_window_size,
                "auto_adjustment_enabled": self.enable_auto_adjustment,
                "alert_thresholds": self.alert_thresholds
            },
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on current quality metrics."""
        recommendations = []
        metrics = self.current_metrics
        
        if metrics.avg_confidence < 0.7:
            recommendations.append("Consider improving audio quality or adjusting microphone settings")
        
        if metrics.completion_rate < 0.8:
            recommendations.append("Review confidence threshold settings to reduce filtering")
        
        if metrics.avg_processing_time > 1.5:
            recommendations.append("Check system performance and API connectivity")
        
        if metrics.repetition_rate > 0.2:
            recommendations.append("Review deduplication settings to reduce repetitive content")
        
        if metrics.fragmentation_rate > 0.3:
            recommendations.append("Adjust buffering settings to improve sentence completeness")
        
        if metrics.quality_trend == "degrading":
            recommendations.append("Monitor system resources and consider manual intervention")
        
        if not recommendations:
            recommendations.append("Quality metrics are within acceptable ranges")
        
        return recommendations
    
    def reset_session_metrics(self) -> None:
        """Reset session metrics for a new session."""
        self.session_metrics = QualityMetrics()
        self.current_metrics = QualityMetrics()
        self.recent_segments.clear()
        self.processing_times.clear()
        self.quality_history.clear()
        self.active_alerts.clear()
        self.adjustment_history.clear()
        self.last_adjustment_time = 0.0
        
        logger.info("Session metrics reset for new session")


# Factory function for creating quality monitor instances
def create_quality_monitor(
    confidence_threshold: float = 0.7,
    quality_window_size: int = 50,
    alert_thresholds: Optional[Dict[str, float]] = None,
    enable_auto_adjustment: bool = True
) -> TranscriptQualityMonitor:
    """
    Create a new TranscriptQualityMonitor instance with specified configuration.
    
    Args:
        confidence_threshold: Minimum confidence threshold for segments
        quality_window_size: Number of recent segments to consider for quality trends
        alert_thresholds: Custom thresholds for quality alerts
        enable_auto_adjustment: Whether to enable automatic quality adjustments
        
    Returns:
        Configured TranscriptQualityMonitor instance
    """
    return TranscriptQualityMonitor(
        confidence_threshold=confidence_threshold,
        quality_window_size=quality_window_size,
        alert_thresholds=alert_thresholds,
        enable_auto_adjustment=enable_auto_adjustment
    )