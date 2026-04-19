/**
 * AudioCaptureService - Production-grade audio capture service for MeetNova
 * 
 * This service provides comprehensive audio capture capabilities including:
 * - System audio capture from Google Meet tabs
 * - Microphone audio capture with advanced processing
 * - Real-time audio level monitoring
 * - Device change detection and recovery
 * - Browser compatibility validation
 * - Enhanced error handling and recovery
 * 
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
 */

// ── Core Interfaces ──

export interface AudioCaptureConfig {
  sampleRate: number;
  channels: number;
  chunkSize: number;
  format: 'webm' | 'wav' | 'mp3';
  echoCancellation: boolean;
  noiseSuppression: boolean;
  autoGainControl: boolean;
  systemAudioGain: number;
  microphoneGain: number;
}

export interface AudioChunk {
  id: string;
  data: Blob;
  timestamp: number;
  duration: number;
  speakerTag?: string;
  confidence?: number;
  audioLevels?: {
    systemAudio: number;
    microphone: number;
    mixed: number;
  };
}

export interface AudioLevels {
  systemAudio: number;
  microphone: number;
  mixed: number;
  timestamp: number;
}

export interface AudioDeviceInfo {
  deviceId: string;
  label: string;
  kind: MediaDeviceKind;
  groupId: string;
}

export interface AudioProcessingState {
  isCapturing: boolean;
  hasSystemAudio: boolean;
  hasMicrophone: boolean;
  deviceChangeDetected: boolean;
  audioLevels: AudioLevels;
  lastError?: string;
}

export interface AudioSupportInfo {
  isSupported: boolean;
  hasGetDisplayMedia: boolean;
  hasGetUserMedia: boolean;
  hasAudioContext: boolean;
  hasMediaRecorder: boolean;
  supportedFormats: string[];
  issues: string[];
}

export interface AudioCaptureResult {
  mixedStream: MediaStream;
  displayStream: MediaStream;
  micStream: MediaStream;
  audioContext: AudioContext;
  hasSystemAudio: boolean;
  hasMicrophone: boolean;
}

// ── Event Types ──

export type AudioCaptureEventType = 
  | 'stateChange'
  | 'audioLevels'
  | 'deviceChange'
  | 'error'
  | 'chunk'
  | 'qualityChange';

export interface AudioCaptureEvent {
  type: AudioCaptureEventType;
  data: any;
  timestamp: number;
}

export type AudioCaptureEventListener = (event: AudioCaptureEvent) => void;

// ── Error Classes ──

export class AudioCaptureError extends Error {
  constructor(
    message: string,
    public code: string,
    public recoverable: boolean = true
  ) {
    super(message);
    this.name = 'AudioCaptureError';
  }
}

export class AudioDeviceError extends AudioCaptureError {
  constructor(message: string, public deviceType: 'microphone' | 'system') {
    super(message, 'DEVICE_ERROR', true);
    this.name = 'AudioDeviceError';
  }
}

export class AudioCompatibilityError extends AudioCaptureError {
  constructor(message: string, public missingFeatures: string[]) {
    super(message, 'COMPATIBILITY_ERROR', false);
    this.name = 'AudioCompatibilityError';
  }
}

// ── Main Service Class ──

export class AudioCaptureService {
  private config: AudioCaptureConfig;
  private state: AudioProcessingState;
  private eventListeners: Map<AudioCaptureEventType, Set<AudioCaptureEventListener>>;
  
  // Audio processing components
  private audioContext: AudioContext | null = null;
  private systemAudioAnalyser: AnalyserNode | null = null;
  private microphoneAnalyser: AnalyserNode | null = null;
  private mixedAnalyser: AnalyserNode | null = null;
  private audioLevelMonitor: ReturnType<typeof setInterval> | null = null;
  private deviceChangeListener: (() => void) | null = null;
  
  // Stream references
  private displayStream: MediaStream | null = null;
  private micStream: MediaStream | null = null;
  private mixedStream: MediaStream | null = null;
  
  // Device management
  private availableDevices: AudioDeviceInfo[] = [];
  private selectedMicrophoneId: string = 'default';
  
  // Quality monitoring
  private qualityMetrics = {
    droppedChunks: 0,
    averageLatency: 0,
    lastQualityCheck: 0,
  };

  constructor(config?: Partial<AudioCaptureConfig>) {
    this.config = {
      sampleRate: 44100,
      channels: 2,
      chunkSize: 4096,
      format: 'webm',
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      systemAudioGain: 1.2,
      microphoneGain: 1.0,
      ...config
    };

    this.state = {
      isCapturing: false,
      hasSystemAudio: false,
      hasMicrophone: false,
      deviceChangeDetected: false,
      audioLevels: { systemAudio: 0, microphone: 0, mixed: 0, timestamp: 0 }
    };

    this.eventListeners = new Map();
    
    // Initialize device change monitoring
    this.initializeDeviceChangeMonitoring();
  }

  // ── Public API Methods ──

  /**
   * Validates browser audio support and compatibility
   * Requirements: 1.6 - Browser compatibility checking
   */
  public validateAudioSupport(): AudioSupportInfo {
    const issues: string[] = [];
    const supportedFormats: string[] = [];

    // Check core APIs
    const hasGetDisplayMedia = !!(navigator.mediaDevices?.getDisplayMedia);
    const hasGetUserMedia = !!(navigator.mediaDevices?.getUserMedia);
    const hasAudioContext = !!(window.AudioContext || (window as any).webkitAudioContext);
    const hasMediaRecorder = !!window.MediaRecorder;

    if (!hasGetDisplayMedia) issues.push('getDisplayMedia not supported');
    if (!hasGetUserMedia) issues.push('getUserMedia not supported');
    if (!hasAudioContext) issues.push('AudioContext not supported');
    if (!hasMediaRecorder) issues.push('MediaRecorder not supported');

    // Check supported formats
    if (hasMediaRecorder) {
      const formats = ['audio/webm', 'audio/wav', 'audio/mp3', 'audio/ogg'];
      formats.forEach(format => {
        if (MediaRecorder.isTypeSupported(format)) {
          supportedFormats.push(format.split('/')[1]);
        }
      });
    }

    const isSupported = hasGetDisplayMedia && hasGetUserMedia && hasAudioContext && hasMediaRecorder;

    return {
      isSupported,
      hasGetDisplayMedia,
      hasGetUserMedia,
      hasAudioContext,
      hasMediaRecorder,
      supportedFormats,
      issues
    };
  }

  /**
   * Captures system and microphone audio with enhanced processing
   * Requirements: 1.1, 1.2, 1.3, 1.4, 1.5 - Enhanced audio capture
   */
  public async captureSystemAndMicAudio(): Promise<AudioCaptureResult> {
    console.log('[AudioCaptureService] Starting enhanced audio capture with config:', this.config);
    
    // Validate browser support
    const support = this.validateAudioSupport();
    if (!support.isSupported) {
      throw new AudioCompatibilityError(
        `Browser audio support incomplete: ${support.issues.join(', ')}`,
        support.issues
      );
    }

    try {
      // Initialize audio context
      await this.initializeAudioContext();
      
      // Capture system audio (Google Meet tab)
      const displayStream = await this.captureSystemAudio();
      
      // Capture microphone audio
      const micStream = await this.captureMicrophoneAudio();
      
      // Create mixed audio stream
      const mixedStream = await this.createMixedAudioStream(displayStream, micStream);
      
      // Update state
      this.updateState({
        isCapturing: true,
        hasSystemAudio: displayStream.getAudioTracks().length > 0,
        hasMicrophone: micStream.getAudioTracks().length > 0,
        deviceChangeDetected: false,
        lastError: undefined
      });
      
      // Start monitoring
      this.startAudioLevelMonitoring();
      
      // Store stream references
      this.displayStream = displayStream;
      this.micStream = micStream;
      this.mixedStream = mixedStream;
      
      const result: AudioCaptureResult = {
        mixedStream,
        displayStream,
        micStream,
        audioContext: this.audioContext!,
        hasSystemAudio: this.state.hasSystemAudio,
        hasMicrophone: this.state.hasMicrophone
      };
      
      this.emitEvent('stateChange', this.state);
      
      console.log('[AudioCaptureService] Audio capture setup complete', {
        hasSystemAudio: result.hasSystemAudio,
        hasMicrophone: result.hasMicrophone,
        sampleRate: this.audioContext?.sampleRate,
        channels: this.config.channels
      });
      
      return result;
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown audio capture error';
      this.updateState({
        isCapturing: false,
        lastError: errorMessage
      });
      
      this.emitEvent('error', { error, message: errorMessage });
      
      if (error instanceof AudioCaptureError) {
        throw error;
      } else {
        throw new AudioCaptureError(errorMessage, 'CAPTURE_FAILED');
      }
    }
  }

  /**
   * Gets real-time audio levels for monitoring
   * Requirements: 1.4 - Real-time audio monitoring
   */
  public getAudioLevels(): AudioLevels {
    if (!this.state.isCapturing) {
      return { systemAudio: 0, microphone: 0, mixed: 0, timestamp: Date.now() };
    }

    const levels: AudioLevels = {
      systemAudio: this.getAnalyserLevel(this.systemAudioAnalyser),
      microphone: this.getAnalyserLevel(this.microphoneAnalyser),
      mixed: this.getAnalyserLevel(this.mixedAnalyser),
      timestamp: Date.now()
    };

    return levels;
  }

  /**
   * Handles audio device changes and recovery
   * Requirements: 1.6 - Device management and recovery
   */
  public async handleDeviceChange(): Promise<void> {
    console.log('[AudioCaptureService] Handling device change...');
    
    try {
      // Refresh available devices
      await this.refreshAvailableDevices();
      
      // Check if current device is still available
      const currentDevice = this.availableDevices.find(
        device => device.deviceId === this.selectedMicrophoneId
      );
      
      if (!currentDevice && this.selectedMicrophoneId !== 'default') {
        console.log('[AudioCaptureService] Current device no longer available, switching to default');
        this.selectedMicrophoneId = 'default';
      }
      
      // Update state
      this.updateState({ deviceChangeDetected: true });
      
      // Emit device change event
      this.emitEvent('deviceChange', {
        availableDevices: this.availableDevices,
        selectedDeviceId: this.selectedMicrophoneId,
        deviceLost: !currentDevice
      });
      
    } catch (error) {
      console.error('[AudioCaptureService] Device change handling failed:', error);
      this.emitEvent('error', { error, message: 'Device change handling failed' });
    }
  }

  /**
   * Stops audio capture and cleans up resources
   */
  public async stopCapture(): Promise<void> {
    console.log('[AudioCaptureService] Stopping audio capture...');
    
    try {
      // Stop monitoring
      this.stopAudioLevelMonitoring();
      
      // Stop streams
      if (this.displayStream) {
        this.displayStream.getTracks().forEach(track => track.stop());
        this.displayStream = null;
      }
      
      if (this.micStream) {
        this.micStream.getTracks().forEach(track => track.stop());
        this.micStream = null;
      }
      
      if (this.mixedStream) {
        this.mixedStream.getTracks().forEach(track => track.stop());
        this.mixedStream = null;
      }
      
      // Close audio context
      if (this.audioContext && this.audioContext.state !== 'closed') {
        await this.audioContext.close();
        this.audioContext = null;
      }
      
      // Reset analysers
      this.systemAudioAnalyser = null;
      this.microphoneAnalyser = null;
      this.mixedAnalyser = null;
      
      // Update state
      this.updateState({
        isCapturing: false,
        hasSystemAudio: false,
        hasMicrophone: false,
        audioLevels: { systemAudio: 0, microphone: 0, mixed: 0, timestamp: Date.now() }
      });
      
      this.emitEvent('stateChange', this.state);
      
    } catch (error) {
      console.error('[AudioCaptureService] Error stopping capture:', error);
      this.emitEvent('error', { error, message: 'Failed to stop capture cleanly' });
    }
  }

  // ── Configuration and Device Management ──

  public updateConfig(updates: Partial<AudioCaptureConfig>): void {
    this.config = { ...this.config, ...updates };
    console.log('[AudioCaptureService] Config updated:', updates);
  }

  public getConfig(): AudioCaptureConfig {
    return { ...this.config };
  }

  public getState(): AudioProcessingState {
    return { ...this.state };
  }

  public async getAvailableDevices(): Promise<AudioDeviceInfo[]> {
    await this.refreshAvailableDevices();
    return [...this.availableDevices];
  }

  public setSelectedMicrophone(deviceId: string): void {
    this.selectedMicrophoneId = deviceId;
    console.log('[AudioCaptureService] Selected microphone changed:', deviceId);
  }

  public getSelectedMicrophone(): string {
    return this.selectedMicrophoneId;
  }

  // ── Event Management ──

  public addEventListener(type: AudioCaptureEventType, listener: AudioCaptureEventListener): void {
    if (!this.eventListeners.has(type)) {
      this.eventListeners.set(type, new Set());
    }
    this.eventListeners.get(type)!.add(listener);
  }

  public removeEventListener(type: AudioCaptureEventType, listener: AudioCaptureEventListener): void {
    const listeners = this.eventListeners.get(type);
    if (listeners) {
      listeners.delete(listener);
    }
  }

  public removeAllEventListeners(): void {
    this.eventListeners.clear();
  }

  // ── Quality Monitoring ──

  public getQualityMetrics() {
    return { ...this.qualityMetrics };
  }

  // ── Cleanup ──

  public async dispose(): Promise<void> {
    console.log('[AudioCaptureService] Disposing service...');
    
    await this.stopCapture();
    
    // Remove device change listener
    if (this.deviceChangeListener) {
      this.deviceChangeListener();
      this.deviceChangeListener = null;
    }
    
    // Clear all event listeners
    this.removeAllEventListeners();
  }

  // ── Private Implementation Methods ──

  private async initializeAudioContext(): Promise<void> {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    
    if (this.audioContext && this.audioContext.state !== 'closed') {
      await this.audioContext.close();
    }
    
    this.audioContext = new AudioContextClass({ sampleRate: this.config.sampleRate });
    await this.audioContext.resume();
  }

  private async captureSystemAudio(): Promise<MediaStream> {
    try {
      console.log('[AudioCaptureService] Requesting display media with audio...');
      
      const displayStream = await navigator.mediaDevices.getDisplayMedia({
        audio: {
          echoCancellation: this.config.echoCancellation,
          noiseSuppression: this.config.noiseSuppression,
          autoGainControl: this.config.autoGainControl,
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels
        },
        video: true
      });
      
      return displayStream;
      
    } catch (error) {
      if (error instanceof Error && error.name === 'NotAllowedError') {
        throw new AudioDeviceError('System audio permission denied', 'system');
      }
      throw new AudioDeviceError('Failed to capture system audio', 'system');
    }
  }

  private async captureMicrophoneAudio(): Promise<MediaStream> {
    try {
      console.log('[AudioCaptureService] Requesting microphone access...');
      
      const micConstraints: MediaStreamConstraints = {
        audio: {
          deviceId: this.selectedMicrophoneId !== 'default' 
            ? { exact: this.selectedMicrophoneId } 
            : undefined,
          echoCancellation: this.config.echoCancellation,
          noiseSuppression: this.config.noiseSuppression,
          autoGainControl: this.config.autoGainControl,
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels
        }
      };
      
      const micStream = await navigator.mediaDevices.getUserMedia(micConstraints);
      
      return micStream;
      
    } catch (error) {
      if (error instanceof Error && error.name === 'NotAllowedError') {
        throw new AudioDeviceError('Microphone permission denied', 'microphone');
      }
      throw new AudioDeviceError('Failed to capture microphone audio', 'microphone');
    }
  }

  private async createMixedAudioStream(
    displayStream: MediaStream, 
    micStream: MediaStream
  ): Promise<MediaStream> {
    if (!this.audioContext) {
      throw new AudioCaptureError('Audio context not initialized', 'CONTEXT_ERROR');
    }

    // Create destination for mixed audio
    const destination = this.audioContext.createMediaStreamDestination();

    // Process system audio
    const displayAudioTracks = displayStream.getAudioTracks();
    if (displayAudioTracks.length > 0) {
      console.log('[AudioCaptureService] Setting up system audio processing...');
      
      const displaySource = this.audioContext.createMediaStreamSource(
        new MediaStream(displayAudioTracks)
      );
      
      // Create analyser for system audio level monitoring
      this.systemAudioAnalyser = this.audioContext.createAnalyser();
      this.systemAudioAnalyser.fftSize = 256;
      this.systemAudioAnalyser.smoothingTimeConstant = 0.8;
      
      // Create gain control for system audio
      const displayGain = this.audioContext.createGain();
      displayGain.gain.value = this.config.systemAudioGain;
      
      // Create compressor for dynamic range control
      const systemCompressor = this.audioContext.createDynamicsCompressor();
      systemCompressor.threshold.value = -24;
      systemCompressor.knee.value = 30;
      systemCompressor.ratio.value = 12;
      systemCompressor.attack.value = 0.003;
      systemCompressor.release.value = 0.25;
      
      // Connect system audio chain
      displaySource.connect(this.systemAudioAnalyser);
      this.systemAudioAnalyser.connect(displayGain);
      displayGain.connect(systemCompressor);
      systemCompressor.connect(destination);
    }

    // Process microphone audio
    const micAudioTracks = micStream.getAudioTracks();
    if (micAudioTracks.length > 0) {
      console.log('[AudioCaptureService] Setting up microphone audio processing...');
      
      const micSource = this.audioContext.createMediaStreamSource(
        new MediaStream(micAudioTracks)
      );
      
      // Create analyser for microphone level monitoring
      this.microphoneAnalyser = this.audioContext.createAnalyser();
      this.microphoneAnalyser.fftSize = 256;
      this.microphoneAnalyser.smoothingTimeConstant = 0.8;
      
      // Create gain control for microphone
      const micGain = this.audioContext.createGain();
      micGain.gain.value = this.config.microphoneGain;
      
      // Create high-pass filter to remove low-frequency noise
      const highPassFilter = this.audioContext.createBiquadFilter();
      highPassFilter.type = 'highpass';
      highPassFilter.frequency.value = 80; // Remove frequencies below 80Hz
      highPassFilter.Q.value = 0.7;
      
      // Create compressor for microphone
      const micCompressor = this.audioContext.createDynamicsCompressor();
      micCompressor.threshold.value = -18;
      micCompressor.knee.value = 20;
      micCompressor.ratio.value = 8;
      micCompressor.attack.value = 0.003;
      micCompressor.release.value = 0.1;
      
      // Connect microphone audio chain
      micSource.connect(this.microphoneAnalyser);
      this.microphoneAnalyser.connect(highPassFilter);
      highPassFilter.connect(micGain);
      micGain.connect(micCompressor);
      micCompressor.connect(destination);
    }

    // Set up mixed audio analyser for final output monitoring
    this.mixedAnalyser = this.audioContext.createAnalyser();
    this.mixedAnalyser.fftSize = 256;
    this.mixedAnalyser.smoothingTimeConstant = 0.8;
    
    // Connect mixed analyser to monitor final output
    destination.connect(this.mixedAnalyser);

    return destination.stream;
  }

  private getAnalyserLevel(analyser: AnalyserNode | null): number {
    if (!analyser) return 0;
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);
    
    // Calculate RMS level
    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
      sum += dataArray[i] * dataArray[i];
    }
    const rms = Math.sqrt(sum / bufferLength);
    
    // Convert to percentage (0-100)
    return Math.min(100, Math.round((rms / 255) * 100));
  }

  private startAudioLevelMonitoring(): void {
    if (this.audioLevelMonitor) {
      clearInterval(this.audioLevelMonitor);
    }
    
    this.audioLevelMonitor = setInterval(() => {
      const levels = this.getAudioLevels();
      this.updateState({ audioLevels: levels });
      this.emitEvent('audioLevels', levels);
    }, 100); // Update every 100ms
  }

  private stopAudioLevelMonitoring(): void {
    if (this.audioLevelMonitor) {
      clearInterval(this.audioLevelMonitor);
      this.audioLevelMonitor = null;
    }
  }

  private async refreshAvailableDevices(): Promise<void> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      this.availableDevices = devices
        .filter(device => device.kind === 'audioinput')
        .map(device => ({
          deviceId: device.deviceId,
          label: device.label || `Microphone ${device.deviceId.slice(0, 8)}`,
          kind: device.kind,
          groupId: device.groupId
        }));
    } catch (error) {
      console.error('[AudioCaptureService] Failed to enumerate devices:', error);
      this.availableDevices = [];
    }
  }

  private initializeDeviceChangeMonitoring(): void {
    if (!navigator.mediaDevices?.addEventListener) return;
    
    const handleDeviceChange = () => {
      console.log('[AudioCaptureService] Device change detected');
      this.handleDeviceChange();
    };
    
    navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange);
    
    this.deviceChangeListener = () => {
      navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange);
    };
  }

  private updateState(updates: Partial<AudioProcessingState>): void {
    this.state = { ...this.state, ...updates };
  }

  private emitEvent(type: AudioCaptureEventType, data: any): void {
    const event: AudioCaptureEvent = {
      type,
      data,
      timestamp: Date.now()
    };
    
    const listeners = this.eventListeners.get(type);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(event);
        } catch (error) {
          console.error(`[AudioCaptureService] Event listener error for ${type}:`, error);
        }
      });
    }
  }
}

// ── Utility Functions ──

/**
 * Creates a default AudioCaptureService instance with production settings
 */
export function createAudioCaptureService(config?: Partial<AudioCaptureConfig>): AudioCaptureService {
  return new AudioCaptureService(config);
}

/**
 * Validates if the current browser supports all required audio features
 */
export function validateBrowserAudioSupport(): AudioSupportInfo {
  const service = new AudioCaptureService();
  return service.validateAudioSupport();
}

/**
 * Creates an AudioChunk with metadata
 */
export function createAudioChunk(
  data: Blob,
  options: {
    speakerTag?: string;
    audioLevels?: { systemAudio: number; microphone: number; mixed: number };
  } = {}
): AudioChunk {
  return {
    id: `chunk_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    data,
    timestamp: Date.now(),
    duration: 0, // Will be calculated based on audio data
    speakerTag: options.speakerTag,
    audioLevels: options.audioLevels
  };
}