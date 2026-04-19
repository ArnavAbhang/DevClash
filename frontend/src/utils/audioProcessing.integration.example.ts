/**
 * Integration example showing how audio processing utilities can enhance
 * the existing AudioCaptureService
 * 
 * This file demonstrates how to use the new audio processing utilities
 * with the existing audio capture infrastructure.
 */

import { AudioCaptureService } from '../services/audioCaptureService';
import {
  mergeAudioStreams,
  detectSilence,
  normalizeAudioLevels,
  validateAudioQuality,
  createAudioProcessingChain,
  type AudioMergeConfig,
  type SilenceDetectionConfig,
  type AudioNormalizationConfig,
  type AudioQualityThresholds
} from './audioProcessing';

/**
 * Enhanced audio capture service that uses the new audio processing utilities
 */
export class EnhancedAudioCaptureService extends AudioCaptureService {
  private silenceDetectionConfig: SilenceDetectionConfig = {
    threshold: -40,
    minSilenceDuration: 500,
    lookAheadTime: 100
  };

  private normalizationConfig: AudioNormalizationConfig = {
    targetLevel: -12,
    maxGain: 20,
    attackTime: 10,
    releaseTime: 100
  };

  private qualityThresholds: AudioQualityThresholds = {
    minSampleRate: 16000,
    minSNR: 20,
    maxTHD: 5,
    minDynamicRange: 30,
    allowClipping: false
  };

  /**
   * Enhanced audio capture with advanced processing
   */
  public async captureWithAdvancedProcessing(): Promise<{
    stream: MediaStream;
    qualityMetrics: any;
    processingChain: any;
  }> {
    // Use the existing capture method
    const captureResult = await this.captureSystemAndMicAudio();
    
    // Create advanced processing chain
    const audioContext = new AudioContext({
      sampleRate: 44100,
      latencyHint: 'interactive'
    });

    const processingChain = createAudioProcessingChain(audioContext, {
      enableEchoCancellation: true,
      enableNoiseSuppression: true,
      enableAutoGainControl: true,
      enableNormalization: true
    });

    // For demonstration, we'll simulate quality validation
    // In a real implementation, you'd extract audio data from the stream
    const sampleAudioData = new Float32Array(1024);
    for (let i = 0; i < sampleAudioData.length; i++) {
      sampleAudioData[i] = Math.sin(2 * Math.PI * 440 * i / 44100) * 0.5;
    }

    const qualityMetrics = validateAudioQuality(
      sampleAudioData,
      44100,
      this.qualityThresholds
    );

    return {
      stream: captureResult.combinedStream,
      qualityMetrics,
      processingChain
    };
  }

  /**
   * Process audio chunk with silence detection and normalization
   */
  public processAudioChunk(audioData: Float32Array, sampleRate: number): {
    normalizedData: Float32Array;
    silencePeriods: Array<{ start: number; end: number; duration: number }>;
    qualityMetrics: any;
  } {
    // Detect silence periods for intelligent chunking
    const silencePeriods = detectSilence(
      audioData,
      sampleRate,
      this.silenceDetectionConfig
    );

    // Normalize audio levels for consistent volume
    const normalizedData = normalizeAudioLevels(
      audioData,
      this.normalizationConfig
    );

    // Validate audio quality
    const qualityMetrics = validateAudioQuality(
      normalizedData,
      sampleRate,
      this.qualityThresholds
    );

    return {
      normalizedData,
      silencePeriods,
      qualityMetrics
    };
  }

  /**
   * Enhanced stream merging with custom configuration
   */
  public async mergeStreamsWithAdvancedConfig(
    streams: MediaStream[],
    config?: Partial<AudioMergeConfig>
  ): Promise<MediaStream> {
    const mergeConfig: AudioMergeConfig = {
      systemGain: 1.2,
      microphoneGain: 1.0,
      enableEchoCancellation: true,
      enableNoiseSuppression: true,
      enableAutoGainControl: true,
      ...config
    };

    return mergeAudioStreams(streams, mergeConfig);
  }

  /**
   * Real-time quality monitoring
   */
  public startQualityMonitoring(
    stream: MediaStream,
    callback: (metrics: any) => void
  ): void {
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    
    analyser.fftSize = 2048;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Float32Array(bufferLength);

    const monitor = () => {
      analyser.getFloatFrequencyData(dataArray);
      
      // Convert frequency data to time domain for quality analysis
      const timeData = new Float32Array(bufferLength);
      analyser.getFloatTimeDomainData(timeData);
      
      const qualityMetrics = validateAudioQuality(
        timeData,
        audioContext.sampleRate,
        this.qualityThresholds
      );

      callback(qualityMetrics);
      
      requestAnimationFrame(monitor);
    };

    monitor();
  }

  /**
   * Intelligent audio chunking based on silence detection
   */
  public createIntelligentChunks(
    audioData: Float32Array,
    sampleRate: number,
    maxChunkDuration: number = 30000 // 30 seconds in ms
  ): Array<{
    data: Float32Array;
    startTime: number;
    endTime: number;
    hasSilence: boolean;
  }> {
    const silencePeriods = detectSilence(
      audioData,
      sampleRate,
      this.silenceDetectionConfig
    );

    const chunks: Array<{
      data: Float32Array;
      startTime: number;
      endTime: number;
      hasSilence: boolean;
    }> = [];

    let currentStart = 0;
    const samplesPerMs = sampleRate / 1000;
    const maxChunkSamples = maxChunkDuration * samplesPerMs;

    for (const silencePeriod of silencePeriods) {
      const silenceStartSample = Math.floor(silencePeriod.start * samplesPerMs);
      const silenceEndSample = Math.floor(silencePeriod.end * samplesPerMs);

      // Create chunk before silence if it's long enough
      if (silenceStartSample - currentStart > samplesPerMs * 1000) { // At least 1 second
        const chunkEnd = Math.min(silenceStartSample, currentStart + maxChunkSamples);
        
        chunks.push({
          data: audioData.slice(currentStart, chunkEnd),
          startTime: currentStart / samplesPerMs,
          endTime: chunkEnd / samplesPerMs,
          hasSilence: false
        });

        currentStart = chunkEnd;
      }

      // Skip the silence period
      currentStart = Math.max(currentStart, silenceEndSample);
    }

    // Add final chunk if there's remaining audio
    if (currentStart < audioData.length) {
      chunks.push({
        data: audioData.slice(currentStart),
        startTime: currentStart / samplesPerMs,
        endTime: audioData.length / samplesPerMs,
        hasSilence: silencePeriods.some(period => 
          period.start >= currentStart / samplesPerMs
        )
      });
    }

    return chunks;
  }
}

/**
 * Factory function to create enhanced audio capture service
 */
export function createEnhancedAudioCaptureService(config?: any): EnhancedAudioCaptureService {
  return new EnhancedAudioCaptureService(config);
}

/**
 * Utility function to analyze audio stream quality in real-time
 */
export async function analyzeStreamQuality(
  stream: MediaStream,
  duration: number = 5000 // 5 seconds
): Promise<{
  averageQuality: any;
  qualityHistory: any[];
  recommendations: string[];
}> {
  return new Promise((resolve) => {
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    
    analyser.fftSize = 2048;
    source.connect(analyser);

    const qualityHistory: any[] = [];
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Float32Array(bufferLength);

    const startTime = Date.now();
    
    const analyze = () => {
      analyser.getFloatTimeDomainData(dataArray);
      
      const qualityMetrics = validateAudioQuality(
        dataArray,
        audioContext.sampleRate
      );

      qualityHistory.push({
        timestamp: Date.now() - startTime,
        ...qualityMetrics
      });

      if (Date.now() - startTime < duration) {
        setTimeout(analyze, 100); // Analyze every 100ms
      } else {
        // Calculate average quality
        const averageQuality = {
          sampleRate: qualityHistory[0]?.sampleRate || 0,
          bitDepth: qualityHistory[0]?.bitDepth || 0,
          channels: qualityHistory[0]?.channels || 0,
          snr: qualityHistory.reduce((sum, q) => sum + q.snr, 0) / qualityHistory.length,
          thd: qualityHistory.reduce((sum, q) => sum + q.thd, 0) / qualityHistory.length,
          dynamicRange: qualityHistory.reduce((sum, q) => sum + q.dynamicRange, 0) / qualityHistory.length,
          clippingDetected: qualityHistory.some(q => q.clippingDetected)
        };

        // Generate recommendations
        const recommendations: string[] = [];
        if (averageQuality.snr < 20) {
          recommendations.push('Consider reducing background noise or increasing microphone gain');
        }
        if (averageQuality.thd > 5) {
          recommendations.push('Audio distortion detected - check input levels');
        }
        if (averageQuality.clippingDetected) {
          recommendations.push('Audio clipping detected - reduce input gain');
        }
        if (averageQuality.dynamicRange < 30) {
          recommendations.push('Low dynamic range - consider adjusting compression settings');
        }

        resolve({
          averageQuality,
          qualityHistory,
          recommendations
        });
      }
    };

    analyze();
  });
}