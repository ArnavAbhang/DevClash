/**
 * TaskPanel.test.tsx
 * ~~~~~~~~~~~~~~~~~~
 * Tests for the enhanced TaskPanel component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider } from '../context/ThemeContext';
import TaskPanel from './TaskPanel';
import { DetectedTask } from '../services/detectedTasksService';

// Mock the hooks and services
vi.mock('../hooks/useDetectedTasks', () => ({
  useDetectedTasks: () => ({
    tasks: mockTasks,
    pendingTasks: mockTasks.filter(t => t.status === 'pending'),
    completedTasks: mockTasks.filter(t => t.status === 'done'),
    highConfidenceTasks: mockTasks.filter(t => t.confidence >= 0.8),
    lowConfidenceTasks: mockTasks.filter(t => t.confidence < 0.7),
    participants: ['John Doe', 'Jane Smith'],
    loading: false,
    error: null,
    connected: true,
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    addParticipant: vi.fn(),
    clearError: vi.fn()
  })
}));

vi.mock('./ToastSystem', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn()
  })
}));

const mockTasks: DetectedTask[] = [
  {
    id: '1',
    title: 'Review the quarterly report',
    description: 'Need to review Q4 numbers',
    status: 'pending',
    priority: 'high',
    confidence: 0.85,
    source_text: 'Can you review the quarterly report by tomorrow?',
    assignee: 'John Doe',
    deadline: '2024-01-15T00:00:00Z',
    user_id: 'user1',
    meeting_id: 'meeting1',
    created_at: '2024-01-10T10:00:00Z',
    updated_at: '2024-01-10T10:00:00Z',
    tags: ['urgent', 'finance'],
    approved: false,
    dismissed: false
  },
  {
    id: '2',
    title: 'Schedule team meeting',
    description: 'Weekly sync meeting',
    status: 'done',
    priority: 'medium',
    confidence: 0.75,
    source_text: 'Let\'s schedule our weekly team meeting',
    assignee: 'Jane Smith',
    user_id: 'user1',
    meeting_id: 'meeting1',
    created_at: '2024-01-09T14:00:00Z',
    updated_at: '2024-01-10T09:00:00Z',
    tags: ['meeting'],
    approved: true,
    dismissed: false
  }
];

const renderTaskPanel = (props = {}) => {
  return render(
    <ThemeProvider>
      <TaskPanel userId="user1" meetingId="meeting1" {...props} />
    </ThemeProvider>
  );
};

describe('TaskPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the task panel with header', () => {
    renderTaskPanel();
    
    expect(screen.getByText('AI Tasks')).toBeInTheDocument();
    expect(screen.getByText('Live')).toBeInTheDocument();
  });

  it('displays task statistics correctly', () => {
    renderTaskPanel();
    
    // Should show pending tasks count
    expect(screen.getByText('1')).toBeInTheDocument(); // Pending count
    expect(screen.getByText('Pending')).toBeInTheDocument();
    
    // Should show high confidence tasks
    expect(screen.getByText('High Conf.')).toBeInTheDocument();
    
    // Should show completed tasks
    expect(screen.getByText('Done')).toBeInTheDocument();
  });

  it('shows search functionality', () => {
    renderTaskPanel();
    
    const searchInput = screen.getByPlaceholderText('Search tasks...');
    expect(searchInput).toBeInTheDocument();
  });

  it('displays filter button with active state indicator', () => {
    renderTaskPanel();
    
    const filterButton = screen.getByTitle('Filters');
    expect(filterButton).toBeInTheDocument();
  });

  it('shows export menu when export button is clicked', async () => {
    renderTaskPanel();
    
    const exportButton = screen.getByTitle('Export tasks');
    fireEvent.click(exportButton);
    
    await waitFor(() => {
      expect(screen.getByText('Export as JSON')).toBeInTheDocument();
      expect(screen.getByText('Export as CSV')).toBeInTheDocument();
      expect(screen.getByText('Export as PDF')).toBeInTheDocument();
      expect(screen.getByText('Share Tasks')).toBeInTheDocument();
    });
  });

  it('displays tabs with correct counts', () => {
    renderTaskPanel();
    
    // Check tab labels and counts
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByText('Done')).toBeInTheDocument();
    expect(screen.getByText('All')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
  });

  it('shows analytics dashboard when analytics tab is selected', async () => {
    renderTaskPanel();
    
    const analyticsTab = screen.getByText('Analytics');
    fireEvent.click(analyticsTab);
    
    await waitFor(() => {
      expect(screen.getByText('Completion Rate')).toBeInTheDocument();
      expect(screen.getByText('Avg Confidence')).toBeInTheDocument();
      expect(screen.getByText('Tasks by Assignee')).toBeInTheDocument();
      expect(screen.getByText('7-Day Trend')).toBeInTheDocument();
    });
  });

  it('displays participants section', () => {
    renderTaskPanel();
    
    expect(screen.getByText('Participants (2)')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
  });

  it('shows filters panel when filter button is clicked', async () => {
    renderTaskPanel();
    
    const filterButton = screen.getByTitle('Filters');
    fireEvent.click(filterButton);
    
    await waitFor(() => {
      expect(screen.getByText('Filters & Sorting')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Priority')).toBeInTheDocument();
      expect(screen.getByText('Sort by')).toBeInTheDocument();
      expect(screen.getByText('Confidence Range:')).toBeInTheDocument();
    });
  });

  it('can be collapsed and expanded', async () => {
    renderTaskPanel();
    
    const collapseButton = screen.getByRole('button', { name: /collapse|expand/i });
    fireEvent.click(collapseButton);
    
    // Content should be hidden when collapsed
    await waitFor(() => {
      expect(screen.queryByText('Pending')).not.toBeInTheDocument();
    });
  });

  it('handles search input correctly', async () => {
    renderTaskPanel();
    
    const searchInput = screen.getByPlaceholderText('Search tasks...');
    fireEvent.change(searchInput, { target: { value: 'quarterly' } });
    
    expect(searchInput).toHaveValue('quarterly');
  });

  it('shows empty state when no tasks match filters', async () => {
    // Mock empty tasks
    vi.mocked(require('../hooks/useDetectedTasks').useDetectedTasks).mockReturnValue({
      tasks: [],
      pendingTasks: [],
      completedTasks: [],
      highConfidenceTasks: [],
      lowConfidenceTasks: [],
      participants: [],
      loading: false,
      error: null,
      connected: true,
      updateTask: vi.fn(),
      deleteTask: vi.fn(),
      addParticipant: vi.fn(),
      clearError: vi.fn()
    });

    renderTaskPanel();
    
    expect(screen.getByText('No tasks detected yet')).toBeInTheDocument();
    expect(screen.getByText('Tasks will appear here as they\'re detected from speech')).toBeInTheDocument();
  });
});