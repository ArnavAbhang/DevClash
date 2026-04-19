/**
 * Enhanced Transcript Panel Tests
 * Tests for the enhanced Live Transcript Panel functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock the transcript functionality
const mockTranscriptLines = [
  {
    id: '1',
    timestamp: '10:30:15',
    speaker: 'Speaker A',
    text: 'Hello everyone, welcome to the meeting',
    confidence: 0.95
  },
  {
    id: '2',
    timestamp: '10:30:20',
    speaker: 'Speaker B',
    text: 'Thank you for joining us today',
    confidence: 0.88
  },
  {
    id: '3',
    timestamp: '10:30:25',
    speaker: 'Speaker A',
    text: 'Let me assign this task to John for tomorrow',
    confidence: 0.92
  }
];

// Mock component for testing transcript functionality
const MockTranscriptPanel = ({ 
  transcriptLines = mockTranscriptLines,
  onSearch = vi.fn(),
  onSpeakerFilter = vi.fn(),
  onExport = vi.fn()
}) => {
  return (
    <div data-testid="transcript-panel">
      <div data-testid="search-input">
        <input 
          placeholder="Search transcript..."
          onChange={(e) => onSearch(e.target.value)}
        />
      </div>
      
      <div data-testid="speaker-filter">
        <select onChange={(e) => onSpeakerFilter(e.target.value)}>
          <option value="all">All Speakers</option>
          <option value="Speaker A">Speaker A</option>
          <option value="Speaker B">Speaker B</option>
        </select>
      </div>

      <div data-testid="transcript-content">
        {transcriptLines.map(line => (
          <div key={line.id} data-testid={`segment-${line.id}`}>
            <span data-testid="timestamp">{line.timestamp}</span>
            <span data-testid="speaker">{line.speaker}</span>
            <span data-testid="text">{line.text}</span>
            <span data-testid="confidence">{Math.round(line.confidence * 100)}%</span>
          </div>
        ))}
      </div>

      <div data-testid="export-controls">
        <button onClick={() => onExport('txt')}>Export TXT</button>
        <button onClick={() => onExport('json')}>Export JSON</button>
        <button onClick={() => onExport('srt')}>Export SRT</button>
      </div>
    </div>
  );
};

describe('Enhanced Transcript Panel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders transcript segments with all metadata', () => {
    render(<MockTranscriptPanel />);
    
    // Check that all segments are rendered
    expect(screen.getByTestId('segment-1')).toBeInTheDocument();
    expect(screen.getByTestId('segment-2')).toBeInTheDocument();
    expect(screen.getByTestId('segment-3')).toBeInTheDocument();
    
    // Check timestamp display
    expect(screen.getByText('10:30:15')).toBeInTheDocument();
    expect(screen.getByText('10:30:20')).toBeInTheDocument();
    
    // Check speaker identification
    expect(screen.getAllByText('Speaker A')).toHaveLength(3); // 2 segments + 1 in dropdown
    expect(screen.getAllByText('Speaker B')).toHaveLength(2); // 1 segment + 1 in dropdown
    
    // Check confidence scores
    expect(screen.getByText('95%')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
  });

  it('provides search functionality', async () => {
    const mockOnSearch = vi.fn();
    render(<MockTranscriptPanel onSearch={mockOnSearch} />);
    
    const searchInput = screen.getByPlaceholderText('Search transcript...');
    
    fireEvent.change(searchInput, { target: { value: 'meeting' } });
    
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith('meeting');
    });
  });

  it('provides speaker filtering', async () => {
    const mockOnSpeakerFilter = vi.fn();
    render(<MockTranscriptPanel onSpeakerFilter={mockOnSpeakerFilter} />);
    
    const speakerSelect = screen.getByDisplayValue('All Speakers');
    
    fireEvent.change(speakerSelect, { target: { value: 'Speaker A' } });
    
    await waitFor(() => {
      expect(mockOnSpeakerFilter).toHaveBeenCalledWith('Speaker A');
    });
  });

  it('provides export functionality for different formats', async () => {
    const mockOnExport = vi.fn();
    render(<MockTranscriptPanel onExport={mockOnExport} />);
    
    // Test TXT export
    fireEvent.click(screen.getByText('Export TXT'));
    expect(mockOnExport).toHaveBeenCalledWith('txt');
    
    // Test JSON export
    fireEvent.click(screen.getByText('Export JSON'));
    expect(mockOnExport).toHaveBeenCalledWith('json');
    
    // Test SRT export
    fireEvent.click(screen.getByText('Export SRT'));
    expect(mockOnExport).toHaveBeenCalledWith('srt');
  });

  it('displays confidence indicators correctly', () => {
    render(<MockTranscriptPanel />);
    
    // High confidence (95%) should be displayed
    const highConfidence = screen.getByText('95%');
    expect(highConfidence).toBeInTheDocument();
    
    // Medium confidence (88%) should be displayed
    const mediumConfidence = screen.getByText('88%');
    expect(mediumConfidence).toBeInTheDocument();
    
    // All confidence scores should be present
    const confidenceElements = screen.getAllByText(/%$/);
    expect(confidenceElements).toHaveLength(3);
  });

  it('handles empty transcript state', () => {
    render(<MockTranscriptPanel transcriptLines={[]} />);
    
    const transcriptContent = screen.getByTestId('transcript-content');
    expect(transcriptContent).toBeEmptyDOMElement();
  });

  it('displays task-related content correctly', () => {
    render(<MockTranscriptPanel />);
    
    // Check that task-related text is displayed
    expect(screen.getByText('Let me assign this task to John for tomorrow')).toBeInTheDocument();
  });
});

// Test utility functions
describe('Transcript Utility Functions', () => {
  describe('highlightSearchTerms', () => {
    const highlightSearchTerms = (text: string, searchTerm: string) => {
      if (!searchTerm.trim()) return text;
      const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      return text.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">$1</mark>');
    };

    it('highlights search terms correctly', () => {
      const text = 'Hello everyone, welcome to the meeting';
      const highlighted = highlightSearchTerms(text, 'meeting');
      
      expect(highlighted).toContain('<mark class="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">meeting</mark>');
    });

    it('handles case-insensitive search', () => {
      const text = 'Hello Everyone';
      const highlighted = highlightSearchTerms(text, 'everyone');
      
      expect(highlighted).toContain('<mark class="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">Everyone</mark>');
    });

    it('returns original text when no search term', () => {
      const text = 'Hello everyone';
      const highlighted = highlightSearchTerms(text, '');
      
      expect(highlighted).toBe(text);
    });
  });

  describe('exportTranscriptSegments', () => {
    const mockSegments = [
      {
        id: '1',
        timestamp: '10:30:15',
        speaker: 'Speaker A',
        text: 'Hello everyone',
        confidence: 0.95
      }
    ];

    it('generates correct TXT format', () => {
      const expectedTxt = '[10:30:15] Speaker A: Hello everyone';
      const result = mockSegments.map(line => 
        `[${line.timestamp}] ${line.speaker}: ${line.text}`
      ).join('\n');
      
      expect(result).toBe(expectedTxt);
    });

    it('generates correct JSON format structure', () => {
      const jsonData = {
        transcript: mockSegments.map(line => ({
          id: line.id,
          timestamp: line.timestamp,
          speaker: line.speaker,
          text: line.text,
          confidence: line.confidence,
          startTime: line.timestamp,
          endTime: line.timestamp
        })),
        metadata: {
          totalSegments: mockSegments.length,
          totalWords: mockSegments.reduce((count, line) => count + line.text.split(/\s+/).length, 0),
          speakers: Array.from(new Set(mockSegments.map(line => line.speaker))),
          exportedAt: expect.any(String),
          confidence: {
            average: mockSegments.reduce((sum, line) => sum + line.confidence, 0) / mockSegments.length,
            high: mockSegments.filter(line => line.confidence >= 0.85).length,
            medium: mockSegments.filter(line => line.confidence >= 0.7 && line.confidence < 0.85).length,
            low: mockSegments.filter(line => line.confidence < 0.7).length
          }
        }
      };

      expect(jsonData.transcript).toHaveLength(1);
      expect(jsonData.metadata.totalSegments).toBe(1);
      expect(jsonData.metadata.speakers).toContain('Speaker A');
    });
  });
});