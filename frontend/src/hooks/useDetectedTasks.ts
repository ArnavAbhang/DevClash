/**
 * hooks/useDetectedTasks.ts
 * ~~~~~~~~~~~~~~~~~~~~~~~~~
 * React hook for managing AI-detected tasks from voice commands.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { detectedTasksService, DetectedTask, DetectedTaskUpdate } from '../services/detectedTasksService';

interface UseDetectedTasksOptions {
  autoConnect?: boolean;
  userId?: string;
  meetingId?: string;
}

export function useDetectedTasks(options: UseDetectedTasksOptions = {}) {
  const { autoConnect = true, userId, meetingId } = options;
  
  const [tasks, setTasks] = useState<DetectedTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [participants, setParticipants] = useState<string[]>([]);
  
  const conversationHistoryRef = useRef<string[]>([]);
  const isConnectingRef = useRef(false);

  // Load initial tasks
  const loadTasks = useCallback(async (status?: string, assignee?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const taskList = await detectedTasksService.list(status, assignee);
      setTasks(taskList);
    } catch (err: any) {
      setError(err.message || 'Failed to load tasks');
      console.error('Failed to load detected tasks:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load participants
  const loadParticipants = useCallback(async () => {
    try {
      const participantList = await detectedTasksService.getParticipants();
      setParticipants(participantList);
    } catch (err: any) {
      console.error('Failed to load participants:', err);
    }
  }, []);

  // Update task
  const updateTask = useCallback(async (taskId: string, updateData: DetectedTaskUpdate) => {
    try {
      const updatedTask = await detectedTasksService.update(taskId, updateData);
      setTasks(prev => prev.map(task => task.id === taskId ? updatedTask : task));
      return updatedTask;
    } catch (err: any) {
      setError(err.message || 'Failed to update task');
      throw err;
    }
  }, []);

  // Delete task
  const deleteTask = useCallback(async (taskId: string) => {
    try {
      await detectedTasksService.delete(taskId);
      setTasks(prev => prev.filter(task => task.id !== taskId));
    } catch (err: any) {
      setError(err.message || 'Failed to delete task');
      throw err;
    }
  }, []);

  // Add participant
  const addParticipant = useCallback(async (name: string) => {
    try {
      await detectedTasksService.addParticipant(name);
      await loadParticipants(); // Reload the list
    } catch (err: any) {
      setError(err.message || 'Failed to add participant');
      throw err;
    }
  }, [loadParticipants]);

  // Detect tasks from text
  const detectTasks = useCallback(async (text: string, context?: string[]) => {
    try {
      const detectedTasks = await detectedTasksService.detectTasks({
        text,
        context: context || conversationHistoryRef.current.slice(-5), // Last 5 messages for context
        meeting_id: meetingId
      });
      
      // Add to local state (they should also come via WebSocket)
      setTasks(prev => [...detectedTasks, ...prev]);
      return detectedTasks;
    } catch (err: any) {
      setError(err.message || 'Failed to detect tasks');
      throw err;
    }
  }, [meetingId]);

  // Send task detection via WebSocket (for real-time processing)
  const sendTaskDetection = useCallback((text: string, context?: string[]) => {
    if (!connected) {
      console.warn('WebSocket not connected, cannot send task detection');
      return;
    }
    
    detectedTasksService.sendTaskDetection(
      text, 
      context || conversationHistoryRef.current.slice(-5),
      meetingId
    );
  }, [connected, meetingId]);

  // Add to conversation history (for context)
  const addToConversation = useCallback((text: string) => {
    conversationHistoryRef.current.push(text);
    // Keep only last 10 messages for context
    if (conversationHistoryRef.current.length > 10) {
      conversationHistoryRef.current = conversationHistoryRef.current.slice(-10);
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(async () => {
    if (!userId || isConnectingRef.current || connected) {
      return;
    }

    isConnectingRef.current = true;
    setError(null);

    try {
      await detectedTasksService.connect(userId);
      setConnected(true);
      
      // Set up event listeners
      detectedTasksService.on('new_task', (data: any) => {
        console.log('New task detected:', data.task);
        setTasks(prev => {
          // Avoid duplicates
          const exists = prev.some(task => task.id === data.task.id);
          if (exists) return prev;
          return [data.task, ...prev];
        });
      });

      detectedTasksService.on('task_updated', (data: any) => {
        console.log('Task updated:', data.task);
        setTasks(prev => prev.map(task => task.id === data.task.id ? data.task : task));
      });

      detectedTasksService.on('task_deleted', (data: any) => {
        console.log('Task deleted:', data.task_id);
        setTasks(prev => prev.filter(task => task.id !== data.task_id));
      });

      detectedTasksService.on('error', (data: any) => {
        console.error('WebSocket error:', data.message);
        setError(data.message);
      });

    } catch (err: any) {
      setError(err.message || 'Failed to connect to task detection service');
      console.error('Failed to connect to detected tasks WebSocket:', err);
    } finally {
      isConnectingRef.current = false;
    }
  }, [userId, connected]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    detectedTasksService.disconnect();
    setConnected(false);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && userId && !connected && !isConnectingRef.current) {
      connect();
    }

    return () => {
      if (connected) {
        disconnect();
      }
    };
  }, [autoConnect, userId, connected, connect, disconnect]);

  // Load initial data
  useEffect(() => {
    loadTasks();
    loadParticipants();
  }, [loadTasks, loadParticipants]);

  // Computed values
  const pendingTasks = tasks.filter(task => task.status === 'pending');
  const inProgressTasks = tasks.filter(task => task.status === 'in-progress');
  const completedTasks = tasks.filter(task => task.status === 'done');
  const highConfidenceTasks = tasks.filter(task => task.confidence >= 0.8);
  const lowConfidenceTasks = tasks.filter(task => task.confidence < 0.7);

  return {
    // State
    tasks,
    pendingTasks,
    inProgressTasks,
    completedTasks,
    highConfidenceTasks,
    lowConfidenceTasks,
    participants,
    loading,
    error,
    connected,
    
    // Actions
    loadTasks,
    updateTask,
    deleteTask,
    detectTasks,
    sendTaskDetection,
    addToConversation,
    addParticipant,
    connect,
    disconnect,
    
    // Utilities
    clearError: () => setError(null),
  };
}