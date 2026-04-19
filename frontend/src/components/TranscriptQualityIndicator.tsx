/**
 * TranscriptQualityIndicator.tsx
 * 
 * React component for displaying real-time transcript quality indicators in the UI.
 * Shows quality metrics, alerts, and provides visual feedback about transcription performance.
 * 
 * Features:
 * - Real-time quality score display
 * - Confidence level indicators
 * - Active alerts with severity levels
 * - Quality trend visualization
 * - Expandable detailed metrics
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  AlertTriangle, 
  CheckCircle, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

// Types for quality data
interface QualityMetrics {
  confidence: {
    average: number;
    minimum: number;
    maximum: number;
    distribution: Record<string, number>;
  };
  completeness: {
    total_segments: number;
    filtered_segments: number;
    completion_rate: number;
  };
  accuracy: {
    repetition_rate: number;
    fragmentation_rate: number;
    sentence_completeness: number;
  };
  latency: {
    average_processing_time: number;
    max_processing_time: number;
    processing_count: number;
  };
  coverage: {
    audio_coverage: number;
    silence_detection_accuracy: number;
  };
  overall: {
    quality_score: number;
    quality_trend: 'improving' | 'degrading' | 'stable';
  };
}

interface QualityAlert {
  timestamp: number;
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  metrics: Record<string, any>;
  suggested_actions: string[];
}

interface TranscriptQualityIndicatorProps {
  /** Whether to show detailed metrics */
  showDetails?: boolean;
  /** Update interval in milliseconds */
  updateInterval?: number;
  /** Custom CSS classes */
  className?: string;
  /** Callback when quality changes significantly */
  onQualityChange?: (score: number, trend: string) => void;
}

const TranscriptQualityIndicator: React.FC<TranscriptQualityIndicatorProps> = ({
  showDetails = false,
  updateInterval = 5000,
  className = '',
  onQualityChange
}) => {
  const [metrics, setMetrics] = useState<QualityMetrics | null>(null);
  const [alerts, setAlerts] = useState<QualityAlert[]>([]);
  const [isExpanded, setIsExpanded] = useState(showDetails);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch quality metrics from API
  const fetchQualityData = async () => {
    try {
      const [metricsResponse, alertsResponse] = await Promise.all([
        fetch('/api/transcript-quality/metrics/current'),
        fetch('/api/transcript-quality/alerts')
      ]);

      if (metricsResponse.ok && alertsResponse.ok) {
        const metricsData = await metricsResponse.json();
        const alertsData = await alertsResponse.json();
        
        setMetrics(metricsData);
        setAlerts(alertsData);
        setError(null);
        
        // Notify parent of quality changes
        if (onQualityChange && metricsData.overall) {
          onQualityChange(metricsData.overall.quality_score, metricsData.overall.quality_trend);
        }
      } else {
        setError('Failed to fetch quality data');
      }
    } catch (err) {
      setError('Quality monitoring unavailable');
      console.warn('Quality monitoring error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Set up polling for real-time updates
  useEffect(() => {
    fetchQualityData();
    const interval = setInterval(fetchQualityData, updateInterval);
    return () => clearInterval(interval);
  }, [updateInterval]);

  // Get quality score color based on value
  const getQualityColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    if (score >= 0.4) return 'text-orange-600';
    return 'text-red-600';
  };

  // Get quality score background color
  const getQualityBgColor = (score: number): string => {
    if (score >= 0.8) return 'bg-green-100';
    if (score >= 0.6) return 'bg-yellow-100';
    if (score >= 0.4) return 'bg-orange-100';
    return 'bg-red-100';
  };

  // Get alert severity color
  const getAlertColor = (severity: string): string => {
    switch (severity) {
      case 'critical': return 'text-red-700 bg-red-100';
      case 'high': return 'text-red-600 bg-red-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-blue-600 bg-blue-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  // Get trend icon
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return <TrendingUp className="w-4 h-4 text-green-600" />;
      case 'degrading': return <TrendingDown className="w-4 h-4 text-red-600" />;
      default: return <Minus className="w-4 h-4 text-gray-600" />;
    }
  };

  // Format percentage
  const formatPercentage = (value: number): string => {
    return `${Math.round(value * 100)}%`;
  };

  // Format time
  const formatTime = (seconds: number): string => {
    return `${seconds.toFixed(2)}s`;
  };

  if (isLoading) {
    return (
      <div className={`flex items-center space-x-2 p-3 bg-gray-50 rounded-lg ${className}`}>
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
        <span className="text-sm text-gray-600">Loading quality metrics...</span>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className={`flex items-center space-x-2 p-3 bg-gray-50 rounded-lg ${className}`}>
        <Info className="w-4 h-4 text-gray-500" />
        <span className="text-sm text-gray-600">
          {error || 'Quality monitoring unavailable'}
        </span>
      </div>
    );
  }

  const qualityScore = metrics.overall.quality_score;
  const qualityTrend = metrics.overall.quality_trend;
  const hasAlerts = alerts.length > 0;
  const criticalAlerts = alerts.filter(a => a.severity === 'critical').length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-white border rounded-lg shadow-sm ${className}`}
    >
      {/* Main Quality Indicator */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {/* Quality Score */}
            <div className={`flex items-center space-x-2 px-3 py-1 rounded-full ${getQualityBgColor(qualityScore)}`}>
              <div className={`w-2 h-2 rounded-full ${qualityScore >= 0.8 ? 'bg-green-600' : qualityScore >= 0.6 ? 'bg-yellow-600' : 'bg-red-600'}`}></div>
              <span className={`text-sm font-medium ${getQualityColor(qualityScore)}`}>
                {formatPercentage(qualityScore)}
              </span>
            </div>

            {/* Trend Indicator */}
            <div className="flex items-center space-x-1">
              {getTrendIcon(qualityTrend)}
              <span className="text-xs text-gray-600 capitalize">{qualityTrend}</span>
            </div>

            {/* Alert Indicator */}
            {hasAlerts && (
              <div className="flex items-center space-x-1">
                <AlertTriangle className={`w-4 h-4 ${criticalAlerts > 0 ? 'text-red-600' : 'text-yellow-600'}`} />
                <span className="text-xs text-gray-600">
                  {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
                </span>
              </div>
            )}
          </div>

          {/* Expand/Collapse Button */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <span>Details</span>
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {/* Quick Stats */}
        <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Confidence</span>
            <div className="font-medium">{formatPercentage(metrics.confidence.average)}</div>
          </div>
          <div>
            <span className="text-gray-500">Completion</span>
            <div className="font-medium">{formatPercentage(metrics.completeness.completion_rate)}</div>
          </div>
          <div>
            <span className="text-gray-500">Latency</span>
            <div className="font-medium">{formatTime(metrics.latency.average_processing_time)}</div>
          </div>
        </div>
      </div>

      {/* Detailed Metrics */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t bg-gray-50"
          >
            <div className="p-4 space-y-4">
              {/* Active Alerts */}
              {hasAlerts && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Active Alerts</h4>
                  <div className="space-y-2">
                    {alerts.slice(0, 3).map((alert, index) => (
                      <div
                        key={index}
                        className={`p-2 rounded text-xs ${getAlertColor(alert.severity)}`}
                      >
                        <div className="font-medium capitalize">{alert.type.replace('_', ' ')}</div>
                        <div className="mt-1">{alert.message}</div>
                        {alert.suggested_actions.length > 0 && (
                          <div className="mt-1 text-xs opacity-75">
                            Suggestion: {alert.suggested_actions[0]}
                          </div>
                        )}
                      </div>
                    ))}
                    {alerts.length > 3 && (
                      <div className="text-xs text-gray-500">
                        +{alerts.length - 3} more alerts
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Detailed Metrics */}
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <h5 className="font-medium text-gray-700 mb-2">Confidence</h5>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Average:</span>
                      <span>{formatPercentage(metrics.confidence.average)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Range:</span>
                      <span>{formatPercentage(metrics.confidence.minimum)} - {formatPercentage(metrics.confidence.maximum)}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h5 className="font-medium text-gray-700 mb-2">Processing</h5>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Segments:</span>
                      <span>{metrics.completeness.total_segments}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Filtered:</span>
                      <span>{metrics.completeness.filtered_segments}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h5 className="font-medium text-gray-700 mb-2">Accuracy</h5>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Completeness:</span>
                      <span>{formatPercentage(metrics.accuracy.sentence_completeness)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Repetition:</span>
                      <span>{formatPercentage(metrics.accuracy.repetition_rate)}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h5 className="font-medium text-gray-700 mb-2">Performance</h5>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Avg Time:</span>
                      <span>{formatTime(metrics.latency.average_processing_time)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Max Time:</span>
                      <span>{formatTime(metrics.latency.max_processing_time)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default TranscriptQualityIndicator;