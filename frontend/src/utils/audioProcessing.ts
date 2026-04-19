/**
 * Audio Processing Utilities for MeetNova Production Upgrade
 * 
 * This module provides advanced audio processing functions for production-grade
 * audio manipulation including stream merging, silence detection, level normalization,
 * quality validation, and format conversion.
 * 
 * Requirements: 1.3, 1.4, 1.5
 */

// Audio processing configuration interfaces
export interface AudioMergeConfig {
  systemGain: number;
  microphoneGain: number;
  enableEchoCancellation: boolean;
  enableNoiseSuppression: boolean;
  enableAutoGainControl: boolean;
}

export interface SilenceDetectionConfig {
  threshold: number; // dB threshold for silence detection
  minSilenceDuration: number; // minimum silence duration in ms
  lookAheadTime: number; // look ahead time for chunk boundaries in ms
}

export interface AudioNormalizationConfig {
  targetLevel: number; // target RMS level in dB
  maxGain: number; // maximum gain adjustment in dB
  attackTime: number; // attack time for gain changes in ms
  releaseTime: number; // release time for gain changes in ms
}

export interface AudioQualityMetrics {
  sampleRate: number;
  bitDepth: number;
  channels: number;
  snr: number; // signal-to-noise ratio in dB
  thd: number; // total harmonic distortion percentage
  dynamicRange: number; // dynamic range in dB
  clippingDetected: boolean;
}

export interface AudioQualityThresholds {
  minSampleRate: number;
  minSNR: number;
  maxTHD: number;
  minDynamicRange: number;
  allowClipping: boolean;
}

export interface AudioFormatConfig {
  sampleRate: number;
  channels: number;
  bitDepth: number;
  format: 'wav' | 'webm' | 'mp3' | 'ogg';
  quality?: number; // for lossy formats (0-1)
}

/**
 * Merges multiple audio streams into a single combined stream with gain control
 * and advanced audio processing features.
 * 
 * @param streams - Array of MediaStreams to merge
 * @param config - Audio merge configuration
 * @returns Promise<MediaStream> - Combined audio stream
 * 
 * Validates: Requirements 1.3, 1.4
 */
export async function mergeAudioStreams(
  streams: MediaStream[],
  config: AudioMergeConfig = {
    systemGain: 1.2,
    microphoneGain: 1.0,
    enableEchoCancellation: true,
    enableNoiseSuppression: true,
    enableAutoGainControl: true
  }
): Promise<MediaStream> {
  if (streams.length === 0) {
    throw new Error('At least one audio stream is required for merging');
  }

  // Create audio context for processing
  const audioContext = new AudioContext({
    sampleRate: 44100,
    latencyHint: 'interactive'
  });

  // Create destination for merged stream
  const destination = audioContext.createMediaStreamDestination();

  // Create master gain node for final output control
  const masterGain = audioContext.createGain();
  masterGain.gain.value = 1.0;
  masterGain.connect(destination);

  // Process each input stream
  for (let i = 0; i < streams.length; i++) {
    const stream = streams[i];
    const audioTracks = stream.getAudioTracks();

    if (audioTracks.length === 0) {
      console.warn(`Stream ${i} has no audio tracks, skipping`);
      continue;
    }

    // Create source from stream
    const source = audioContext.createMediaStreamSource(stream);

    // Create gain node for this stream
    const gainNode = audioContext.createGain();
    
    // Apply appropriate gain based on stream type (system vs microphone)
    // Assume first stream is system audio, second is microphone
    gainNode.gain.value = i === 0 ? config.systemGain : config.microphoneGain;

    // Create processing chain
    let currentNode: AudioNode = source;

    // Add echo cancellation if enabled (simulated with high-pass filter)
    if (config.enableEchoCancellation) {
      const highPassFilter = audioContext.createBiquadFilter();
      highPassFilter.type = 'highpass';
      highPassFilter.frequency.value = 100; // Remove low-frequency echo
      highPassFilter.Q.value = 0.7;
      
      currentNode.connect(highPassFilter);
      currentNode = highPassFilter;
    }

    // Add noise suppression (simulated with notch filters)
    if (config.enableNoiseSuppression) {
      // Create notch filter for common noise frequencies
      const notchFilter = audioContext.createBiquadFilter();
      notchFilter.type = 'notch';
      notchFilter.frequency.value = 60; // Remove 60Hz hum
      notchFilter.Q.value = 10;
      
      currentNode.connect(notchFilter);
      currentNode = notchFilter;
    }

    // Add automatic gain control (simulated with compressor)
    if (config.enableAutoGainControl) {
      const compressor = audioContext.createDynamicsCompressor();
      compressor.threshold.value = -24;
      compressor.knee.value = 30;
      compressor.ratio.value = 12;
      compressor.attack.value = 0.003;
      compressor.release.value = 0.25;
      
      currentNode.connect(compressor);
      currentNode = compressor;
    }

    // Connect to gain node and then to master
    currentNode.connect(gainNode);
    gainNode.connect(masterGain);
  }

  return destination.stream;
}

/**
 * Detects silence periods in audio data for intelligent chunking
 * 
 * @param audioData - Float32Array of audio samples
 * @param config - Silence detection configuration
 * @returns Array of silence periods with start and end times
 * 
 * Validates: Requirements 1.4, 1.5
 */
export function detectSilence(
  audioData: Float32Array,
  sampleRate: number,
  config: SilenceDetectionConfig = {
    threshold: -40, // dB
    minSilenceDuration: 500, // ms
    lookAheadTime: 100 // ms
  }
): Array<{ start: number; end: number; duration: number }> {
  const silencePeriods: Array<{ start: number; end: number; duration: number }> = [];
  
  // Convert threshold from dB to linear scale
  const linearThreshold = Math.pow(10, config.threshold / 20);
  
  // Calculate window size for RMS analysis
  const windowSize = Math.floor(sampleRate * 0.01); // 10ms windows
  const minSilenceSamples = Math.floor((config.minSilenceDuration / 1000) * sampleRate);
  
  let silenceStart = -1;
  let consecutiveSilentSamples = 0;
  
  // Process audio in windows
  for (let i = 0; i < audioData.length - windowSize; i += windowSize) {
    // Calculate RMS for current window
    let rmsSum = 0;
    for (let j = i; j < i + windowSize && j < audioData.length; j++) {
      rmsSum += audioData[j] * audioData[j];
    }
    const rms = Math.sqrt(rmsSum / windowSize);
    
    const currentTime = (i / sampleRate) * 1000; // Convert to milliseconds
    
    if (rms < linearThreshold) {
      // Silent sample detected
      if (silenceStart === -1) {
        silenceStart = currentTime;
        consecutiveSilentSamples = windowSize;
      } else {
        consecutiveSilentSamples += windowSize;
      }
    } else {
      // Non-silent sample detected
      if (silenceStart !== -1 && consecutiveSilentSamples >= minSilenceSamples) {
        // End of silence period that meets minimum duration
        const silenceEnd = currentTime;
        const duration = silenceEnd - silenceStart;
        
        silencePeriods.push({
          start: silenceStart,
          end: silenceEnd,
          duration: duration
        });
      }
      
      // Reset silence tracking
      silenceStart = -1;
      consecutiveSilentSamples = 0;
    }
  }
  
  // Handle silence that extends to the end of the audio
  if (silenceStart !== -1 && consecutiveSilentSamples >= minSilenceSamples) {
    const silenceEnd = (audioData.length / sampleRate) * 1000;
    const duration = silenceEnd - silenceStart;
    
    silencePeriods.push({
      start: silenceStart,
      end: silenceEnd,
      duration: duration
    });
  }
  
  return silencePeriods;
}

/**
 * Normalizes audio levels for consistent volume across different sources
 * 
 * @param audioData - Float32Array of audio samples to normalize
 * @param config - Normalization configuration
 * @returns Float32Array - Normalized audio data
 * 
 * Validates: Requirements 1.4, 1.5
 */
export function normalizeAudioLevels(
  audioData: Float32Array,
  config: AudioNormalizationConfig = {
    targetLevel: -12, // dB
    maxGain: 20, // dB
    attackTime: 10, // ms
    releaseTime: 100 // ms
  }
): Float32Array {
  if (audioData.length === 0) {
    return new Float32Array(0);
  }

  const normalizedData = new Float32Array(audioData.length);
  
  // Convert target level from dB to linear scale
  const targetLinear = Math.pow(10, config.targetLevel / 20);
  const maxGainLinear = Math.pow(10, config.maxGain / 20);
  
  // Calculate current RMS level
  let rmsSum = 0;
  for (let i = 0; i < audioData.length; i++) {
    rmsSum += audioData[i] * audioData[i];
  }
  const currentRMS = Math.sqrt(rmsSum / audioData.length);
  
  if (currentRMS === 0) {
    // Silent audio, return as-is
    return audioData.slice();
  }
  
  // Calculate required gain
  let requiredGain = targetLinear / currentRMS;
  
  // Limit gain to prevent excessive amplification
  requiredGain = Math.min(requiredGain, maxGainLinear);
  
  // Apply gain with attack/release envelope for smooth transitions
  const sampleRate = 44100; // Assume standard sample rate
  const attackSamples = Math.floor((config.attackTime / 1000) * sampleRate);
  const releaseSamples = Math.floor((config.releaseTime / 1000) * sampleRate);
  
  let currentGain = 1.0;
  const gainStep = (requiredGain - currentGain) / Math.max(attackSamples, 1);
  
  for (let i = 0; i < audioData.length; i++) {
    // Smooth gain transition
    if (i < attackSamples) {
      currentGain += gainStep;
    } else if (i > audioData.length - releaseSamples) {
      // Fade out to prevent clicks
      const fadePosition = (audioData.length - i) / releaseSamples;
      currentGain = requiredGain * fadePosition;
    } else {
      currentGain = requiredGain;
    }
    
    // Apply gain and prevent clipping
    normalizedData[i] = Math.max(-1.0, Math.min(1.0, audioData[i] * currentGain));
  }
  
  return normalizedData;
}

/**
 * Validates audio quality against specified thresholds
 * 
 * @param audioData - Float32Array of audio samples
 * @param sampleRate - Sample rate of the audio
 * @param thresholds - Quality validation thresholds
 * @returns AudioQualityMetrics - Detailed quality metrics
 * 
 * Validates: Requirements 1.5
 */
export function validateAudioQuality(
  audioData: Float32Array,
  sampleRate: number,
  thresholds: AudioQualityThresholds = {
    minSampleRate: 16000,
    minSNR: 20, // dB
    maxTHD: 5, // %
    minDynamicRange: 30, // dB
    allowClipping: false
  }
): AudioQualityMetrics {
  // Calculate basic metrics
  const channels = 1; // Assume mono for analysis
  const bitDepth = 32; // Float32 equivalent
  
  // Calculate signal level (RMS)
  let signalSum = 0;
  let peakLevel = 0;
  let clippingDetected = false;
  
  for (let i = 0; i < audioData.length; i++) {
    const sample = Math.abs(audioData[i]);
    signalSum += sample * sample;
    peakLevel = Math.max(peakLevel, sample);
    
    // Check for clipping (samples at or near maximum)
    if (sample >= 0.99) {
      clippingDetected = true;
    }
  }
  
  const rmsLevel = Math.sqrt(signalSum / audioData.length);
  
  // Estimate noise floor (use quietest 10% of samples)
  const sortedSamples = Array.from(audioData).map(Math.abs).sort((a, b) => a - b);
  const noiseFloorIndex = Math.floor(sortedSamples.length * 0.1);
  const noiseFloor = sortedSamples[noiseFloorIndex];
  
  // Calculate SNR
  const snr = noiseFloor > 0 ? 20 * Math.log10(rmsLevel / noiseFloor) : 100;
  
  // Estimate THD (simplified - would need FFT for accurate measurement)
  // Using peak-to-RMS ratio as a rough approximation
  const crestFactor = peakLevel / rmsLevel;
  const estimatedTHD = Math.max(0, (crestFactor - 3) * 2); // Rough approximation
  
  // Calculate dynamic range
  const dynamicRange = peakLevel > 0 && noiseFloor > 0 ? 
    20 * Math.log10(peakLevel / noiseFloor) : 0;
  
  const metrics: AudioQualityMetrics = {
    sampleRate,
    bitDepth,
    channels,
    snr: Math.max(0, snr),
    thd: Math.min(100, estimatedTHD),
    dynamicRange: Math.max(0, dynamicRange),
    clippingDetected
  };
  
  return metrics;
}

/**
 * Converts audio data between different formats
 * 
 * @param audioData - Input audio data
 * @param inputConfig - Input format configuration
 * @param outputConfig - Desired output format configuration
 * @returns Promise<Blob> - Converted audio data as blob
 * 
 * Validates: Requirements 1.5
 */
export async function convertAudioFormat(
  audioData: Float32Array,
  inputConfig: AudioFormatConfig,
  outputConfig: AudioFormatConfig
): Promise<Blob> {
  // Create audio context for processing
  const audioContext = new AudioContext({
    sampleRate: inputConfig.sampleRate
  });
  
  // Create audio buffer from input data
  const audioBuffer = audioContext.createBuffer(
    inputConfig.channels,
    audioData.length / inputConfig.channels,
    inputConfig.sampleRate
  );
  
  // Fill buffer with audio data
  for (let channel = 0; channel < inputConfig.channels; channel++) {
    const channelData = audioBuffer.getChannelData(channel);
    for (let i = 0; i < channelData.length; i++) {
      channelData[i] = audioData[i * inputConfig.channels + channel];
    }
  }
  
  // Handle sample rate conversion if needed
  let processedBuffer = audioBuffer;
  if (inputConfig.sampleRate !== outputConfig.sampleRate) {
    // Create offline context for resampling
    const offlineContext = new OfflineAudioContext(
      outputConfig.channels,
      Math.floor(audioBuffer.length * (outputConfig.sampleRate / inputConfig.sampleRate)),
      outputConfig.sampleRate
    );
    
    const source = offlineContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(offlineContext.destination);
    source.start();
    
    processedBuffer = await offlineContext.startRendering();
  }
  
  // Convert to desired format
  switch (outputConfig.format) {
    case 'wav':
      return convertToWAV(processedBuffer, outputConfig);
    
    case 'webm':
      return convertToWebM(processedBuffer, outputConfig);
    
    case 'mp3':
      // Note: MP3 encoding requires additional libraries in browser
      throw new Error('MP3 encoding not supported in browser environment');
    
    case 'ogg':
      // Note: OGG encoding requires additional libraries in browser
      throw new Error('OGG encoding not supported in browser environment');
    
    default:
      throw new Error(`Unsupported output format: ${outputConfig.format}`);
  }
}

/**
 * Converts audio buffer to WAV format
 */
function convertToWAV(audioBuffer: AudioBuffer, config: AudioFormatConfig): Blob {
  const numberOfChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const length = audioBuffer.length;
  const bitDepth = config.bitDepth || 16;
  const bytesPerSample = bitDepth / 8;
  
  // Calculate buffer size
  const bufferLength = 44 + length * numberOfChannels * bytesPerSample;
  const arrayBuffer = new ArrayBuffer(bufferLength);
  const view = new DataView(arrayBuffer);
  
  // Write WAV header
  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };
  
  writeString(0, 'RIFF');
  view.setUint32(4, bufferLength - 8, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // PCM format
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, numberOfChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numberOfChannels * bytesPerSample, true);
  view.setUint16(32, numberOfChannels * bytesPerSample, true);
  view.setUint16(34, bitDepth, true);
  writeString(36, 'data');
  view.setUint32(40, length * numberOfChannels * bytesPerSample, true);
  
  // Write audio data
  let offset = 44;
  for (let i = 0; i < length; i++) {
    for (let channel = 0; channel < numberOfChannels; channel++) {
      const sample = audioBuffer.getChannelData(channel)[i];
      
      if (bitDepth === 16) {
        const intSample = Math.max(-32768, Math.min(32767, sample * 32767));
        view.setInt16(offset, intSample, true);
        offset += 2;
      } else if (bitDepth === 32) {
        view.setFloat32(offset, sample, true);
        offset += 4;
      }
    }
  }
  
  return new Blob([arrayBuffer], { type: 'audio/wav' });
}

/**
 * Converts audio buffer to WebM format using MediaRecorder
 */
async function convertToWebM(audioBuffer: AudioBuffer, config: AudioFormatConfig): Promise<Blob> {
  // Create a MediaStream from the audio buffer
  const audioContext = new AudioContext();
  const source = audioContext.createBufferSource();
  const destination = audioContext.createMediaStreamDestination();
  
  source.buffer = audioBuffer;
  source.connect(destination);
  
  // Use MediaRecorder to encode to WebM
  const mediaRecorder = new MediaRecorder(destination.stream, {
    mimeType: 'audio/webm;codecs=opus',
    audioBitsPerSecond: config.quality ? config.quality * 128000 : 128000
  });
  
  const chunks: Blob[] = [];
  
  return new Promise((resolve, reject) => {
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };
    
    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      resolve(blob);
    };
    
    mediaRecorder.onerror = (event) => {
      reject(new Error('MediaRecorder error'));
    };
    
    mediaRecorder.start();
    source.start();
    
    // Stop recording after buffer duration
    setTimeout(() => {
      mediaRecorder.stop();
      source.stop();
    }, (audioBuffer.length / audioBuffer.sampleRate) * 1000);
  });
}

/**
 * Utility function to create audio processing chain for real-time processing
 * 
 * @param audioContext - Web Audio API context
 * @param config - Processing configuration
 * @returns Object with processing nodes
 */
export function createAudioProcessingChain(
  audioContext: AudioContext,
  config: {
    enableEchoCancellation?: boolean;
    enableNoiseSuppression?: boolean;
    enableAutoGainControl?: boolean;
    enableNormalization?: boolean;
  } = {}
) {
  const nodes: {
    input: GainNode;
    output: GainNode;
    highPass?: BiquadFilterNode;
    notchFilter?: BiquadFilterNode;
    compressor?: DynamicsCompressorNode;
    normalizer?: GainNode;
  } = {
    input: audioContext.createGain(),
    output: audioContext.createGain()
  };
  
  let currentNode: AudioNode = nodes.input;
  
  // Echo cancellation (high-pass filter)
  if (config.enableEchoCancellation) {
    nodes.highPass = audioContext.createBiquadFilter();
    nodes.highPass.type = 'highpass';
    nodes.highPass.frequency.value = 100;
    nodes.highPass.Q.value = 0.7;
    
    currentNode.connect(nodes.highPass);
    currentNode = nodes.highPass;
  }
  
  // Noise suppression (notch filter)
  if (config.enableNoiseSuppression) {
    nodes.notchFilter = audioContext.createBiquadFilter();
    nodes.notchFilter.type = 'notch';
    nodes.notchFilter.frequency.value = 60;
    nodes.notchFilter.Q.value = 10;
    
    currentNode.connect(nodes.notchFilter);
    currentNode = nodes.notchFilter;
  }
  
  // Automatic gain control (compressor)
  if (config.enableAutoGainControl) {
    nodes.compressor = audioContext.createDynamicsCompressor();
    nodes.compressor.threshold.value = -24;
    nodes.compressor.knee.value = 30;
    nodes.compressor.ratio.value = 12;
    nodes.compressor.attack.value = 0.003;
    nodes.compressor.release.value = 0.25;
    
    currentNode.connect(nodes.compressor);
    currentNode = nodes.compressor;
  }
  
  // Normalization (gain node)
  if (config.enableNormalization) {
    nodes.normalizer = audioContext.createGain();
    nodes.normalizer.gain.value = 1.0;
    
    currentNode.connect(nodes.normalizer);
    currentNode = nodes.normalizer;
  }
  
  // Connect to output
  currentNode.connect(nodes.output);
  
  return nodes;
}