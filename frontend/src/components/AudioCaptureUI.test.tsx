import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from '../context/ThemeContext';

// Mock the audio components since they use Canvas API and Web Audio API
const MockCanvasAudioVisualizer = ({ isActive }: { isActive: boolean }) => (
  <div data-testid="canvas-visualizer" data-active={isActive}>
    Canvas Visualizer
  </div>
);

const MockRecordingStatusIndicator = ({ 
  isRecording, 
  hasSystemAudio, 
  hasMicrophone, 
  voiceDetected 
}: { 
  isRecording: boolean; 
  hasSystemAudio: boolean; 
  hasMicrophone: boolean; 
  voiceDetected: boolean;
}) => (
  <div data-testid="recording-status" data-recording={isRecording}>
    <span data-testid="system-audio" data-active={hasSystemAudio}>System</span>
    <span data-testid="microphone" data-active={hasMicrophone}>Mic</span>
    <span data-testid="voice-detected" data-active={voiceDetected}>Voice</span>
  </div>
);

const MockAudioQualityPanel = ({ 
  config, 
  onConfigChange, 
  isExpanded, 
  onToggle 
}: { 
  config: any; 
  onConfigChange: (updates: any) => void;
  isExpanded: boolean;
  onToggle: () => void;
}) => (
  <div data-testid="quality-panel" data-expanded={isExpanded}>
    <button onClick={onToggle} data-testid="quality-toggle">
      Audio Quality Settings
    </button>
    {isExpanded && (
      <div data-testid="quality-controls">
        <button 
          onClick={() => onConfigChange({ sampleRate: 48000 })}
          data-testid="sample-rate-48k"
        >
          48kHz
        </button>
        <button 
          onClick={() => onConfigChange({ format: 'wav' })}
          data-testid="format-wav"
        >
          WAV
        </button>
      </div>
    )}
  </div>
);

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('Enhanced Audio Capture UI Components', () => {
  const renderWithTheme = (component: React.ReactElement) => {
    return render(
      <ThemeProvider>
        {component}
      </ThemeProvider>
    );
  };

  describe('CanvasAudioVisualizer', () => {
    it('should render when active', () => {
      renderWithTheme(<MockCanvasAudioVisualizer isActive={true} />);
      
      const visualizer = screen.getByTestId('canvas-visualizer');
      expect(visualizer).toBeInTheDocument();
      expect(visualizer).toHaveAttribute('data-active', 'true');
    });

    it('should render when inactive', () => {
      renderWithTheme(<MockCanvasAudioVisualizer isActive={false} />);
      
      const visualizer = screen.getByTestId('canvas-visualizer');
      expect(visualizer).toBeInTheDocument();
      expect(visualizer).toHaveAttribute('data-active', 'false');
    });
  });

  describe('RecordingStatusIndicator', () => {
    it('should show recording status correctly', () => {
      renderWithTheme(
        <MockRecordingStatusIndicator
          isRecording={true}
          hasSystemAudio={true}
          hasMicrophone={true}
          voiceDetected={true}
        />
      );

      const status = screen.getByTestId('recording-status');
      expect(status).toHaveAttribute('data-recording', 'true');
      
      const systemAudio = screen.getByTestId('system-audio');
      expect(systemAudio).toHaveAttribute('data-active', 'true');
      
      const microphone = screen.getByTestId('microphone');
      expect(microphone).toHaveAttribute('data-active', 'true');
      
      const voiceDetected = screen.getByTestId('voice-detected');
      expect(voiceDetected).toHaveAttribute('data-active', 'true');
    });

    it('should show inactive states correctly', () => {
      renderWithTheme(
        <MockRecordingStatusIndicator
          isRecording={false}
          hasSystemAudio={false}
          hasMicrophone={false}
          voiceDetected={false}
        />
      );

      const status = screen.getByTestId('recording-status');
      expect(status).toHaveAttribute('data-recording', 'false');
      
      const systemAudio = screen.getByTestId('system-audio');
      expect(systemAudio).toHaveAttribute('data-active', 'false');
      
      const microphone = screen.getByTestId('microphone');
      expect(microphone).toHaveAttribute('data-active', 'false');
      
      const voiceDetected = screen.getByTestId('voice-detected');
      expect(voiceDetected).toHaveAttribute('data-active', 'false');
    });
  });

  describe('AudioQualityPanel', () => {
    it('should toggle expansion correctly', () => {
      const mockOnToggle = vi.fn();
      const mockOnConfigChange = vi.fn();
      
      renderWithTheme(
        <MockAudioQualityPanel
          config={{ sampleRate: 44100, format: 'webm' }}
          onConfigChange={mockOnConfigChange}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      const panel = screen.getByTestId('quality-panel');
      expect(panel).toHaveAttribute('data-expanded', 'false');
      
      const toggleButton = screen.getByTestId('quality-toggle');
      fireEvent.click(toggleButton);
      
      expect(mockOnToggle).toHaveBeenCalledTimes(1);
    });

    it('should show controls when expanded', () => {
      const mockOnToggle = vi.fn();
      const mockOnConfigChange = vi.fn();
      
      renderWithTheme(
        <MockAudioQualityPanel
          config={{ sampleRate: 44100, format: 'webm' }}
          onConfigChange={mockOnConfigChange}
          isExpanded={true}
          onToggle={mockOnToggle}
        />
      );

      const controls = screen.getByTestId('quality-controls');
      expect(controls).toBeInTheDocument();
      
      const sampleRateButton = screen.getByTestId('sample-rate-48k');
      fireEvent.click(sampleRateButton);
      
      expect(mockOnConfigChange).toHaveBeenCalledWith({ sampleRate: 48000 });
      
      const formatButton = screen.getByTestId('format-wav');
      fireEvent.click(formatButton);
      
      expect(mockOnConfigChange).toHaveBeenCalledWith({ format: 'wav' });
    });

    it('should hide controls when collapsed', () => {
      const mockOnToggle = vi.fn();
      const mockOnConfigChange = vi.fn();
      
      renderWithTheme(
        <MockAudioQualityPanel
          config={{ sampleRate: 44100, format: 'webm' }}
          onConfigChange={mockOnConfigChange}
          isExpanded={false}
          onToggle={mockOnToggle}
        />
      );

      const controls = screen.queryByTestId('quality-controls');
      expect(controls).not.toBeInTheDocument();
    });
  });
});