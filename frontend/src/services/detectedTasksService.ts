/**
 * services/detectedTasksService.ts
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 * Service for managing AI-detected tasks from voice commands.
 */

import { detectedTasksApi, type DetectedTask, type DetectedTaskUpdate } from '../lib/api';

export type { DetectedTask, DetectedTaskUpdate } from '../lib/api';

export interface TaskDetectionRequest {
  text: string;
  context?: string[];
  meeting_id?: string;
}

class DetectedTasksService {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<Function>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  // REST API methods
  async list(status?: string, assignee?: string, limit = 50): Promise<DetectedTask[]> {
    return detectedTasksApi.list({ status, assignee, limit });
  }

  async get(taskId: string): Promise<DetectedTask> {
    return detectedTasksApi.get(taskId);
  }

  async update(taskId: string, updateData: DetectedTaskUpdate): Promise<DetectedTask> {
    return detectedTasksApi.update(taskId, updateData);
  }

  async delete(taskId: string): Promise<void> {
    await detectedTasksApi.delete(taskId);
  }

  async detectTasks(request: TaskDetectionRequest): Promise<DetectedTask[]> {
    return detectedTasksApi.detect(request.text, request.context, request.meeting_id);
  }

  async getParticipants(): Promise<string[]> {
    const data = await detectedTasksApi.getParticipants();
    return data.participants;
  }

  async addParticipant(name: string): Promise<void> {
    await detectedTasksApi.addParticipant(name);
  }

  // WebSocket methods
  connect(userId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/detected-tasks/ws`;
      
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[DetectedTasks] WebSocket connected');
        this.reconnectAttempts = 0;
        
        // Authenticate
        this.ws!.send(JSON.stringify({
          type: 'auth',
          user_id: userId
        }));
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'auth_success') {
            console.log('[DetectedTasks] WebSocket authenticated');
            resolve();
          } else if (data.type === 'auth_error') {
            console.error('[DetectedTasks] WebSocket auth failed:', data.message);
            reject(new Error(data.message));
          } else {
            this.handleMessage(data);
          }
        } catch (error) {
          console.error('[DetectedTasks] Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('[DetectedTasks] WebSocket disconnected');
        this.ws = null;
        this.attemptReconnect(userId);
      };

      this.ws.onerror = (error) => {
        console.error('[DetectedTasks] WebSocket error:', error);
        reject(error);
      };
    });
  }

  private attemptReconnect(userId: string) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[DetectedTasks] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`[DetectedTasks] Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect(userId).catch(console.error);
    }, delay);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.listeners.clear();
  }

  sendTaskDetection(text: string, context?: string[], meetingId?: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[DetectedTasks] WebSocket not connected, cannot send task detection');
      return;
    }

    this.ws.send(JSON.stringify({
      type: 'detect_tasks',
      text,
      context,
      meeting_id: meetingId
    }));
  }

  // 🚨 NEW: Send transcript chunk for buffered processing
  sendTranscriptChunk(chunk: string, meetingId?: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[DetectedTasks] WebSocket not connected, cannot send chunk');
      return;
    }

    console.log('[DetectedTasks] 🚀 Sending chunk for buffered processing:', chunk);
    this.ws.send(JSON.stringify({
      type: 'process_chunk',
      chunk,
      meeting_id: meetingId
    }));
  }

  // 🚨 NEW: Flush buffer when transcription ends
  flushBuffer(meetingId?: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[DetectedTasks] WebSocket not connected, cannot flush buffer');
      return;
    }

    console.log('[DetectedTasks] 🔄 Flushing buffer');
    this.ws.send(JSON.stringify({
      type: 'flush_buffer',
      meeting_id: meetingId
    }));
  }

  // Event handling
  on(event: string, callback: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  off(event: string, callback: Function) {
    if (this.listeners.has(event)) {
      this.listeners.get(event)!.delete(callback);
    }
  }

  private handleMessage(data: any) {
    const { type } = data;
    
    if (this.listeners.has(type)) {
      this.listeners.get(type)!.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`[DetectedTasks] Error in ${type} callback:`, error);
        }
      });
    }

    // Also emit to 'message' listeners for generic handling
    if (this.listeners.has('message')) {
      this.listeners.get('message')!.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('[DetectedTasks] Error in message callback:', error);
        }
      });
    }
  }
}

export const detectedTasksService = new DetectedTasksService();