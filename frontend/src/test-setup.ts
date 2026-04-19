import '@testing-library/jest-dom'

// Mock MediaStream and related APIs for testing
global.MediaStream = class MediaStream {
  constructor() {
    this.id = Math.random().toString(36).substr(2, 9);
  }
  
  getAudioTracks() {
    return [{ stop: () => {} }];
  }
  
  getTracks() {
    return [{ stop: () => {} }];
  }
  
  addTrack() {}
  removeTrack() {}
  clone() {
    return new MediaStream();
  }
} as any;

// Mock Blob for audio data
global.Blob = class Blob {
  constructor(parts: any[], options?: any) {
    this.size = parts.reduce((acc, part) => acc + (part.length || 0), 0);
    this.type = options?.type || '';
  }
  
  size: number;
  type: string;
} as any;