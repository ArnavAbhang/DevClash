/**
 * Example usage of AudioCaptureService
 * This demonstrates how to integrate the AudioCaptureService into a React component
 */

import { AudioCaptureService, AudioCaptureEvent, AudioLevels } from './audioCaptureService';

// Example: Basic usage in a React component
export class AudioCaptureExample {
  private audioService: AudioCaptureService;
  private isRecording = false;

  constructor() {
    // Initialize with production-grade configuration
    this.audioService = new AudioCaptureService({
      sampleRate: 44100,
      channels: 2,
      chunkSize: 4096,
      format: 'webm',
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      systemAudioGain: 1.2,
      microphoneGain: 1.0
    });

    // Set up event listeners
    this.setupEventListeners();
  }

  private setupEventListeners() {
    // Listen for state changes
    this.audioService.addEventListener('stateChange', (event: AudioCaptureEvent) => {
      console.log('Audio capture state changed:', event.data);
      this.handleStateChange(event.data);
    });

    // Listen for audio level updates
    this.audioService.addEventListener('audioLevels', (event: AudioCaptureEvent) => {
      const levels: AudioLevels = event.data;
      this.updateAudioLevelUI(levels);
    });

    // Listen for device changes
    this.audioService.addEventListener('deviceChange', (event: AudioCaptureEvent) => {
      console.log('Audio device changed:', event.data);
      this.handleDeviceChange(event.data);
    });

    // Listen for errors
    this.audioService.addEventListener('error', (event: AudioCaptureEvent) => {
      console.error('Audio capture error:', event.data);
      this.handleError(event.data);
    });
  }

  // Start audio capture
  public async startCapture(): Promise<void> {
    try {
      // Validate browser support first
      const support = this.audioService.validateAudioSupport();
      if (!support.isSupported) {
        throw new Error(`Browser not supported: ${support.issues.join(', ')}`);
      }

      console.log('Starting audio capture...');
      const result = await this.audioService.captureSystemAndMicAudio();
      
      console.log('Audio capture started successfully:', {
        hasSystemAudio: result.hasSystemAudio,
        hasMicrophone: result.hasMicrophone,
        sampleRate: result.audioContext.sampleRate
      });

      this.isRecording = true;

      // You can now use result.mixedStream for recording or processing
      this.processAudioStream(result.mixedStream);

    } catch (error) {
      console.error('Failed to start audio capture:', error);
      throw error;
    }
  }

  // Stop audio capture
  public async stopCapture(): Promise<void> {
    try {
      console.log('Stopping audio capture...');
      await this.audioService.stopCapture();
      this.isRecording = false;
      console.log('Audio capture stopped successfully');
    } catch (error) {
      console.error('Failed to stop audio capture:', error);
      throw error;
    }
  }

  // Get current audio levels
  public getAudioLevels(): AudioLevels {
    return this.audioService.getAudioLevels();
  }

  // Get available audio devices
  public async getAvailableDevices() {
    return await this.audioService.getAvailableDevices();
  }

  // Select microphone device
  public selectMicrophone(deviceId: string): void {
    this.audioService.setSelectedMicrophone(deviceId);
  }

  // Update audio configuration
  public updateConfig(updates: any): void {
    this.audioService.updateConfig(updates);
  }

  // Clean up resources
  public async dispose(): Promise<void> {
    await this.audioService.dispose();
  }

  // Private methods for handling events and UI updates

  private handleStateChange(state: any): void {
    // Update UI based on state changes
    console.log('State changed:', {
      isCapturing: state.isCapturing,
      hasSystemAudio: state.hasSystemAudio,
      hasMicrophone: state.hasMicrophone,
      deviceChangeDetected: state.deviceChangeDetected
    });

    // Example: Update recording button state
    this.updateRecordingButton(state.isCapturing);
    
    // Example: Show device status indicators
    this.updateDeviceIndicators(state.hasSystemAudio, state.hasMicrophone);
  }

  private updateAudioLevelUI(levels: AudioLevels): void {
    // Update audio level meters in the UI
    console.log('Audio levels:', {
      systemAudio: levels.systemAudio,
      microphone: levels.microphone,
      mixed: levels.mixed
    });

    // Example: Update progress bars or visual indicators
    this.updateAudioMeter('system', levels.systemAudio);
    this.updateAudioMeter('microphone', levels.microphone);
    this.updateAudioMeter('mixed', levels.mixed);
  }

  private handleDeviceChange(data: any): void {
    console.log('Device change detected:', data);
    
    // Example: Show notification to user
    if (data.deviceLost) {
      this.showNotification('Audio device disconnected. Switched to default device.');
    }

    // Example: Update device selection UI
    this.updateDeviceList(data.availableDevices);
  }

  private handleError(error: any): void {
    console.error('Audio capture error:', error);
    
    // Example: Show user-friendly error message
    let userMessage = 'Audio capture error occurred.';
    
    if (error.error?.name === 'NotAllowedError') {
      userMessage = 'Please allow microphone and screen sharing permissions.';
    } else if (error.error?.code === 'COMPATIBILITY_ERROR') {
      userMessage = 'Your browser does not support audio capture features.';
    }
    
    this.showErrorMessage(userMessage);
  }

  private processAudioStream(stream: MediaStream): void {
    // Example: Set up MediaRecorder for recording
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'audio/webm;codecs=opus'
    });

    const audioChunks: Blob[] = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
        
        // Example: Send chunk for real-time transcription
        this.processAudioChunk(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      // Example: Create final audio file
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      this.handleRecordingComplete(audioBlob);
    };

    // Start recording in chunks for real-time processing
    mediaRecorder.start(1000); // 1 second chunks
  }

  private processAudioChunk(chunk: Blob): void {
    // Example: Send chunk to transcription service
    console.log('Processing audio chunk:', chunk.size, 'bytes');
    
    // This is where you would integrate with your transcription API
    // For example, sending to the backend for Groq Whisper processing
  }

  // UI update methods (these would be implemented based on your UI framework)

  private updateRecordingButton(isRecording: boolean): void {
    console.log('Update recording button:', isRecording ? 'Stop' : 'Start');
  }

  private updateDeviceIndicators(hasSystemAudio: boolean, hasMicrophone: boolean): void {
    console.log('Update device indicators:', { hasSystemAudio, hasMicrophone });
  }

  private updateAudioMeter(type: string, level: number): void {
    console.log(`Update ${type} audio meter:`, level + '%');
  }

  private updateDeviceList(devices: any[]): void {
    console.log('Update device list:', devices.length, 'devices');
  }

  private showNotification(message: string): void {
    console.log('Notification:', message);
  }

  private showErrorMessage(message: string): void {
    console.error('Error message:', message);
  }

  private handleRecordingComplete(audioBlob: Blob): void {
    console.log('Recording complete:', audioBlob.size, 'bytes');
  }
}

// Example: React Hook for using AudioCaptureService
export function useAudioCapture() {
  const [audioService] = useState(() => new AudioCaptureService());
  const [isCapturing, setIsCapturing] = useState(false);
  const [audioLevels, setAudioLevels] = useState<AudioLevels>({
    systemAudio: 0,
    microphone: 0,
    mixed: 0,
    timestamp: 0
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Set up event listeners
    const handleStateChange = (event: AudioCaptureEvent) => {
      setIsCapturing(event.data.isCapturing);
    };

    const handleAudioLevels = (event: AudioCaptureEvent) => {
      setAudioLevels(event.data);
    };

    const handleError = (event: AudioCaptureEvent) => {
      setError(event.data.message);
    };

    audioService.addEventListener('stateChange', handleStateChange);
    audioService.addEventListener('audioLevels', handleAudioLevels);
    audioService.addEventListener('error', handleError);

    // Cleanup
    return () => {
      audioService.removeEventListener('stateChange', handleStateChange);
      audioService.removeEventListener('audioLevels', handleAudioLevels);
      audioService.removeEventListener('error', handleError);
    };
  }, [audioService]);

  const startCapture = useCallback(async () => {
    try {
      setError(null);
      await audioService.captureSystemAndMicAudio();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [audioService]);

  const stopCapture = useCallback(async () => {
    try {
      await audioService.stopCapture();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [audioService]);

  const getCurrentLevels = useCallback(() => {
    return audioService.getAudioLevels();
  }, [audioService]);

  return {
    audioService,
    isCapturing,
    audioLevels,
    error,
    startCapture,
    stopCapture,
    getCurrentLevels
  };
}

// Required imports for the React hook example
import { useState, useEffect, useCallback } from 'react';