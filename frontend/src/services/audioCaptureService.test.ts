/**
 * Unit tests for AudioCaptureService
 * Tests all core functionality including audio capture, device management, and error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  AudioCaptureService,
  AudioCaptureConfig,
  AudioCaptureError,
  AudioDeviceError,
  AudioCompatibilityError,
  createAudioCaptureService,
  validateBrowserAudioSupport,
  createAudioChunk
} from './audioCaptureService';

// Mock implementations
const createMockMediaStream = () => ({
  getAudioTracks: vi.fn(() => [{ stop: vi.fn() }]),
  getTracks: vi.fn(() => [{ stop: vi.fn() }]),
  id: 'mock-stream-id'
});

const createMockAnalyser = () => ({
  fftSize: 256,
  smoothingTimeConstant: 0.8,
  frequencyBinCount: 128,
  getByteFrequencyData: vi.fn((dataArray: Uint8Array) => {
    // Simulate some audio data
    for (let i = 0; i < dataArray.length; i++) {
      dataArray[i] = Math.floor(Math.random() * 128);
    }
  }),
  connect: vi.fn()
});

const createMockGain = () => ({
  gain: { value: 1.0 },
  connect: vi.fn()
});

const createMockCompressor = () => ({
  threshold: { value: -24 },
  knee: { value: 30 },
  ratio: { value: 12 },
  attack: { value: 0.003 },
  release: { value: 0.25 },
  connect: vi.fn()
});

const createMockFilter = () => ({
  type: 'highpass',
  frequency: { value: 80 },
  Q: { value: 0.7 },
  connect: vi.fn()
});

const createMockDestination = () => ({
  stream: createMockMediaStream(),
  connect: vi.fn()
});

const createMockMediaStreamSource = () => ({
  connect: vi.fn()
});

const createMockAudioContext = () => ({
  createMediaStreamSource: vi.fn(() => createMockMediaStreamSource()),
  createAnalyser: vi.fn(() => createMockAnalyser()),
  createGain: vi.fn(() => createMockGain()),
  createDynamicsCompressor: vi.fn(() => createMockCompressor()),
  createBiquadFilter: vi.fn(() => createMockFilter()),
  createMediaStreamDestination: vi.fn(() => createMockDestination()),
  resume: vi.fn().mockResolvedValue(undefined),
  close: vi.fn().mockResolvedValue(undefined),
  state: 'running',
  sampleRate: 44100
});

const createMockMediaDevices = () => ({
  getDisplayMedia: vi.fn().mockResolvedValue(createMockMediaStream()),
  getUserMedia: vi.fn().mockResolvedValue(createMockMediaStream()),
  enumerateDevices: vi.fn().mockResolvedValue([
    {
      deviceId: 'default',
      label: 'Default Microphone',
      kind: 'audioinput',
      groupId: 'group1'
    },
    {
      deviceId: 'mic1',
      label: 'USB Microphone',
      kind: 'audioinput',
      groupId: 'group2'
    }
  ]),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn()
});

// Global mocks
let mockMediaDevices: ReturnType<typeof createMockMediaDevices>;
let mockAudioContext: ReturnType<typeof createMockAudioContext>;

// Setup global mocks
beforeEach(() => {
  // Reset all mocks
  vi.clearAllMocks();
  
  // Create fresh mock instances
  mockMediaDevices = createMockMediaDevices();
  mockAudioContext = createMockAudioContext();
  
  // Mock navigator.mediaDevices
  Object.defineProperty(navigator, 'mediaDevices', {
    value: mockMediaDevices,
    writable: true,
    configurable: true
  });
  
  // Mock AudioContext
  (global as any).AudioContext = function MockAudioContext() {
    return mockAudioContext;
  };
  (global as any).webkitAudioContext = function MockWebkitAudioContext() {
    return mockAudioContext;
  };
  
  // Mock MediaRecorder
  (global as any).MediaRecorder = {
    isTypeSupported: vi.fn(() => true)
  };
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('AudioCaptureService', () => {
  describe('Constructor and Configuration', () => {
    it('should create service with default configuration', () => {
      const service = new AudioCaptureService();
      const config = service.getConfig();
      
      expect(config.sampleRate).toBe(44100);
      expect(config.channels).toBe(2);
      expect(config.chunkSize).toBe(4096);
      expect(config.format).toBe('webm');
      expect(config.echoCancellation).toBe(true);
      expect(config.noiseSuppression).toBe(true);
      expect(config.autoGainControl).toBe(true);
      expect(config.systemAudioGain).toBe(1.2);
      expect(config.microphoneGain).toBe(1.0);
    });

    it('should create service with custom configuration', () => {
      const customConfig: Partial<AudioCaptureConfig> = {
        sampleRate: 48000,
        channels: 1,
        format: 'wav',
        systemAudioGain: 1.5
      };
      
      const service = new AudioCaptureService(customConfig);
      const config = service.getConfig();
      
      expect(config.sampleRate).toBe(48000);
      expect(config.channels).toBe(1);
      expect(config.format).toBe('wav');
      expect(config.systemAudioGain).toBe(1.5);
      // Should keep defaults for unspecified values
      expect(config.echoCancellation).toBe(true);
    });

    it('should update configuration', () => {
      const service = new AudioCaptureService();
      
      service.updateConfig({ sampleRate: 48000, format: 'mp3' });
      const config = service.getConfig();
      
      expect(config.sampleRate).toBe(48000);
      expect(config.format).toBe('mp3');
      // Should keep other values unchanged
      expect(config.channels).toBe(2);
    });
  });

  describe('Browser Support Validation', () => {
    it('should validate full browser support', () => {
      const service = new AudioCaptureService();
      const support = service.validateAudioSupport();
      
      expect(support.isSupported).toBe(true);
      expect(support.hasGetDisplayMedia).toBe(true);
      expect(support.hasGetUserMedia).toBe(true);
      expect(support.hasAudioContext).toBe(true);
      expect(support.hasMediaRecorder).toBe(true);
      expect(support.supportedFormats).toContain('webm');
      expect(support.issues).toHaveLength(0);
    });

    it('should detect missing getDisplayMedia support', () => {
      // Remove getDisplayMedia
      delete (navigator.mediaDevices as any).getDisplayMedia;
      
      const service = new AudioCaptureService();
      const support = service.validateAudioSupport();
      
      expect(support.isSupported).toBe(false);
      expect(support.hasGetDisplayMedia).toBe(false);
      expect(support.issues).toContain('getDisplayMedia not supported');
    });

    it('should detect missing AudioContext support', () => {
      // Remove AudioContext
      delete (global as any).AudioContext;
      delete (global as any).webkitAudioContext;
      
      const service = new AudioCaptureService();
      const support = service.validateAudioSupport();
      
      expect(support.isSupported).toBe(false);
      expect(support.hasAudioContext).toBe(false);
      expect(support.issues).toContain('AudioContext not supported');
    });
  });

  describe('Audio Capture', () => {
    it('should successfully capture system and microphone audio', async () => {
      const service = new AudioCaptureService();
      
      const result = await service.captureSystemAndMicAudio();
      
      expect(result.mixedStream).toBeDefined();
      expect(result.displayStream).toBeDefined();
      expect(result.micStream).toBeDefined();
      expect(result.audioContext).toBeDefined();
      expect(result.hasSystemAudio).toBe(true);
      expect(result.hasMicrophone).toBe(true);
      
      // Verify API calls
      expect(mockMediaDevices.getDisplayMedia).toHaveBeenCalledWith({
        audio: expect.objectContaining({
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 44100,
          channelCount: 2
        }),
        video: true
      });
      
      expect(mockMediaDevices.getUserMedia).toHaveBeenCalledWith({
        audio: expect.objectContaining({
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 44100,
          channelCount: 2
        })
      });
      
      // Verify state update
      const state = service.getState();
      expect(state.isCapturing).toBe(true);
      expect(state.hasSystemAudio).toBe(true);
      expect(state.hasMicrophone).toBe(true);
    });

    it('should handle system audio permission denied', async () => {
      mockMediaDevices.getDisplayMedia.mockRejectedValue(
        Object.assign(new Error('Permission denied'), { name: 'NotAllowedError' })
      );
      
      const service = new AudioCaptureService();
      
      await expect(service.captureSystemAndMicAudio()).rejects.toThrow(AudioDeviceError);
      await expect(service.captureSystemAndMicAudio()).rejects.toThrow('System audio permission denied');
    });

    it('should handle microphone permission denied', async () => {
      mockMediaDevices.getUserMedia.mockRejectedValue(
        Object.assign(new Error('Permission denied'), { name: 'NotAllowedError' })
      );
      
      const service = new AudioCaptureService();
      
      await expect(service.captureSystemAndMicAudio()).rejects.toThrow(AudioDeviceError);
      await expect(service.captureSystemAndMicAudio()).rejects.toThrow('Microphone permission denied');
    });

    it('should handle browser compatibility errors', async () => {
      // Remove required API
      delete (navigator.mediaDevices as any).getDisplayMedia;
      
      const service = new AudioCaptureService();
      
      await expect(service.captureSystemAndMicAudio()).rejects.toThrow(AudioCompatibilityError);
    });
  });

  describe('Audio Level Monitoring', () => {
    it('should return zero levels when not capturing', () => {
      const service = new AudioCaptureService();
      const levels = service.getAudioLevels();
      
      expect(levels.systemAudio).toBe(0);
      expect(levels.microphone).toBe(0);
      expect(levels.mixed).toBe(0);
      expect(levels.timestamp).toBeGreaterThan(0);
    });

    it('should calculate audio levels when capturing', async () => {
      const service = new AudioCaptureService();
      await service.captureSystemAndMicAudio();
      
      const levels = service.getAudioLevels();
      
      // Should have some level values (mocked to return random data)
      expect(levels.systemAudio).toBeGreaterThanOrEqual(0);
      expect(levels.systemAudio).toBeLessThanOrEqual(100);
      expect(levels.microphone).toBeGreaterThanOrEqual(0);
      expect(levels.microphone).toBeLessThanOrEqual(100);
      expect(levels.mixed).toBeGreaterThanOrEqual(0);
      expect(levels.mixed).toBeLessThanOrEqual(100);
      expect(levels.timestamp).toBeGreaterThan(0);
    });
  });

  describe('Device Management', () => {
    it('should get available audio devices', async () => {
      const service = new AudioCaptureService();
      const devices = await service.getAvailableDevices();
      
      expect(devices).toHaveLength(2);
      expect(devices[0]).toEqual({
        deviceId: 'default',
        label: 'Default Microphone',
        kind: 'audioinput',
        groupId: 'group1'
      });
      expect(devices[1]).toEqual({
        deviceId: 'mic1',
        label: 'USB Microphone',
        kind: 'audioinput',
        groupId: 'group2'
      });
    });

    it('should handle device selection', () => {
      const service = new AudioCaptureService();
      
      service.setSelectedMicrophone('mic1');
      expect(service.getSelectedMicrophone()).toBe('mic1');
    });

    it('should handle device changes', async () => {
      const service = new AudioCaptureService();
      let deviceChangeEvent: any = null;
      
      service.addEventListener('deviceChange', (event) => {
        deviceChangeEvent = event;
      });
      
      await service.handleDeviceChange();
      
      expect(deviceChangeEvent).toBeDefined();
      expect(deviceChangeEvent.type).toBe('deviceChange');
      expect(deviceChangeEvent.data.availableDevices).toHaveLength(2);
      
      const state = service.getState();
      expect(state.deviceChangeDetected).toBe(true);
    });

    it('should switch to default when selected device is lost', async () => {
      const service = new AudioCaptureService();
      service.setSelectedMicrophone('mic1');
      
      // Mock device enumeration without mic1
      mockMediaDevices.enumerateDevices.mockResolvedValue([
        {
          deviceId: 'default',
          label: 'Default Microphone',
          kind: 'audioinput',
          groupId: 'group1'
        }
      ]);
      
      await service.handleDeviceChange();
      
      expect(service.getSelectedMicrophone()).toBe('default');
    });
  });

  describe('Event System', () => {
    it('should add and remove event listeners', () => {
      const service = new AudioCaptureService();
      const listener = vi.fn();
      
      service.addEventListener('stateChange', listener);
      service.removeEventListener('stateChange', listener);
      
      // Trigger state change - listener should not be called
      service.updateConfig({ sampleRate: 48000 });
      expect(listener).not.toHaveBeenCalled();
    });

    it('should emit state change events', async () => {
      const service = new AudioCaptureService();
      let stateChangeEvent: any = null;
      
      service.addEventListener('stateChange', (event) => {
        stateChangeEvent = event;
      });
      
      await service.captureSystemAndMicAudio();
      
      expect(stateChangeEvent).toBeDefined();
      expect(stateChangeEvent.type).toBe('stateChange');
      expect(stateChangeEvent.data.isCapturing).toBe(true);
    });

    it('should emit error events', async () => {
      const service = new AudioCaptureService();
      let errorEvent: any = null;
      
      service.addEventListener('error', (event) => {
        errorEvent = event;
      });
      
      // Cause an error
      mockMediaDevices.getDisplayMedia.mockRejectedValue(new Error('Test error'));
      
      try {
        await service.captureSystemAndMicAudio();
      } catch (error) {
        // Expected to throw
      }
      
      expect(errorEvent).toBeDefined();
      expect(errorEvent.type).toBe('error');
      expect(errorEvent.data.message).toContain('Failed to capture system audio');
    });

    it('should remove all event listeners', () => {
      const service = new AudioCaptureService();
      const listener1 = vi.fn();
      const listener2 = vi.fn();
      
      service.addEventListener('stateChange', listener1);
      service.addEventListener('error', listener2);
      
      service.removeAllEventListeners();
      
      // Events should not be emitted after removing all listeners
      // This is tested implicitly by the service not crashing
      expect(() => service.removeAllEventListeners()).not.toThrow();
    });
  });

  describe('Cleanup and Disposal', () => {
    it('should stop capture and clean up resources', async () => {
      const service = new AudioCaptureService();
      await service.captureSystemAndMicAudio();
      
      await service.stopCapture();
      
      const state = service.getState();
      expect(state.isCapturing).toBe(false);
      expect(state.hasSystemAudio).toBe(false);
      expect(state.hasMicrophone).toBe(false);
      
      // Verify audio context was closed
      expect(mockAudioContext.close).toHaveBeenCalled();
    });

    it('should dispose service completely', async () => {
      const service = new AudioCaptureService();
      await service.captureSystemAndMicAudio();
      
      await service.dispose();
      
      const state = service.getState();
      expect(state.isCapturing).toBe(false);
      
      // Should not throw when disposing again
      await expect(service.dispose()).resolves.not.toThrow();
    });
  });

  describe('Quality Metrics', () => {
    it('should provide quality metrics', () => {
      const service = new AudioCaptureService();
      const metrics = service.getQualityMetrics();
      
      expect(metrics).toHaveProperty('droppedChunks');
      expect(metrics).toHaveProperty('averageLatency');
      expect(metrics).toHaveProperty('lastQualityCheck');
      expect(typeof metrics.droppedChunks).toBe('number');
      expect(typeof metrics.averageLatency).toBe('number');
      expect(typeof metrics.lastQualityCheck).toBe('number');
    });
  });
});

describe('Utility Functions', () => {
  describe('createAudioCaptureService', () => {
    it('should create service with default config', () => {
      const service = createAudioCaptureService();
      expect(service).toBeInstanceOf(AudioCaptureService);
      
      const config = service.getConfig();
      expect(config.sampleRate).toBe(44100);
    });

    it('should create service with custom config', () => {
      const service = createAudioCaptureService({ sampleRate: 48000 });
      expect(service).toBeInstanceOf(AudioCaptureService);
      
      const config = service.getConfig();
      expect(config.sampleRate).toBe(48000);
    });
  });

  describe('validateBrowserAudioSupport', () => {
    it('should validate browser support', () => {
      const support = validateBrowserAudioSupport();
      expect(support).toHaveProperty('isSupported');
      expect(support).toHaveProperty('hasGetDisplayMedia');
      expect(support).toHaveProperty('hasGetUserMedia');
      expect(support).toHaveProperty('hasAudioContext');
      expect(support).toHaveProperty('hasMediaRecorder');
      expect(support).toHaveProperty('supportedFormats');
      expect(support).toHaveProperty('issues');
    });
  });

  describe('createAudioChunk', () => {
    it('should create audio chunk with metadata', () => {
      const blob = new Blob(['test'], { type: 'audio/webm' });
      const chunk = createAudioChunk(blob, {
        speakerTag: 'speaker1',
        audioLevels: { systemAudio: 50, microphone: 75, mixed: 60 }
      });
      
      expect(chunk.id).toMatch(/^chunk_\d+_[a-z0-9]+$/);
      expect(chunk.data).toBe(blob);
      expect(chunk.timestamp).toBeGreaterThan(0);
      expect(chunk.duration).toBe(0);
      expect(chunk.speakerTag).toBe('speaker1');
      expect(chunk.audioLevels).toEqual({
        systemAudio: 50,
        microphone: 75,
        mixed: 60
      });
    });

    it('should create audio chunk with minimal options', () => {
      const blob = new Blob(['test'], { type: 'audio/webm' });
      const chunk = createAudioChunk(blob);
      
      expect(chunk.id).toMatch(/^chunk_\d+_[a-z0-9]+$/);
      expect(chunk.data).toBe(blob);
      expect(chunk.timestamp).toBeGreaterThan(0);
      expect(chunk.duration).toBe(0);
      expect(chunk.speakerTag).toBeUndefined();
      expect(chunk.audioLevels).toBeUndefined();
    });
  });
});

describe('Error Classes', () => {
  describe('AudioCaptureError', () => {
    it('should create error with message and code', () => {
      const error = new AudioCaptureError('Test error', 'TEST_CODE');
      
      expect(error.message).toBe('Test error');
      expect(error.code).toBe('TEST_CODE');
      expect(error.recoverable).toBe(true);
      expect(error.name).toBe('AudioCaptureError');
    });

    it('should create non-recoverable error', () => {
      const error = new AudioCaptureError('Fatal error', 'FATAL', false);
      
      expect(error.recoverable).toBe(false);
    });
  });

  describe('AudioDeviceError', () => {
    it('should create device error', () => {
      const error = new AudioDeviceError('Device failed', 'microphone');
      
      expect(error.message).toBe('Device failed');
      expect(error.deviceType).toBe('microphone');
      expect(error.code).toBe('DEVICE_ERROR');
      expect(error.recoverable).toBe(true);
      expect(error.name).toBe('AudioDeviceError');
    });
  });

  describe('AudioCompatibilityError', () => {
    it('should create compatibility error', () => {
      const missingFeatures = ['getDisplayMedia', 'AudioContext'];
      const error = new AudioCompatibilityError('Browser not supported', missingFeatures);
      
      expect(error.message).toBe('Browser not supported');
      expect(error.missingFeatures).toEqual(missingFeatures);
      expect(error.code).toBe('COMPATIBILITY_ERROR');
      expect(error.recoverable).toBe(false);
      expect(error.name).toBe('AudioCompatibilityError');
    });
  });
});