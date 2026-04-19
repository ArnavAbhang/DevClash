/**
 * api.ts
 * ──────
 * Thin fetch wrapper that:
 *  - Reads VITE_API_BASE_URL from the Vite env (dev: http://localhost:8000/api, prod: /api)
 *  - Attaches the JWT Bearer token from localStorage on every request
 *  - Redirects to "/" on 401 (token expired / invalid)
 *  - Returns parsed JSON or throws an Error with the backend's detail message
 */

const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

function getToken(): string | null {
  return localStorage.getItem('token');
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  customHeaders?: Record<string, string>,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: authHeaders(customHeaders),
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
    throw new Error('Session expired. Please log in again.');
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((e: any) => e.msg).join(', ')
          : 'Request failed',
    );
  }
  return data as T;
}

// ── Typed API surface ─────────────────────────────────────────────────────────

export interface UserInfo {
  id: string;
  name: string;
  email: string;
}

export interface TaskItem {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in-progress' | 'done';
  priority: 'low' | 'medium' | 'high';
  user: string;
  created_at: string;
  updated_at: string;
}

export interface TaskCreatePayload {
  title: string;
  description?: string;
  status?: TaskItem['status'];
  priority?: TaskItem['priority'];
}

export interface TaskUpdatePayload {
  title?: string;
  description?: string;
  status?: TaskItem['status'];
  priority?: TaskItem['priority'];
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  me: () =>
    request<{ success: boolean; data: { user: UserInfo } }>('GET', '/auth/me'),
};

// ── Tasks ─────────────────────────────────────────────────────────────────────

export const tasksApi = {
  list: (params?: { status?: string; priority?: string }) => {
    const qs = params
      ? '?' + new URLSearchParams(
          Object.fromEntries(
            Object.entries(params).filter(([, v]) => v !== undefined && v !== ''),
          ) as Record<string, string>,
        ).toString()
      : '';
    return request<{ success: boolean; count: number; data: TaskItem[] }>('GET', `/tasks${qs}`);
  },

  create: (payload: TaskCreatePayload) =>
    request<{ success: boolean; message: string; data: TaskItem }>('POST', '/tasks', payload),

  update: (id: string, payload: TaskUpdatePayload) =>
    request<{ success: boolean; message: string; data: TaskItem }>('PUT', `/tasks/${id}`, payload),

  delete: (id: string) =>
    request<{ success: boolean; message: string }>('DELETE', `/tasks/${id}`),
};

// ── AI ────────────────────────────────────────────────────────────────────────

export const aiApi = {
  summarize: (text: string) =>
    request<{ summary: string }>('POST', '/summarize', { text }),

  transcribe: async (audioBlob: Blob, conversationHistory?: string): Promise<{ transcription: string }> => {
    const token = getToken();
    const formData = new FormData();

    // Derive a filename whose extension matches the blob MIME type so the
    // backend receives the correct Content-Type on the multipart field.
    const extMap: Record<string, string> = {
      'audio/mp4': 'recording.mp4',
      'audio/mpeg': 'recording.mp3',
      'audio/wav': 'recording.wav',
      'audio/ogg': 'recording.ogg',
      'audio/webm': 'recording.webm',
    };
    const filename = extMap[audioBlob.type] ?? 'recording.webm';
    formData.append('audio', audioBlob, filename);

    // Pass full conversation history to detect repeated phrases
    if (conversationHistory) {
      formData.append('conversation_history', conversationHistory);
    }

    // NOTE: Do NOT set Content-Type manually — the browser sets it with the
    // correct multipart boundary when you pass FormData.
    const res = await fetch(`${BASE}/transcribe`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (res.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/';
      throw new Error('Session expired.');
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(
        typeof data.detail === 'string' ? data.detail : 'Transcription failed',
      );
    }
    return data as { transcription: string };
  },
};
