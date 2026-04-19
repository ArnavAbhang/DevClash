/**
 * components/TaskPanel.tsx
 * ~~~~~~~~~~~~~~~~~~~~~~~~
 * Enhanced real-time task panel for AI-detected tasks with production-grade features.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckSquare, Clock, User, Calendar, AlertCircle, Trash2, Edit3,
  ChevronDown, ChevronRight, Zap, Brain, Target, Users, Plus, X,
  CheckCircle, Circle, ArrowRight, Sparkles, MessageSquare, Filter,
  SortAsc, SortDesc, Download, Share2, BarChart3, TrendingUp,
  FileText, FileSpreadsheet, FileImage, Search, Tag, UserCheck,
  CalendarDays, Star, Archive, MoreHorizontal, Eye, EyeOff,
  RefreshCw, Settings, PieChart, Activity, Bookmark
} from 'lucide-react';
import { useDetectedTasks } from '../hooks/useDetectedTasks';
import { DetectedTask } from '../services/detectedTasksService';
import { useTheme } from '../context/ThemeContext';
import { useToast } from './ToastSystem';

interface TaskPanelProps {
  userId?: string;
  meetingId?: string;
  className?: string;
  onTaskClick?: (task: DetectedTask) => void;
}

interface TaskCardProps {
  task: DetectedTask;
  onUpdate: (taskId: string, updates: any) => Promise<DetectedTask>;
  onDelete: (taskId: string) => Promise<void>;
  onClick?: () => void;
  showDetails?: boolean;
}

interface FilterOptions {
  status: string[];
  priority: string[];
  assignee: string[];
  dateRange: { start?: Date; end?: Date };
  tags: string[];
  confidence: { min: number; max: number };
}

interface SortOptions {
  field: 'created_at' | 'deadline' | 'priority' | 'confidence' | 'title';
  direction: 'asc' | 'desc';
}

interface TaskAnalytics {
  totalTasks: number;
  completedTasks: number;
  pendingTasks: number;
  highPriorityTasks: number;
  averageConfidence: number;
  tasksByAssignee: Record<string, number>;
  tasksByPriority: Record<string, number>;
  tasksByStatus: Record<string, number>;
  completionRate: number;
  trendsData: Array<{ date: string; count: number; completed: number }>;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, onUpdate, onDelete, onClick, showDetails = false }) => {
  const { isDark } = useTheme();
  const toast = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [isExpanded, setIsExpanded] = useState(showDetails);
  const [editForm, setEditForm] = useState({
    status: task.status,
    assignee: task.assignee || '',
    priority: task.priority,
    deadline: task.deadline ? new Date(task.deadline).toISOString().split('T')[0] : '',
    tags: task.tags?.join(', ') || ''
  });

  const handleStatusChange = async (newStatus: string) => {
    try {
      await onUpdate(task.id, { status: newStatus });
      toast.success(`Task ${newStatus === 'done' ? 'completed' : 'updated'}`);
    } catch (error) {
      toast.error('Failed to update task');
    }
  };

  const handleApprove = async () => {
    try {
      await onUpdate(task.id, { approved: true });
      toast.success('Task approved');
    } catch (error) {
      toast.error('Failed to approve task');
    }
  };

  const handleDismiss = async () => {
    try {
      await onUpdate(task.id, { dismissed: true });
      toast.success('Task dismissed');
    } catch (error) {
      toast.error('Failed to dismiss task');
    }
  };

  const handleSaveEdit = async () => {
    try {
      const updates: any = {
        status: editForm.status,
        assignee: editForm.assignee || null,
        priority: editForm.priority,
        deadline: editForm.deadline ? new Date(editForm.deadline).toISOString() : null,
        tags: editForm.tags ? editForm.tags.split(',').map(t => t.trim()).filter(Boolean) : []
      };
      
      await onUpdate(task.id, updates);
      setIsEditing(false);
      toast.success('Task updated');
    } catch (error) {
      toast.error('Failed to update task');
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this task?')) return;
    
    try {
      await onDelete(task.id);
      toast.success('Task deleted');
    } catch (error) {
      toast.error('Failed to delete task');
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-emerald-500';
    if (confidence >= 0.7) return 'text-amber-500';
    return 'text-red-500';
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-500 bg-red-500/10 border-red-500/20';
      case 'medium': return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
      case 'low': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
      default: return 'text-slate-500 bg-slate-500/10 border-slate-500/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'done': return <CheckCircle size={16} className="text-emerald-500" />;
      case 'in-progress': return <Clock size={16} className="text-amber-500" />;
      default: return <Circle size={16} className="text-slate-500" />;
    }
  };

  const isOverdue = task.deadline && new Date(task.deadline) < new Date() && task.status !== 'done';
  const isDueSoon = task.deadline && new Date(task.deadline) < new Date(Date.now() + 24 * 60 * 60 * 1000) && task.status !== 'done';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={`group border rounded-xl p-4 transition-all cursor-pointer ${
        isDark 
          ? 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600 hover:bg-slate-800/70' 
          : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-md'
      } ${isOverdue ? 'border-red-500/50 bg-red-500/5' : ''} ${
        task.approved ? 'ring-2 ring-emerald-500/20' : ''
      } ${task.dismissed ? 'opacity-50' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleStatusChange(task.status === 'done' ? 'pending' : 'done');
            }}
            className="hover:scale-110 transition-transform"
          >
            {getStatusIcon(task.status)}
          </button>
          <div className="flex items-center space-x-2">
            <span className={`text-xs px-2 py-1 rounded-full font-medium border ${getPriorityColor(task.priority)}`}>
              {task.priority}
            </span>
            <span className={`text-xs font-mono ${getConfidenceColor(task.confidence)}`}>
              {Math.round(task.confidence * 100)}%
            </span>
            {isOverdue && (
              <span className="text-xs px-2 py-1 bg-red-500/20 text-red-500 rounded-full font-medium">
                Overdue
              </span>
            )}
            {isDueSoon && !isOverdue && (
              <span className="text-xs px-2 py-1 bg-amber-500/20 text-amber-500 rounded-full font-medium">
                Due Soon
              </span>
            )}
            {task.approved && (
              <UserCheck size={12} className="text-emerald-500" />
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className={`p-1.5 rounded-lg transition-colors ${
              isDark ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-100 text-slate-600'
            }`}
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
          {!task.approved && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleApprove();
              }}
              className={`p-1.5 rounded-lg transition-colors ${
                isDark ? 'hover:bg-emerald-500/20 text-emerald-400' : 'hover:bg-emerald-50 text-emerald-500'
              }`}
              title="Approve task"
            >
              <UserCheck size={14} />
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(!isEditing);
            }}
            className={`p-1.5 rounded-lg transition-colors ${
              isDark ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-100 text-slate-600'
            }`}
            title="Edit task"
          >
            <Edit3 size={14} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDismiss();
            }}
            className={`p-1.5 rounded-lg transition-colors ${
              isDark ? 'hover:bg-amber-500/20 text-amber-400' : 'hover:bg-amber-50 text-amber-500'
            }`}
            title="Dismiss task"
          >
            <Archive size={14} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDelete();
            }}
            className={`p-1.5 rounded-lg transition-colors ${
              isDark ? 'hover:bg-red-500/20 text-red-400' : 'hover:bg-red-50 text-red-500'
            }`}
            title="Delete task"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="space-y-2">
        <h4 className={`font-semibold text-sm leading-tight ${
          isDark ? 'text-white' : 'text-slate-900'
        } ${task.status === 'done' ? 'line-through opacity-60' : ''}`}>
          {task.title}
        </h4>
        
        {task.description && (
          <p className={`text-xs leading-relaxed ${
            isDark ? 'text-slate-400' : 'text-slate-600'
          } ${task.status === 'done' ? 'line-through opacity-60' : ''}`}>
            {task.description}
          </p>
        )}

        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-3">
            {task.assignee && (
              <div className="flex items-center space-x-1 text-slate-500">
                <User size={12} />
                <span>{task.assignee}</span>
              </div>
            )}
            {task.deadline && (
              <div className={`flex items-center space-x-1 ${
                isOverdue ? 'text-red-500' : isDueSoon ? 'text-amber-500' : 'text-slate-500'
              }`}>
                <Calendar size={12} />
                <span>{new Date(task.deadline).toLocaleDateString()}</span>
              </div>
            )}
          </div>
          <span className="text-slate-500 font-mono">
            {new Date(task.created_at).toLocaleTimeString('en-US', { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </span>
        </div>

        {/* Tags */}
        {task.tags && task.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {task.tags.map((tag, idx) => (
              <span
                key={idx}
                className={`text-xs px-2 py-0.5 rounded-full ${
                  isDark ? 'bg-slate-700 text-slate-300' : 'bg-slate-100 text-slate-600'
                }`}
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Expanded details */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-2"
            >
              {/* Source text */}
              <div className={`text-xs p-2 rounded-lg border-l-2 border-cyan-500/30 ${
                isDark ? 'bg-slate-900/50 text-slate-500' : 'bg-slate-50 text-slate-600'
              }`}>
                <div className="flex items-center space-x-1 mb-1">
                  <MessageSquare size={10} />
                  <span className="font-medium">Source:</span>
                </div>
                <p className="italic">"{task.source_text}"</p>
              </div>

              {/* Additional metadata */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className={`p-2 rounded ${isDark ? 'bg-slate-800' : 'bg-slate-50'}`}>
                  <span className="font-medium text-slate-500">Created:</span>
                  <p>{new Date(task.created_at).toLocaleString()}</p>
                </div>
                {task.updated_at && (
                  <div className={`p-2 rounded ${isDark ? 'bg-slate-800' : 'bg-slate-50'}`}>
                    <span className="font-medium text-slate-500">Updated:</span>
                    <p>{new Date(task.updated_at).toLocaleString()}</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Edit form */}
      <AnimatePresence>
        {isEditing && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={editForm.status}
                  onChange={(e) => setEditForm(f => ({ ...f, status: e.target.value as 'pending' | 'in-progress' | 'done' }))}
                  className={`text-xs px-2 py-1 rounded border ${
                    isDark 
                      ? 'bg-slate-700 border-slate-600 text-white' 
                      : 'bg-white border-slate-300 text-slate-900'
                  }`}
                >
                  <option value="pending">Pending</option>
                  <option value="in-progress">In Progress</option>
                  <option value="done">Done</option>
                </select>
                <select
                  value={editForm.priority}
                  onChange={(e) => setEditForm(f => ({ ...f, priority: e.target.value as 'low' | 'medium' | 'high' }))}
                  className={`text-xs px-2 py-1 rounded border ${
                    isDark 
                      ? 'bg-slate-700 border-slate-600 text-white' 
                      : 'bg-white border-slate-300 text-slate-900'
                  }`}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <input
                type="text"
                placeholder="Assignee"
                value={editForm.assignee}
                onChange={(e) => setEditForm(f => ({ ...f, assignee: e.target.value }))}
                className={`w-full text-xs px-2 py-1 rounded border ${
                  isDark 
                    ? 'bg-slate-700 border-slate-600 text-white placeholder-slate-400' 
                    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-500'
                }`}
              />
              <input
                type="date"
                value={editForm.deadline}
                onChange={(e) => setEditForm(f => ({ ...f, deadline: e.target.value }))}
                className={`w-full text-xs px-2 py-1 rounded border ${
                  isDark 
                    ? 'bg-slate-700 border-slate-600 text-white' 
                    : 'bg-white border-slate-300 text-slate-900'
                }`}
              />
              <input
                type="text"
                placeholder="Tags (comma separated)"
                value={editForm.tags}
                onChange={(e) => setEditForm(f => ({ ...f, tags: e.target.value }))}
                className={`w-full text-xs px-2 py-1 rounded border ${
                  isDark 
                    ? 'bg-slate-700 border-slate-600 text-white placeholder-slate-400' 
                    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-500'
                }`}
              />
              <div className="flex justify-end space-x-2">
                <button
                  onClick={() => setIsEditing(false)}
                  className="text-xs px-3 py-1 text-slate-500 hover:text-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="text-xs px-3 py-1 bg-cyan-500 hover:bg-cyan-600 text-white rounded transition"
                >
                  Save
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Analytics calculation helper
const calculateAnalytics = (tasks: DetectedTask[]): TaskAnalytics => {
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(t => t.status === 'done').length;
  const pendingTasks = tasks.filter(t => t.status === 'pending').length;
  const highPriorityTasks = tasks.filter(t => t.priority === 'high').length;
  const averageConfidence = tasks.length > 0 ? tasks.reduce((sum, t) => sum + t.confidence, 0) / tasks.length : 0;
  
  const tasksByAssignee = tasks.reduce((acc, task) => {
    const assignee = task.assignee || 'Unassigned';
    acc[assignee] = (acc[assignee] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const tasksByPriority = tasks.reduce((acc, task) => {
    acc[task.priority] = (acc[task.priority] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const tasksByStatus = tasks.reduce((acc, task) => {
    acc[task.status] = (acc[task.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const completionRate = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;
  
  // Generate trends data (last 7 days)
  const trendsData = Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    const dateStr = date.toISOString().split('T')[0];
    
    const dayTasks = tasks.filter(t => 
      new Date(t.created_at).toISOString().split('T')[0] === dateStr
    );
    const dayCompleted = dayTasks.filter(t => t.status === 'done').length;
    
    return {
      date: dateStr,
      count: dayTasks.length,
      completed: dayCompleted
    };
  });
  
  return {
    totalTasks,
    completedTasks,
    pendingTasks,
    highPriorityTasks,
    averageConfidence,
    tasksByAssignee,
    tasksByPriority,
    tasksByStatus,
    completionRate,
    trendsData
  };
};

// Export functionality
const exportTasks = (tasks: DetectedTask[], format: 'json' | 'csv' | 'pdf') => {
  switch (format) {
    case 'json':
      const jsonData = JSON.stringify(tasks, null, 2);
      const jsonBlob = new Blob([jsonData], { type: 'application/json' });
      const jsonUrl = URL.createObjectURL(jsonBlob);
      const jsonLink = document.createElement('a');
      jsonLink.href = jsonUrl;
      jsonLink.download = `tasks-${new Date().toISOString().split('T')[0]}.json`;
      jsonLink.click();
      URL.revokeObjectURL(jsonUrl);
      break;
      
    case 'csv':
      const csvHeaders = ['Title', 'Status', 'Priority', 'Assignee', 'Deadline', 'Confidence', 'Created', 'Source'];
      const csvRows = tasks.map(task => [
        task.title,
        task.status,
        task.priority,
        task.assignee || '',
        task.deadline ? new Date(task.deadline).toLocaleDateString() : '',
        Math.round(task.confidence * 100) + '%',
        new Date(task.created_at).toLocaleDateString(),
        `"${task.source_text}"`
      ]);
      const csvContent = [csvHeaders, ...csvRows].map(row => row.join(',')).join('\n');
      const csvBlob = new Blob([csvContent], { type: 'text/csv' });
      const csvUrl = URL.createObjectURL(csvBlob);
      const csvLink = document.createElement('a');
      csvLink.href = csvUrl;
      csvLink.download = `tasks-${new Date().toISOString().split('T')[0]}.csv`;
      csvLink.click();
      URL.revokeObjectURL(csvUrl);
      break;
      
    case 'pdf':
      // For PDF, we'll create a simple HTML report and print it
      const reportWindow = window.open('', '_blank');
      if (reportWindow) {
        reportWindow.document.write(`
          <html>
            <head>
              <title>Task Report</title>
              <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #0891b2; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .priority-high { color: #ef4444; }
                .priority-medium { color: #f59e0b; }
                .priority-low { color: #3b82f6; }
              </style>
            </head>
            <body>
              <h1>Task Report - ${new Date().toLocaleDateString()}</h1>
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Assignee</th>
                    <th>Deadline</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  ${tasks.map(task => `
                    <tr>
                      <td>${task.title}</td>
                      <td>${task.status}</td>
                      <td class="priority-${task.priority}">${task.priority}</td>
                      <td>${task.assignee || 'Unassigned'}</td>
                      <td>${task.deadline ? new Date(task.deadline).toLocaleDateString() : '-'}</td>
                      <td>${Math.round(task.confidence * 100)}%</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </body>
          </html>
        `);
        reportWindow.document.close();
        setTimeout(() => {
          reportWindow.print();
          reportWindow.close();
        }, 500);
      }
      break;
  }
};

const TaskPanel: React.FC<TaskPanelProps> = ({ 
  userId, 
  meetingId, 
  className = '', 
  onTaskClick 
}) => {
  const { isDark } = useTheme();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'pending' | 'completed' | 'all' | 'analytics'>('pending');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showAddParticipant, setShowAddParticipant] = useState(false);
  const [newParticipant, setNewParticipant] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Filter and sort state
  const [filters, setFilters] = useState<FilterOptions>({
    status: [],
    priority: [],
    assignee: [],
    dateRange: {},
    tags: [],
    confidence: { min: 0, max: 1 }
  });
  
  const [sortOptions, setSortOptions] = useState<SortOptions>({
    field: 'created_at',
    direction: 'desc'
  });

  const {
    tasks,
    pendingTasks,
    completedTasks,
    highConfidenceTasks,
    lowConfidenceTasks,
    participants,
    loading,
    error,
    connected,
    updateTask,
    deleteTask,
    addParticipant,
    clearError
  } = useDetectedTasks({ userId, meetingId });

  // Memoized filtered and sorted tasks
  const filteredAndSortedTasks = useMemo(() => {
    let filtered = tasks.filter(task => {
      // Search query filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesSearch = 
          task.title.toLowerCase().includes(query) ||
          task.description?.toLowerCase().includes(query) ||
          task.assignee?.toLowerCase().includes(query) ||
          task.source_text.toLowerCase().includes(query) ||
          task.tags?.some(tag => tag.toLowerCase().includes(query));
        if (!matchesSearch) return false;
      }
      
      // Status filter
      if (filters.status.length > 0 && !filters.status.includes(task.status)) {
        return false;
      }
      
      // Priority filter
      if (filters.priority.length > 0 && !filters.priority.includes(task.priority)) {
        return false;
      }
      
      // Assignee filter
      if (filters.assignee.length > 0) {
        const taskAssignee = task.assignee || 'Unassigned';
        if (!filters.assignee.includes(taskAssignee)) return false;
      }
      
      // Date range filter
      if (filters.dateRange.start || filters.dateRange.end) {
        const taskDate = new Date(task.created_at);
        if (filters.dateRange.start && taskDate < filters.dateRange.start) return false;
        if (filters.dateRange.end && taskDate > filters.dateRange.end) return false;
      }
      
      // Tags filter
      if (filters.tags.length > 0) {
        const taskTags = task.tags || [];
        if (!filters.tags.some(tag => taskTags.includes(tag))) return false;
      }
      
      // Confidence filter
      if (task.confidence < filters.confidence.min || task.confidence > filters.confidence.max) {
        return false;
      }
      
      return true;
    });
    
    // Sort tasks
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (sortOptions.field) {
        case 'created_at':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case 'deadline':
          aValue = a.deadline ? new Date(a.deadline).getTime() : 0;
          bValue = b.deadline ? new Date(b.deadline).getTime() : 0;
          break;
        case 'priority':
          const priorityOrder = { high: 3, medium: 2, low: 1 };
          aValue = priorityOrder[a.priority as keyof typeof priorityOrder];
          bValue = priorityOrder[b.priority as keyof typeof priorityOrder];
          break;
        case 'confidence':
          aValue = a.confidence;
          bValue = b.confidence;
          break;
        case 'title':
          aValue = a.title.toLowerCase();
          bValue = b.title.toLowerCase();
          break;
        default:
          return 0;
      }
      
      if (sortOptions.direction === 'asc') {
        return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
      } else {
        return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
      }
    });
    
    return filtered;
  }, [tasks, searchQuery, filters, sortOptions]);

  // Get display tasks based on active tab
  const getDisplayTasks = () => {
    const filtered = filteredAndSortedTasks;
    switch (activeTab) {
      case 'pending': return filtered.filter(t => t.status === 'pending');
      case 'completed': return filtered.filter(t => t.status === 'done');
      case 'all': return filtered;
      case 'analytics': return filtered;
      default: return filtered;
    }
  };

  // Calculate analytics
  const analytics = useMemo(() => calculateAnalytics(filteredAndSortedTasks), [filteredAndSortedTasks]);

  const handleAddParticipant = async () => {
    if (!newParticipant.trim()) return;
    
    try {
      await addParticipant(newParticipant.trim());
      setNewParticipant('');
      setShowAddParticipant(false);
      toast.success('Participant added');
    } catch (error) {
      // Error is handled by the hook
    }
  };

  const handleExport = (format: 'json' | 'csv' | 'pdf') => {
    exportTasks(getDisplayTasks(), format);
    setShowExportMenu(false);
    toast.success(`Tasks exported as ${format.toUpperCase()}`);
  };

  const handleShare = async () => {
    const shareData = {
      title: 'Meeting Tasks',
      text: `${analytics.totalTasks} tasks detected from meeting`,
      url: window.location.href
    };
    
    if (navigator.share) {
      try {
        await navigator.share(shareData);
        toast.success('Tasks shared');
      } catch (error) {
        // User cancelled sharing
      }
    } else {
      // Fallback: copy to clipboard
      await navigator.clipboard.writeText(window.location.href);
      toast.success('Link copied to clipboard');
    }
  };

  const resetFilters = () => {
    setFilters({
      status: [],
      priority: [],
      assignee: [],
      dateRange: {},
      tags: [],
      confidence: { min: 0, max: 1 }
    });
    setSearchQuery('');
  };

  const displayTasks = getDisplayTasks();
  const hasActiveFilters = searchQuery || 
    filters.status.length > 0 || 
    filters.priority.length > 0 || 
    filters.assignee.length > 0 || 
    filters.tags.length > 0 ||
    filters.confidence.min > 0 || 
    filters.confidence.max < 1 ||
    filters.dateRange.start || 
    filters.dateRange.end;

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-4 border-b ${
        isDark ? 'border-slate-700' : 'border-slate-200'
      }`}>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className={`p-1 rounded transition-colors ${
              isDark ? 'hover:bg-slate-700' : 'hover:bg-slate-100'
            }`}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
          </button>
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
              <Brain size={16} className="text-white" />
            </div>
            <div>
              <h3 className={`font-bold text-sm ${isDark ? 'text-white' : 'text-slate-900'}`}>
                AI Tasks
              </h3>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${
                  connected ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                }`} />
                <span className="text-xs text-slate-500">
                  {connected ? 'Live' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-2 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={`pl-7 pr-3 py-1 text-xs rounded border ${
                isDark 
                  ? 'bg-slate-700 border-slate-600 text-white placeholder-slate-400' 
                  : 'bg-white border-slate-300 text-slate-900 placeholder-slate-500'
              } focus:outline-none focus:ring-2 focus:ring-cyan-500/50`}
            />
          </div>
          
          {/* Filter button */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-1.5 rounded transition-colors relative ${
              isDark ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-100 text-slate-600'
            } ${hasActiveFilters ? 'text-cyan-500' : ''}`}
            title="Filters"
          >
            <Filter size={14} />
            {hasActiveFilters && (
              <div className="absolute -top-1 -right-1 w-2 h-2 bg-cyan-500 rounded-full" />
            )}
          </button>
          
          {/* Export menu */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className={`p-1.5 rounded transition-colors ${
                isDark ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-100 text-slate-600'
              }`}
              title="Export tasks"
            >
              <Download size={14} />
            </button>
            
            <AnimatePresence>
              {showExportMenu && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: -10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: -10 }}
                  className={`absolute right-0 top-full mt-2 w-48 rounded-lg border shadow-lg z-50 ${
                    isDark ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
                  }`}
                >
                  <div className="p-2">
                    <button
                      onClick={() => handleExport('json')}
                      className={`w-full flex items-center space-x-2 px-3 py-2 text-sm rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors ${
                        isDark ? 'text-white' : 'text-slate-900'
                      }`}
                    >
                      <FileText size={16} />
                      <span>Export as JSON</span>
                    </button>
                    <button
                      onClick={() => handleExport('csv')}
                      className={`w-full flex items-center space-x-2 px-3 py-2 text-sm rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors ${
                        isDark ? 'text-white' : 'text-slate-900'
                      }`}
                    >
                      <FileSpreadsheet size={16} />
                      <span>Export as CSV</span>
                    </button>
                    <button
                      onClick={() => handleExport('pdf')}
                      className={`w-full flex items-center space-x-2 px-3 py-2 text-sm rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors ${
                        isDark ? 'text-white' : 'text-slate-900'
                      }`}
                    >
                      <FileImage size={16} />
                      <span>Export as PDF</span>
                    </button>
                    <hr className={`my-2 ${isDark ? 'border-slate-700' : 'border-slate-200'}`} />
                    <button
                      onClick={handleShare}
                      className={`w-full flex items-center space-x-2 px-3 py-2 text-sm rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors ${
                        isDark ? 'text-white' : 'text-slate-900'
                      }`}
                    >
                      <Share2 size={16} />
                      <span>Share Tasks</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          
          <div className="flex items-center space-x-1">
            <span className="text-xs font-mono text-slate-500">
              {displayTasks.length}
            </span>
            <Sparkles size={14} className="text-cyan-500" />
          </div>
        </div>
      </div>

      <AnimatePresence>
        {!isCollapsed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex-1 flex flex-col overflow-hidden"
          >
            {/* Filters Panel */}
            <AnimatePresence>
              {showFilters && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className={`border-b p-4 space-y-3 ${
                    isDark ? 'border-slate-700 bg-slate-800/30' : 'border-slate-200 bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h4 className={`font-medium text-sm ${isDark ? 'text-white' : 'text-slate-900'}`}>
                      Filters & Sorting
                    </h4>
                    <button
                      onClick={resetFilters}
                      className="text-xs text-cyan-500 hover:text-cyan-600 transition"
                    >
                      Reset All
                    </button>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    {/* Status filter */}
                    <div>
                      <label className="text-xs font-medium text-slate-500 mb-1 block">Status</label>
                      <div className="flex flex-wrap gap-1">
                        {['pending', 'in-progress', 'done'].map(status => (
                          <button
                            key={status}
                            onClick={() => {
                              setFilters(f => ({
                                ...f,
                                status: f.status.includes(status) 
                                  ? f.status.filter(s => s !== status)
                                  : [...f.status, status]
                              }));
                            }}
                            className={`text-xs px-2 py-1 rounded border transition ${
                              filters.status.includes(status)
                                ? 'bg-cyan-500 text-white border-cyan-500'
                                : isDark
                                  ? 'bg-slate-700 text-slate-300 border-slate-600 hover:border-slate-500'
                                  : 'bg-white text-slate-700 border-slate-300 hover:border-slate-400'
                            }`}
                          >
                            {status}
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    {/* Priority filter */}
                    <div>
                      <label className="text-xs font-medium text-slate-500 mb-1 block">Priority</label>
                      <div className="flex flex-wrap gap-1">
                        {['low', 'medium', 'high'].map(priority => (
                          <button
                            key={priority}
                            onClick={() => {
                              setFilters(f => ({
                                ...f,
                                priority: f.priority.includes(priority) 
                                  ? f.priority.filter(p => p !== priority)
                                  : [...f.priority, priority]
                              }));
                            }}
                            className={`text-xs px-2 py-1 rounded border transition ${
                              filters.priority.includes(priority)
                                ? 'bg-cyan-500 text-white border-cyan-500'
                                : isDark
                                  ? 'bg-slate-700 text-slate-300 border-slate-600 hover:border-slate-500'
                                  : 'bg-white text-slate-700 border-slate-300 hover:border-slate-400'
                            }`}
                          >
                            {priority}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  {/* Sort options */}
                  <div className="flex items-center space-x-3">
                    <div>
                      <label className="text-xs font-medium text-slate-500 mb-1 block">Sort by</label>
                      <select
                        value={sortOptions.field}
                        onChange={(e) => setSortOptions(s => ({ ...s, field: e.target.value as any }))}
                        className={`text-xs px-2 py-1 rounded border ${
                          isDark 
                            ? 'bg-slate-700 border-slate-600 text-white' 
                            : 'bg-white border-slate-300 text-slate-900'
                        }`}
                      >
                        <option value="created_at">Created Date</option>
                        <option value="deadline">Deadline</option>
                        <option value="priority">Priority</option>
                        <option value="confidence">Confidence</option>
                        <option value="title">Title</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-500 mb-1 block">Direction</label>
                      <button
                        onClick={() => setSortOptions(s => ({ 
                          ...s, 
                          direction: s.direction === 'asc' ? 'desc' : 'asc' 
                        }))}
                        className={`p-1 rounded border transition ${
                          isDark 
                            ? 'bg-slate-700 border-slate-600 text-white hover:bg-slate-600' 
                            : 'bg-white border-slate-300 text-slate-900 hover:bg-slate-50'
                        }`}
                      >
                        {sortOptions.direction === 'asc' ? <SortAsc size={14} /> : <SortDesc size={14} />}
                      </button>
                    </div>
                  </div>
                  
                  {/* Confidence range */}
                  <div>
                    <label className="text-xs font-medium text-slate-500 mb-1 block">
                      Confidence Range: {Math.round(filters.confidence.min * 100)}% - {Math.round(filters.confidence.max * 100)}%
                    </label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={filters.confidence.min}
                        onChange={(e) => setFilters(f => ({ 
                          ...f, 
                          confidence: { ...f.confidence, min: parseFloat(e.target.value) }
                        }))}
                        className="flex-1"
                      />
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={filters.confidence.max}
                        onChange={(e) => setFilters(f => ({ 
                          ...f, 
                          confidence: { ...f.confidence, max: parseFloat(e.target.value) }
                        }))}
                        className="flex-1"
                      />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error display */}
            {error && (
              <div className={`mx-4 mt-4 p-3 rounded-lg border ${
                isDark 
                  ? 'bg-red-500/10 border-red-500/30 text-red-400' 
                  : 'bg-red-50 border-red-200 text-red-700'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <AlertCircle size={16} />
                    <span className="text-sm">{error}</span>
                  </div>
                  <button
                    onClick={clearError}
                    className="text-red-400 hover:text-red-300 transition"
                  >
                    <X size={14} />
                  </button>
                </div>
              </div>
            )}

            {/* Analytics Dashboard */}
            {activeTab === 'analytics' && (
              <div className="p-4 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className={`p-3 rounded-lg ${isDark ? 'bg-slate-800/50' : 'bg-slate-50'}`}>
                    <div className="flex items-center space-x-2 mb-2">
                      <TrendingUp size={16} className="text-emerald-500" />
                      <span className="text-xs font-medium text-slate-500">Completion Rate</span>
                    </div>
                    <div className="text-2xl font-bold text-emerald-500">
                      {Math.round(analytics.completionRate)}%
                    </div>
                  </div>
                  
                  <div className={`p-3 rounded-lg ${isDark ? 'bg-slate-800/50' : 'bg-slate-50'}`}>
                    <div className="flex items-center space-x-2 mb-2">
                      <Star size={16} className="text-amber-500" />
                      <span className="text-xs font-medium text-slate-500">Avg Confidence</span>
                    </div>
                    <div className="text-2xl font-bold text-amber-500">
                      {Math.round(analytics.averageConfidence * 100)}%
                    </div>
                  </div>
                </div>
                
                <div className={`p-3 rounded-lg ${isDark ? 'bg-slate-800/50' : 'bg-slate-50'}`}>
                  <h5 className="text-sm font-medium text-slate-500 mb-2">Tasks by Assignee</h5>
                  <div className="space-y-1">
                    {Object.entries(analytics.tasksByAssignee).map(([assignee, count]) => (
                      <div key={assignee} className="flex items-center justify-between text-xs">
                        <span className={isDark ? 'text-slate-300' : 'text-slate-700'}>{assignee}</span>
                        <span className="font-mono text-slate-500">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className={`p-3 rounded-lg ${isDark ? 'bg-slate-800/50' : 'bg-slate-50'}`}>
                  <h5 className="text-sm font-medium text-slate-500 mb-2">7-Day Trend</h5>
                  <div className="flex items-end space-x-1 h-16">
                    {analytics.trendsData.map((day, idx) => (
                      <div key={idx} className="flex-1 flex flex-col items-center">
                        <div className="flex-1 flex flex-col justify-end space-y-0.5">
                          <div 
                            className="bg-cyan-500 rounded-sm"
                            style={{ height: `${Math.max(4, (day.count / Math.max(...analytics.trendsData.map(d => d.count))) * 40)}px` }}
                          />
                          <div 
                            className="bg-emerald-500 rounded-sm"
                            style={{ height: `${Math.max(2, (day.completed / Math.max(...analytics.trendsData.map(d => d.completed))) * 20)}px` }}
                          />
                        </div>
                        <span className="text-xs text-slate-500 mt-1">
                          {new Date(day.date).getDate()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Stats */}
            {activeTab !== 'analytics' && (
              <div className="p-4 grid grid-cols-3 gap-3">
                {[
                  { label: 'Pending', value: pendingTasks.length, color: 'text-amber-500' },
                  { label: 'High Conf.', value: highConfidenceTasks.length, color: 'text-emerald-500' },
                  { label: 'Completed', value: completedTasks.length, color: 'text-blue-500' },
                ].map((stat, idx) => (
                  <div key={idx} className={`text-center p-2 rounded-lg ${
                    isDark ? 'bg-slate-800/50' : 'bg-slate-50'
                  }`}>
                    <div className={`text-lg font-bold ${stat.color}`}>{stat.value}</div>
                    <div className="text-xs text-slate-500">{stat.label}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Tabs */}
            <div className={`flex mx-4 mb-4 p-1 rounded-lg border ${
              isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-slate-100 border-slate-200'
            }`}>
              {[
                { id: 'pending' as const, label: 'Pending', count: pendingTasks.length, icon: Clock },
                { id: 'completed' as const, label: 'Done', count: completedTasks.length, icon: CheckCircle },
                { id: 'all' as const, label: 'All', count: tasks.length, icon: Target },
                { id: 'analytics' as const, label: 'Analytics', count: 0, icon: BarChart3 },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex items-center justify-center space-x-2 px-3 py-2 rounded-md text-xs font-medium transition ${
                    activeTab === tab.id
                      ? isDark 
                        ? 'bg-slate-700 text-white' 
                        : 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <tab.icon size={12} />
                  <span>{tab.label}</span>
                  {tab.id !== 'analytics' && (
                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                      activeTab === tab.id
                        ? 'bg-cyan-500/20 text-cyan-400'
                        : 'bg-slate-500/20 text-slate-500'
                    }`}>
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Task list */}
            {activeTab !== 'analytics' && (
              <div className="flex-1 overflow-y-auto px-4 pb-4">
                {loading ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-6 w-6 border-2 border-cyan-500 border-t-transparent" />
                  </div>
                ) : displayTasks.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <Target size={32} className="text-slate-400 mb-3" />
                    <p className={`text-sm font-medium ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                      {hasActiveFilters ? 'No tasks match your filters' :
                       activeTab === 'pending' ? 'No pending tasks' : 
                       activeTab === 'completed' ? 'No completed tasks' : 'No tasks detected yet'}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      {hasActiveFilters ? 'Try adjusting your search or filters' : 
                       'Tasks will appear here as they\'re detected from speech'}
                    </p>
                    {hasActiveFilters && (
                      <button
                        onClick={resetFilters}
                        className="mt-2 text-xs text-cyan-500 hover:text-cyan-600 transition"
                      >
                        Clear filters
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <AnimatePresence>
                      {displayTasks.map((task) => (
                        <TaskCard
                          key={task.id}
                          task={task}
                          onUpdate={updateTask}
                          onDelete={deleteTask}
                          onClick={() => onTaskClick?.(task)}
                          showDetails={false}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                )}
              </div>
            )}

            {/* Participants section */}
            <div className={`p-4 border-t ${isDark ? 'border-slate-700' : 'border-slate-200'}`}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <Users size={14} className="text-slate-500" />
                  <span className="text-xs font-medium text-slate-500">
                    Participants ({participants.length})
                  </span>
                </div>
                <button
                  onClick={() => setShowAddParticipant(!showAddParticipant)}
                  className={`p-1 rounded transition-colors ${
                    isDark ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-100 text-slate-600'
                  }`}
                >
                  <Plus size={12} />
                </button>
              </div>

              {showAddParticipant && (
                <div className="flex space-x-2 mb-3">
                  <input
                    type="text"
                    placeholder="Add participant..."
                    value={newParticipant}
                    onChange={(e) => setNewParticipant(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddParticipant()}
                    className={`flex-1 text-xs px-2 py-1 rounded border ${
                      isDark 
                        ? 'bg-slate-700 border-slate-600 text-white placeholder-slate-400' 
                        : 'bg-white border-slate-300 text-slate-900 placeholder-slate-500'
                    }`}
                  />
                  <button
                    onClick={handleAddParticipant}
                    className="px-3 py-1 bg-cyan-500 hover:bg-cyan-600 text-white text-xs rounded transition"
                  >
                    Add
                  </button>
                </div>
              )}

              <div className="flex flex-wrap gap-1">
                {participants.map((participant, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      const assigneeFilter = participant;
                      setFilters(f => ({
                        ...f,
                        assignee: f.assignee.includes(assigneeFilter) 
                          ? f.assignee.filter(a => a !== assigneeFilter)
                          : [...f.assignee, assigneeFilter]
                      }));
                    }}
                    className={`text-xs px-2 py-1 rounded-full transition ${
                      filters.assignee.includes(participant)
                        ? 'bg-cyan-500 text-white'
                        : isDark 
                          ? 'bg-slate-700 text-slate-300 hover:bg-slate-600' 
                          : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                    }`}
                  >
                    {participant}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default TaskPanel;