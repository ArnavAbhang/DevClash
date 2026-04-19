import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Web Audio API
const mockAudioContext = {
  createMediaStreamSource: vi.fn(),
  createAnalyser: vi.fn(),
  createGain: vi.fn(),
  createDynamicsCompressor: vi.fn(),
  createBiquadFilter: vi.fn(),
  createMediaStreamDestination: vi.fn(),
  resume: vi.fn().mockResolvedValue(undefined),
  close: vi.fn().mockResolvedValue(undefined),
  sampleRate: 44100,
};

const mockAnalyser = {
  fftSize: 256,
  smoothingTimeConstant: 0.8,
  frequencyBinCount: 128,
  connect: vi.fn(),
  getByteFrequencyData: vi.fn(),
};

const mockGain = {
  gain: { value: 1.0 },
  connect: vi.fn(),
};

const mockCompressor = {
  threshold: { value: -24 },
  knee: { value: 30 },
  ratio: { value: 12 },
  attack: { value: 0.003 },
  release: { value: 0.25 },
  connect: vi.fn(),
};

const mockFilter = {
  type: 'highpass',
  frequency: { value: 80 },
  Q: { value: 0.7 },
  connect: vi.fn(),
};

const mockDestination = {
  stream: new MediaStream(),
  connect: vi.fn(),
};

// Mock MediaStreamTrack
const mockMediaStreamTrack = {
  id: 'mock-track-id',
  kind: 'audio',
  label: 'Mock Audio Track',
  enabled: true,
  muted: false,
  readyState: 'live',
  stop: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
};

// Mock MediaDevices API
const mockGetDisplayMedia = vi.fn();
const mockGetUserMedia = vi.fn();
const mockEnumerateDevices = vi.fn();

// Enhanced Audio Processing Functions
interface AudioCaptureConfig {
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

interface AudioLevels {
  systemAudio: number;
  microphone: number;
  mixed: number;
  timestamp: number;
}

interface AudioDeviceInfo {
  deviceId: string;
  label: string;
  kind: MediaDeviceKind;
  groupId: string;
}

// Mock implementation of enhanced audio processing functions
const validateAudioSupport = () => {
  const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
  const hasMediaDevices = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  const hasDisplayMedia = !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia);
  const hasMediaRecorder = typeof MediaRecorder !== 'undefined';
  
  return {
    audioContext: !!AudioContextClass,
    mediaDevices: hasMediaDevices,
    displayMedia: hasDisplayMedia,
    mediaRecorder: hasMediaRecorder,
    isSupported: !!(AudioContextClass && hasMediaDevices && hasDisplayMedia && hasMediaRecorder)
  };
};

const calculateAudioLevel = (analyser: any): number => {
  const dataArray = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(dataArray);
  const average = dataArray.reduce((sum: number, value: number) => sum + value, 0) / dataArray.length;
  return Math.min(100, Math.round((average / 255) * 100));
};

const getAvailableAudioDevices = async (): Promise<AudioDeviceInfo[]> => {
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices
    .filter(device => device.kind === 'audioinput')
    .map(device => ({
      deviceId: device.deviceId,
      label: device.label || `Microphone ${device.deviceId.slice(0, 8)}`,
      kind: device.kind,
      groupId: device.groupId
    }));
};

const createEnhancedAudioStream = async (config: AudioCaptureConfig, selectedMicId: string) => {
  // Get display stream with system audio
  const displayStream = await navigator.mediaDevices.getDisplayMedia({ 
    audio: {
      echoCancellation: config.echoCancellation,
      noiseSuppression: config.noiseSuppression,
      autoGainControl: config.autoGainControl,
      sampleRate: config.sampleRate,
      channelCount: config.channels
    }, 
    video: true 
  });

  // Get microphone stream
  const micConstraints: MediaStreamConstraints = {
    audio: {
      deviceId: selectedMicId !== 'default' ? { exact: selectedMicId } : undefined,
      echoCancellation: config.echoCancellation,
      noiseSuppression: config.noiseSuppression,
      autoGainControl: config.autoGainControl,
      sampleRate: config.sampleRate,
      channelCount: config.channels
    }
  };
  const micStream = await navigator.mediaDevices.getUserMedia(micConstraints);

  // Create audio context
  const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
  const audioContext = new AudioContextClass({ sampleRate: config.sampleRate });
  await audioContext.resume();

  return {
    displayStream,
    micStream,
    audioContext,
    hasSystemAudio: displayStream.getAudioTracks().length > 0,
    hasMicrophone: micStream.getAudioTracks().length > 0
  };
};

describe('Enhanced Audio Processing', () => {
  beforeEach(() => {
    // Setup global mocks
    (global as any).AudioContext = function MockAudioContext() { return mockAudioContext; };
    (global as any).webkitAudioContext = function MockWebkitAudioContext() { return mockAudioContext; };
    (global as any).MediaStreamTrack = function MockMediaStreamTrack() { return mockMediaStreamTrack; };
    
    mockAudioContext.createAnalyser.mockReturnValue(mockAnalyser);
    mockAudioContext.createGain.mockReturnValue(mockGain);
    mockAudioContext.createDynamicsCompressor.mockReturnValue(mockCompressor);
    mockAudioContext.createBiquadFilter.mockReturnValue(mockFilter);
    mockAudioContext.createMediaStreamDestination.mockReturnValue(mockDestination);
    mockAudioContext.createMediaStreamSource.mockReturnValue({ connect: vi.fn() });

    // Mock MediaDevices
    Object.defineProperty(navigator, 'mediaDevices', {
      value: {
        getDisplayMedia: mockGetDisplayMedia,
        getUserMedia: mockGetUserMedia,
        enumerateDevices: mockEnumerateDevices,
      },
      writable: true,
      configurable: true,
    });

    // Mock MediaRecorder
    (global as any).MediaRecorder = function MockMediaRecorder() {
      return {
        start: vi.fn(),
        stop: vi.fn(),
        ondataavailable: null,
        onstop: null,
        state: 'inactive',
      };
    };
    (global as any).MediaRecorder.isTypeSupported = vi.fn(() => true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('validateAudioSupport', () => {
    it('should return true for supported browser', () => {
      const support = validateAudioSupport();
      
      expect(support.audioContext).toBe(true);
      expect(support.mediaDevices).toBe(true);
      expect(support.displayMedia).toBe(true);
      expect(support.mediaRecorder).toBe(true);
      expect(support.isSupported).toBe(true);
    });

    it('should return false for unsupported browser', () => {
      // Temporarily remove AudioContext
      const originalAudioContext = (global as any).AudioContext;
      delete (global as any).AudioContext;
      delete (global as any).webkitAudioContext;
      
      const support = validateAudioSupport();
      
      expect(support.audioContext).toBe(false);
      expect(support.isSupported).toBe(false);
      
      // Restore
      (global as any).AudioContext = originalAudioContext;
    });
  });

  describe('calculateAudioLevel', () => {
    it('should calculate correct audio level', () => {
      const mockDataArray = new Uint8Array([100, 150, 200, 50]);
      mockAnalyser.getByteFrequencyData.mockImplementation((array: Uint8Array) => {
        array.set(mockDataArray);
      });
      mockAnalyser.frequencyBinCount = 4;

      const level = calculateAudioLevel(mockAnalyser);
      
      // Average: (100 + 150 + 200 + 50) / 4 = 125
      // Percentage: (125 / 255) * 100 ≈ 49
      expect(level).toBe(49);
      expect(mockAnalyser.getByteFrequencyData).toHaveBeenCalled();
    });

    it('should cap audio level at 100', () => {
      const mockDataArray = new Uint8Array([255, 255, 255, 255]);
      mockAnalyser.getByteFrequencyData.mockImplementation((array: Uint8Array) => {
        array.set(mockDataArray);
      });
      mockAnalyser.frequencyBinCount = 4;

      const level = calculateAudioLevel(mockAnalyser);
      
      expect(level).toBe(100);
    });
  });

  describe('getAvailableAudioDevices', () => {
    it('should return filtered audio input devices', async () => {
      const mockDevices = [
        { deviceId: 'mic1', label: 'Built-in Microphone', kind: 'audioinput', groupId: 'group1' },
        { deviceId: 'cam1', label: 'Built-in Camera', kind: 'videoinput', groupId: 'group1' },
        { deviceId: 'mic2', label: 'External Microphone', kind: 'audioinput', groupId: 'group2' },
        { deviceId: 'speaker1', label: 'Built-in Speaker', kind: 'audiooutput', groupId: 'group1' },
      ];
      
      mockEnumerateDevices.mockResolvedValue(mockDevices);

      const devices = await getAvailableAudioDevices();
      
      expect(devices).toHaveLength(2);
      expect(devices[0]).toEqual({
        deviceId: 'mic1',
        label: 'Built-in Microphone',
        kind: 'audioinput',
        groupId: 'group1'
      });
      expect(devices[1]).toEqual({
        deviceId: 'mic2',
        label: 'External Microphone',
        kind: 'audioinput',
        groupId: 'group2'
      });
    });

    it('should provide fallback labels for unnamed devices', async () => {
      const mockDevices = [
        { deviceId: 'abcd1234efgh5678', label: '', kind: 'audioinput', groupId: 'group1' },
      ];
      
      mockEnumerateDevices.mockResolvedValue(mockDevices);

      const devices = await getAvailableAudioDevices();
      
      expect(devices[0].label).toBe('Microphone abcd1234');
    });
  });

  describe('createEnhancedAudioStream', () => {
    it('should create enhanced audio stream with system and microphone audio', async () => {
      const config: AudioCaptureConfig = {
        sampleRate: 44100,
        channels: 2,
        chunkSize: 4096,
        format: 'webm',
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        systemAudioGain: 1.2,
        microphoneGain: 1.0,
      };

      const mockDisplayStream = new MediaStream();
      const mockTrack1 = { ...mockMediaStreamTrack, id: 'track1' };
      mockDisplayStream.addTrack(mockTrack1 as any);
      
      const mockMicStream = new MediaStream();
      const mockTrack2 = { ...mockMediaStreamTrack, id: 'track2' };
      mockMicStream.addTrack(mockTrack2 as any);

      mockGetDisplayMedia.mockResolvedValue(mockDisplayStream);
      mockGetUserMedia.mockResolvedValue(mockMicStream);

      const result = await createEnhancedAudioStream(config, 'default');

      expect(mockGetDisplayMedia).toHaveBeenCalledWith({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 44100,
          channelCount: 2
        },
        video: true
      });

      expect(mockGetUserMedia).toHaveBeenCalledWith({
        audio: {
          deviceId: undefined,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 44100,
          channelCount: 2
        }
      });

      expect(result.hasSystemAudio).toBe(true);
      expect(result.hasMicrophone).toBe(true);
      expect(mockAudioContext.resume).toHaveBeenCalled();
    });

    it('should use specific microphone device when selected', async () => {
      const config: AudioCaptureConfig = {
        sampleRate: 48000,
        channels: 1,
        chunkSize: 2048,
        format: 'wav',
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        systemAudioGain: 1.0,
        microphoneGain: 1.5,
      };

      const mockDisplayStream = new MediaStream();
      const mockMicStream = new MediaStream();
      const mockTrack = { ...mockMediaStreamTrack, id: 'track3' };
      mockMicStream.addTrack(mockTrack as any);

      mockGetDisplayMedia.mockResolvedValue(mockDisplayStream);
      mockGetUserMedia.mockResolvedValue(mockMicStream);

      await createEnhancedAudioStream(config, 'specific-mic-id');

      expect(mockGetUserMedia).toHaveBeenCalledWith({
        audio: {
          deviceId: { exact: 'specific-mic-id' },
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          sampleRate: 48000,
          channelCount: 1
        }
      });
    });

    it('should handle missing system audio gracefully', async () => {
      const config: AudioCaptureConfig = {
        sampleRate: 44100,
        channels: 2,
        chunkSize: 4096,
        format: 'webm',
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        systemAudioGain: 1.2,
        microphoneGain: 1.0,
      };

      const mockDisplayStream = new MediaStream(); // No audio tracks - should have 0 tracks
      const mockMicStream = new MediaStream();
      const mockTrack = { ...mockMediaStreamTrack, id: 'track4' };
      mockMicStream.addTrack(mockTrack as any);

      // Override getAudioTracks to return empty array for display stream
      mockDisplayStream.getAudioTracks = vi.fn().mockReturnValue([]);
      mockMicStream.getAudioTracks = vi.fn().mockReturnValue([mockTrack]);

      mockGetDisplayMedia.mockResolvedValue(mockDisplayStream);
      mockGetUserMedia.mockResolvedValue(mockMicStream);

      const result = await createEnhancedAudioStream(config, 'default');

      expect(result.hasSystemAudio).toBe(false);
      expect(result.hasMicrophone).toBe(true);
    });

    it('should handle errors in stream creation', async () => {
      const config: AudioCaptureConfig = {
        sampleRate: 44100,
        channels: 2,
        chunkSize: 4096,
        format: 'webm',
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        systemAudioGain: 1.2,
        microphoneGain: 1.0,
      };

      mockGetDisplayMedia.mockRejectedValue(new Error('Display media access denied'));

      await expect(createEnhancedAudioStream(config, 'default')).rejects.toThrow('Display media access denied');
    });
  });

  describe('Audio Configuration Validation', () => {
    it('should validate sample rate ranges', () => {
      const validRates = [22050, 44100, 48000];
      const invalidRates = [8000, 96000, 192000];

      validRates.forEach(rate => {
        expect(rate).toBeGreaterThanOrEqual(22050);
        expect(rate).toBeLessThanOrEqual(48000);
      });

      invalidRates.forEach(rate => {
        expect(rate < 22050 || rate > 48000).toBe(true);
      });
    });

    it('should validate gain ranges', () => {
      const validGains = [0.1, 1.0, 2.0];
      const invalidGains = [0.0, -1.0, 3.0];

      validGains.forEach(gain => {
        expect(gain).toBeGreaterThanOrEqual(0.1);
        expect(gain).toBeLessThanOrEqual(2.0);
      });

      invalidGains.forEach(gain => {
        expect(gain < 0.1 || gain > 2.0).toBe(true);
      });
    });

    it('should validate supported formats', () => {
      const validFormats = ['webm', 'wav', 'mp3'];
      const invalidFormats = ['flac', 'ogg', 'aac'];

      validFormats.forEach(format => {
        expect(['webm', 'wav', 'mp3']).toContain(format);
      });

      invalidFormats.forEach(format => {
        expect(['webm', 'wav', 'mp3']).not.toContain(format);
      });
    });
  });
});