import { useState, useEffect, useRef, useCallback, FormEvent } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Calendar, CheckSquare, FileText,
  Settings, Bell,
  ChevronRight, TrendingDown, Clock,
  CheckCircle, Circle,
  Filter, ArrowUpRight,
  Home, MonitorUp,
  Camera, Video, Square, Download, Trash2,
  X, Image as ImageIcon, Zap, Mic, MicOff, ScreenShare, Copy, AlertCircle,
  Plus, Loader2,
} from 'lucide-react';

import AnimatedSearch from '../components/AnimatedSearch';
import AnimatedCheckbox from '../components/AnimatedCheckbox';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../components/ToastSystem';
import { tasksApi, aiApi, type TaskItem, type TaskCreatePayload } from '../lib/api';

// ─────────────────────────────────────────
// DATA
// ─────────────────────────────────────────
const MEETINGS: any[] = [];

const NAV_ITEMS = [
  { id: 'overview', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'meetings', label: 'Meetings', icon: Calendar },
  { id: 'tasks', label: 'Tasks', icon: CheckSquare },
  { id: 'transcript', label: 'Transcript', icon: FileText },
];

// Speaker color map
const SPEAKER_COLORS: { [key: string]: { dot: string; text: string } } = {
  'Speaker 1': { dot: 'bg-cyan-500', text: 'text-cyan-500' },
  'Speaker 2': { dot: 'bg-violet-500', text: 'text-violet-500' },
  'Speaker 3': { dot: 'bg-amber-500', text: 'text-amber-500' },
};

// ─────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────
interface Recording {
  id: number;
  url: string;
  name: string;
  duration: string;
  timestamp: string;
  size: string;
}

interface Screenshot {
  id: number;
  url: string;
  name: string;
  timestamp: string;
}

interface TranscriptLine {
  id: string;
  timestamp: string;
  speaker: string;
  text: string;
  confidence: number;
  simulated?: boolean;
}

// ─────────────────────────────────────────
// STAT CARD
// ─────────────────────────────────────────
function StatCard({ stat, index }: { stat: any; index: number; key?: any }) {
  const { isDark } = useTheme();
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }} 
      animate={{ opacity: 1, y: 0 }} 
      transition={{ delay: index * 0.08 }} 
      className={`border rounded-2xl p-6 transition-all ${
        isDark ? 'bg-bg-secondary border-white/10 hover:border-white/20' : 'bg-white border-border-main shadow-sm hover:shadow-md'
      }`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className={`w-12 h-12 bg-gradient-to-br ${stat.color} rounded-xl flex items-center justify-center shadow-lg`}>
          <stat.icon className="text-white" size={22} />
        </div>
        <div className={`flex items-center space-x-1 text-sm font-medium transition-colors ${stat.up ? 'text-emerald-500' : 'text-rose-500'}`}>
          {stat.up ? <TrendingDown size={14} /> : <TrendingDown size={14} />}
          <span>{stat.trend}</span>
        </div>
      </div>
      <div className={`text-3xl font-bold mb-1 transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>{stat.value}</div>
      <div className="text-sm text-slate-500">{stat.label}</div>
    </motion.div>
  );
}

function MeetingRow({ meeting, index }: { meeting: any; index: number; key?: any }) {
  const { isDark } = useTheme();
  const effColor = meeting.efficiency >= 80 ? 'text-emerald-500' : meeting.efficiency >= 60 ? 'text-amber-500' : 'text-rose-500';
  return (
    <motion.div 
      initial={{ opacity: 0, x: -10 }} 
      animate={{ opacity: 1, x: 0 }} 
      transition={{ delay: index * 0.06 }} 
      className={`flex items-center space-x-4 p-4 rounded-xl border border-transparent transition-all cursor-pointer group ${
        isDark ? 'hover:bg-white/5 hover:border-white/10' : 'hover:bg-slate-50 hover:border-slate-200 shadow-sm hover:shadow-md'
      }`}
    >
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors ${
        isDark ? 'bg-white/5 group-hover:bg-app-primary/20' : 'bg-slate-100 group-hover:bg-indigo-50 text-indigo-600'
      }`}>
        <FileText className="text-app-primary" size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2 mb-0.5">
          <p className={`font-medium truncate transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>{meeting.title}</p>
          <div className="flex space-x-1">
            {meeting.tags.map((tag: string, i: number) => (
              <span key={i} className={`text-[10px] px-1.5 py-0.5 rounded-md uppercase font-bold transition-colors ${
                isDark ? 'bg-white/10 text-slate-500' : 'bg-slate-200 text-slate-600'
              }`}>{tag}</span>
            ))}
          </div>
        </div>
        <div className="flex items-center space-x-3 text-xs text-slate-500">
          <span>{meeting.date}</span>
          <span>•</span>
          <span>{meeting.duration}</span>
        </div>
      </div>
      <div className="hidden md:flex items-center space-x-6 text-xs font-mono">
        <div className="text-right">
          <div className={`transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>{meeting.completedTasks}/{meeting.tasks}</div>
          <div className="text-slate-500 uppercase text-[9px]">Tasks</div>
        </div>
        <div className="text-right">
          <div className={effColor}>{meeting.efficiency}%</div>
          <div className="text-slate-500 uppercase text-[9px]">Perf</div>
        </div>
      </div>
      <ChevronRight className="text-slate-400 group-hover:text-app-primary transition-colors" size={16} />
    </motion.div>
  );
}

// ─────────────────────────────────────────
// ANIMATED WAVEFORM COMPONENT
// ─────────────────────────────────────────
function AnimatedWaveform() {
  return (
    <svg className="w-24 h-24" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <style>{`
        @keyframes wave {
          0%, 100% { height: 15px; }
          50% { height: 35px; }
        }
        .wave-bar {
          animation: wave 1s ease-in-out infinite;
        }
        .bar-1 { animation-delay: 0s; }
        .bar-2 { animation-delay: 0.1s; }
        .bar-3 { animation-delay: 0.2s; }
        .bar-4 { animation-delay: 0.1s; }
        .bar-5 { animation-delay: 0s; }
      `}</style>
      <rect className="wave-bar bar-1" x="15" y="42.5" width="8" height="15" fill="#0EA5E9" rx="2" />
      <rect className="wave-bar bar-2" x="30" y="32.5" width="8" height="35" fill="#22D3EE" rx="2" />
      <rect className="wave-bar bar-3" x="45" y="32.5" width="8" height="35" fill="#0EA5E9" rx="2" />
      <rect className="wave-bar bar-4" x="60" y="32.5" width="8" height="35" fill="#22D3EE" rx="2" />
      <rect className="wave-bar bar-5" x="75" y="42.5" width="8" height="15" fill="#0EA5E9" rx="2" />
    </svg>
  );
}

// ─────────────────────────────────────────
// MAIN DASHBOARD
// ─────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const toast = useToast();
  const [activeSection, setActiveSection] = useState('overview');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // ── Auth guard + user info ──
  const storedUser = (() => {
    try { return JSON.parse(localStorage.getItem('user') ?? 'null'); } catch { return null; }
  })();
  const currentUser = storedUser as { id: string; name: string; email: string } | null;

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      navigate('/');
    }
  }, [navigate]);

  // ── Tasks state (real API) ──
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [tasksError, setTasksError] = useState('');

  // Task modal state
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<TaskItem | null>(null);
  const [taskForm, setTaskForm] = useState<TaskCreatePayload>({
    title: '', description: '', status: 'todo', priority: 'medium',
  });
  const [taskSubmitting, setTaskSubmitting] = useState(false);

  // ── Screen Capture State ──
  const [isRecording, setIsRecording] = useState(false);
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [screenshots, setScreenshots] = useState<Screenshot[]>([]);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [captureTab, setCaptureTab] = useState<'recordings' | 'screenshots'>('recordings');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewType, setPreviewType] = useState<'video' | 'image'>('video');
  const [isPendingScreenshot, setIsPendingScreenshot] = useState(false);
  const screenshotStreamRef = useRef<MediaStream | null>(null);

  // ── Transcript State ──
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptLines, setTranscriptLines] = useState<TranscriptLine[]>([]);
  const [elapsedAudioTime, setElapsedAudioTime] = useState(0);
  const [transcriptStatus, setTranscriptStatus] = useState<'idle' | 'listening' | 'processing'>('idle');
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [recordedAudioName, setRecordedAudioName] = useState<string>('');
  const [voiceDetected, setVoiceDetected] = useState(false);
  // AI summary state
  const [aiSummary, setAiSummary] = useState<string>('');
  const [summaryLoading, setSummaryLoading] = useState(false);

  const transcriptContainerRef = useRef<HTMLDivElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const transcriptionRecorderRef = useRef<MediaRecorder | null>(null);
  const transcriptionStreamRef = useRef<MediaStream | null>(null);
  const audioTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioStartTimeRef = useRef<number>(0);
  const transcriptionQueueRef = useRef<Promise<void>>(Promise.resolve());
  const transcriptionChunksRef = useRef<Blob[]>([]);
  const transcriptionTextRef = useRef<string>('');
  const isTranscribingRef = useRef<boolean>(false);
  const voiceActivityRef = useRef<boolean>(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  // ── Fetch tasks on mount ──
  useEffect(() => {
    const load = async () => {
      setTasksLoading(true);
      setTasksError('');
      try {
        const res = await tasksApi.list();
        setTasks(res.data);
      } catch (err: any) {
        setTasksError(err.message ?? 'Failed to load tasks');
      } finally {
        setTasksLoading(false);
      }
    };
    if (localStorage.getItem('token')) load();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      toast.ai('Welcome to MeetNova AI. Share your screen to start capturing meeting intelligence.', {
        title: 'MeetNova AI',
        duration: 6000
      });
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  // Auto-scroll transcript to bottom
  useEffect(() => {
    if (transcriptContainerRef.current) {
      transcriptContainerRef.current.scrollTop = transcriptContainerRef.current.scrollHeight;
    }
  }, [transcriptLines]);

  // ── Helpers ──
  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) return `${hrs}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // ── Screen Record ──
  const startRecording = useCallback(async () => {
    try {
      // Get screen stream
      const screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: { width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30 } },
        audio: true // Capture system audio if available
      });

      // Get mic stream
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Combine streams
      const combinedStream = new MediaStream([
        ...screenStream.getVideoTracks(),
        ...screenStream.getAudioTracks(),
        ...micStream.getAudioTracks()
      ]);

      streamRef.current = combinedStream;
      chunksRef.current = [];

      const mediaRecorder = new MediaRecorder(combinedStream, {
        mimeType: MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' : 'video/webm'
      });

      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        const now = new Date();
        const duration = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setRecordings(prev => [{
          id: Date.now(), url,
          name: `Recording_${now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}_${now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`,
          duration: formatTime(duration),
          timestamp: now.toLocaleString(),
          size: formatFileSize(blob.size)
        }, ...prev]);
        toast.success('Recording saved successfully!');
      };

      screenStream.getVideoTracks()[0].onended = () => stopRecording();

      mediaRecorder.start(1000);
      mediaRecorderRef.current = mediaRecorder;
      startTimeRef.current = Date.now();
      setIsRecording(true);
      setElapsedTime(0);
      timerRef.current = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);
    } catch (err) {
      console.error('Screen recording failed:', err);
      toast.error('Failed to start screen recording. Please check permissions.');
    }
  }, [toast]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') mediaRecorderRef.current.stop();
    if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setIsRecording(false);
    setElapsedTime(0);
  }, []);

  // ── Screenshot ──
  const startScreenshotSession = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: { width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
      
      stream.getVideoTracks()[0].onended = () => {
        screenshotStreamRef.current = null;
        setIsPendingScreenshot(false);
      };
      
      screenshotStreamRef.current = stream;
      setIsPendingScreenshot(true);
      toast.info('Screen selected. Click "Capture Now" when ready.');
    } catch (err) {
      console.error('Screenshot selection failed:', err);
    }
  }, []);

  const confirmScreenshot = useCallback(async () => {
    if (!screenshotStreamRef.current) return;
    try {
      const track = screenshotStreamRef.current.getVideoTracks()[0];
      let url = '';
      let needsFallback = false;

      // 1. Try ImageCapture API (Chrome/Edge Native)
      if (typeof (window as any).ImageCapture !== 'undefined') {
        try {
          const imageCapture = new (window as any).ImageCapture(track);
          const bitmap = await imageCapture.grabFrame();

          const canvas = document.createElement('canvas');
          canvas.width = bitmap.width;
          canvas.height = bitmap.height;
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.drawImage(bitmap, 0, 0);
            url = canvas.toDataURL('image/png');
          }
        } catch (imageCaptureError) {
          console.warn('ImageCapture failed (normal for screen tracks). Falling back to video engine...', imageCaptureError);
          needsFallback = true;
        }
      } else {
        needsFallback = true;
      }

      // 2. Fallback to Video Element rendering (Firefox/Safari/Screen restrictions)
      if (needsFallback) {
        const video = document.createElement('video');
        video.autoplay = true;
        video.playsInline = true;
        video.muted = true;
        video.srcObject = screenshotStreamRef.current;
        
        video.style.display = 'none';
        video.style.width = '1920px';
        video.style.height = '1080px';
        document.body.appendChild(video);

        try {
          await new Promise<void>((resolve) => {
            let resolved = false;
            const cleanup = () => {
              if (!resolved) {
                resolved = true;
                if (video.parentElement) {
                  document.body.removeChild(video);
                }
                resolve();
              }
            };
            
            video.onloadedmetadata = () => {
              video.play()
                .then(() => {
                  setTimeout(cleanup, 100);
                })
                .catch(cleanup);
            };
            
            setTimeout(cleanup, 2000);
          });

          const canvas = document.createElement('canvas');
          const width = video.videoWidth > 0 ? video.videoWidth : 1920;
          const height = video.videoHeight > 0 ? video.videoHeight : 1080;
          canvas.width = width;
          canvas.height = height;
          
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.fillStyle = '#000';
            ctx.fillRect(0, 0, width, height);
            ctx.drawImage(video, 0, 0);
            url = canvas.toDataURL('image/png');
          }
        } finally {
          if (video.parentElement) {
            document.body.removeChild(video);
          }
        }
      }

      track.stop();
      screenshotStreamRef.current.getTracks().forEach(t => t.stop());
      screenshotStreamRef.current = null;
      setIsPendingScreenshot(false);

      if (url) {
        const now = new Date();
        setScreenshots(prev => [{
          id: Date.now(), url,
          name: `Screenshot_${now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}_${now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`,
          timestamp: now.toLocaleString()
        }, ...prev]);
        toast.success('Screenshot captured!');
      }

    } catch (err) {
      console.error('Antigravity Capture Error:', err);
      toast.error('Failed to grab frame from stream.');
      if (screenshotStreamRef.current) {
        screenshotStreamRef.current.getTracks().forEach(t => t.stop());
        screenshotStreamRef.current = null;
        setIsPendingScreenshot(false);
      }
    }
  }, [toast]);

  const cancelScreenshot = useCallback(() => {
    if (screenshotStreamRef.current) {
      screenshotStreamRef.current.getTracks().forEach(t => t.stop());
      screenshotStreamRef.current = null;
    }
    setIsPendingScreenshot(false);
  }, []);

  const downloadFile = (url: string, name: string, ext: string) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const deleteRecording = (id: number) => {
    setRecordings(prev => {
      const r = prev.find(x => x.id === id);
      if (r) URL.revokeObjectURL(r.url);
      return prev.filter(x => x.id !== id);
    });
  };

  const transcribeRecording = useCallback(async (recording: Recording) => {
    try {
      // Fetch the blob from URL
      const response = await fetch(recording.url);
      const blob = await response.blob();

      // When recording a screen capture, the blob may be video/webm.
      // Convert it to an audio-typed blob so the backend ASR can accept it.
      const audioBlob = new Blob([blob], { type: 'audio/webm' });

      setTranscriptStatus('processing');
      const result = await aiApi.transcribe(audioBlob);
      const transcription = result.transcription;

      if (transcription.trim()) {
        const line: TranscriptLine = {
          id: String(Date.now()),
          timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          speaker: 'Recording',
          text: transcription,
          confidence: 0.95,
        };
        setTranscriptLines(prev => [...prev, line]);
        toast.success('Recording transcribed successfully!');
      } else {
        toast.info('No speech detected in the recording.');
      }
    } catch (err: any) {
      toast.error(`Transcription failed: ${err.message}`);
    } finally {
      setTranscriptStatus('idle');
    }
  }, [toast]);

  const deleteScreenshot = (id: number) => {
    setScreenshots(prev => {
      const s = prev.find(x => x.id === id);
      if (s) URL.revokeObjectURL(s.url);
      return prev.filter(x => x.id !== id);
    });
  };

  const toggleTask = async (id: string) => {
    const task = tasks.find(t => t.id === id);
    if (!task) return;
    const newStatus = task.status === 'done' ? 'todo' : 'done';
    // Optimistic update
    setTasks(prev => prev.map(t => t.id === id ? { ...t, status: newStatus } : t));
    try {
      const res = await tasksApi.update(id, { status: newStatus });
      setTasks(prev => prev.map(t => t.id === id ? res.data : t));
      if (newStatus === 'done') toast.success(`Task completed: ${task.title}`, { duration: 3000 });
    } catch (err: any) {
      // Revert on failure
      setTasks(prev => prev.map(t => t.id === id ? task : t));
      toast.error(err.message ?? 'Failed to update task');
    }
  };

  const handleDeleteTask = async (id: string) => {
    const task = tasks.find(t => t.id === id);
    if (!task) return;
    setTasks(prev => prev.filter(t => t.id !== id));
    try {
      await tasksApi.delete(id);
      toast.success('Task deleted');
    } catch (err: any) {
      setTasks(prev => [task, ...prev]);
      toast.error(err.message ?? 'Failed to delete task');
    }
  };

  const openCreateTask = () => {
    setEditingTask(null);
    setTaskForm({ title: '', description: '', status: 'todo', priority: 'medium' });
    setTaskModalOpen(true);
  };

  const openEditTask = (task: TaskItem) => {
    setEditingTask(task);
    setTaskForm({ title: task.title, description: task.description, status: task.status, priority: task.priority });
    setTaskModalOpen(true);
  };

  const handleTaskSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setTaskSubmitting(true);
    try {
      if (editingTask) {
        const res = await tasksApi.update(editingTask.id, taskForm);
        setTasks(prev => prev.map(t => t.id === editingTask.id ? res.data : t));
        toast.success('Task updated');
      } else {
        const res = await tasksApi.create(taskForm);
        setTasks(prev => [res.data, ...prev]);
        toast.success('Task created');
      }
      setTaskModalOpen(false);
    } catch (err: any) {
      toast.error(err.message ?? 'Failed to save task');
    } finally {
      setTaskSubmitting(false);
    }
  };

  // ── Transcript Functions ──
  const createMixedAudioStream = useCallback(async () => {
    const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) {
      throw new Error('AudioContext is not supported in this browser.');
    }

    const displayStream = await navigator.mediaDevices.getDisplayMedia({ audio: true, video: true });
    const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const audioContext = new AudioContextClass();
    await audioContext.resume(); // Ensure AudioContext is running
    audioContextRef.current = audioContext;
    const destination = audioContext.createMediaStreamDestination();

    const displayAudioTracks = displayStream.getAudioTracks();
    if (displayAudioTracks.length > 0) {
      const displaySource = audioContext.createMediaStreamSource(new MediaStream(displayAudioTracks));
      const displayGain = audioContext.createGain();
      displayGain.gain.value = 1.5; // Boost display audio volume
      displaySource.connect(displayGain);
      displayGain.connect(destination);
    }

    const micAudioTracks = micStream.getAudioTracks();
    if (micAudioTracks.length > 0) {
      const micSource = audioContext.createMediaStreamSource(new MediaStream(micAudioTracks));
      const micGain = audioContext.createGain();
      micGain.gain.value = 1;
      micSource.connect(micGain);
      micGain.connect(destination);
    }

    return { mixedStream: destination.stream, displayStream, micStream };
  }, []);

  const processAudioChunk = useCallback(async (chunk: Blob) => {
    if (!isTranscribingRef.current) return;
    setTranscriptStatus('processing');
    console.log(`[DEBUG] Processing chunk, size: ${chunk.size} bytes`);

    try {
      // Pass the full conversation history to detect repeated phrases
      const conversationHistory = transcriptionTextRef.current;
      const result = await aiApi.transcribe(chunk, conversationHistory);
      console.log('[DEBUG] API response:', result);
      
      const transcription = result.transcription.trim();
      if (!transcription) {
        console.log('[DEBUG] Empty transcription (filtered or no speech)');
        return;
      }

      console.log(`[DEBUG] New transcription: '${transcription}'`);
      
      // Simple append — backend already filtered out repetitions
      transcriptionTextRef.current = transcriptionTextRef.current
        ? `${transcriptionTextRef.current} ${transcription}`
        : transcription;

      const line: TranscriptLine = {
        id: String(Date.now()),
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        speaker: 'Live',
        text: transcription,
        confidence: 0.95,
      };
      setTranscriptLines(prev => [...prev, line]);
    } catch (err: any) {
      console.error('[ERROR] Realtime transcription failed:', err);
      toast.error(`Realtime transcription failed: ${err.message}`);
    } finally {
      setTranscriptStatus(isTranscribingRef.current ? 'listening' : 'idle');
    }
  }, [toast]);

  const generateSummary = useCallback(async () => {
    if (!transcriptionTextRef.current.trim()) return;
    setSummaryLoading(true);
    try {
      const summaryResult = await aiApi.summarize(transcriptionTextRef.current);
      setAiSummary(summaryResult.summary);
      toast.success('Live transcript summarized successfully.');
    } catch (err: any) {
      toast.error(`Summary generation failed: ${err.message}`);
    } finally {
      setSummaryLoading(false);
    }
  }, [toast]);

  const startTranscription = useCallback(async () => {
    console.log('[DEBUG] Starting transcription...');
    try {
      setTranscriptLines([]);
      transcriptionTextRef.current = '';
      setIsTranscribing(true);
      isTranscribingRef.current = true;
      setTranscriptStatus('listening');
      setVoiceDetected(false);
      audioStartTimeRef.current = Date.now();
      setElapsedAudioTime(0);
      setAiSummary('');

      audioTimerRef.current = setInterval(() => {
        setElapsedAudioTime(Math.floor((Date.now() - audioStartTimeRef.current) / 1000));
      }, 1000);

      console.log('[DEBUG] Requesting mic access...');
      const micStream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      console.log('[DEBUG] Mic access granted');

      // Set up voice activity detection
      const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
      if (AudioContextClass) {
        const audioContext = new AudioContextClass();
        await audioContext.resume();
        audioContextRef.current = audioContext;
        
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.8;
        analyserRef.current = analyser;
        
        const source = audioContext.createMediaStreamSource(micStream);
        source.connect(analyser);
        
        // Voice activity detection loop
        const detectVoice = () => {
          if (!isTranscribingRef.current) return;
          
          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          analyser.getByteFrequencyData(dataArray);
          
          // Calculate average volume
          const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
          const isVoiceActive = average > 25; // Threshold for voice detection
          
          if (isVoiceActive !== voiceActivityRef.current) {
            voiceActivityRef.current = isVoiceActive;
            setVoiceDetected(isVoiceActive);
          }
          
          requestAnimationFrame(detectVoice);
        };
        detectVoice();
      }

      transcriptionStreamRef.current = micStream;
      transcriptionChunksRef.current = [];
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      transcriptionRecorderRef.current = new MediaRecorder(micStream, { mimeType });

      console.log('[DEBUG] MediaRecorder created, mimeType:', transcriptionRecorderRef.current.mimeType);

      // WebM streams require the first chunk (which contains the EBML header)
      // to be prepended to every subsequent chunk so each blob is a valid
      // self-contained WebM file that Groq Whisper can decode.
      let headerChunk: Blob | null = null;

      transcriptionRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          console.log(`[DEBUG] Chunk received, size: ${event.data.size} bytes`);
          transcriptionChunksRef.current.push(event.data);

          if (!headerChunk) {
            // First chunk always contains the WebM EBML header — save it.
            headerChunk = event.data;
            // Don't send the header-only chunk alone; wait for the next one.
            return;
          }

          // Only process chunks if there was recent voice activity
          if (voiceActivityRef.current || event.data.size > 10000) {
            // Prepend the header so every chunk is a valid WebM container.
            const fullChunk = new Blob([headerChunk, event.data], { type: 'audio/webm' });
            transcriptionQueueRef.current = transcriptionQueueRef.current.then(() => processAudioChunk(fullChunk));
          } else {
            console.log('[DEBUG] Skipping chunk - no voice activity detected');
          }
        }
      };

      transcriptionRecorderRef.current.onstop = async () => {
        console.log('[DEBUG] MediaRecorder stopped');
        // Send all accumulated chunks as one final blob for any remaining audio.
        if (transcriptionChunksRef.current.length > 0) {
          const finalChunk = new Blob(transcriptionChunksRef.current, { type: 'audio/webm' });
          transcriptionQueueRef.current = transcriptionQueueRef.current.then(() => processAudioChunk(finalChunk));
        }
        await transcriptionQueueRef.current;
        await generateSummary();
      };

      transcriptionRecorderRef.current.start(4000); // 4-second chunks for better accuracy
      console.log('[DEBUG] MediaRecorder started with 4s chunks');

      toast.success('Live transcription started.');

      micStream.getAudioTracks().forEach(track => track.onended = () => stopTranscription());
    } catch (err: any) {
      console.error('[ERROR] Failed to start transcription:', err);
      toast.error(`Failed to start transcription: ${err.message}`);
      if (audioTimerRef.current) {
        clearInterval(audioTimerRef.current);
        audioTimerRef.current = null;
      }
      setIsTranscribing(false);
      setTranscriptStatus('idle');
      setVoiceDetected(false);
      isTranscribingRef.current = false;
    }
  }, [generateSummary, processAudioChunk, toast]);

  const stopTranscription = useCallback(async () => {
    isTranscribingRef.current = false;
    voiceActivityRef.current = false;
    if (transcriptionRecorderRef.current && transcriptionRecorderRef.current.state !== 'inactive') {
      transcriptionRecorderRef.current.stop();
    }
    if (audioTimerRef.current) {
      clearInterval(audioTimerRef.current);
      audioTimerRef.current = null;
    }
    if (transcriptionStreamRef.current) {
      transcriptionStreamRef.current.getTracks().forEach(t => t.stop());
      transcriptionStreamRef.current = null;
    }
    if (audioContextRef.current) {
      await audioContextRef.current.close().catch(() => null);
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setIsTranscribing(false);
    setTranscriptStatus('idle');
    setVoiceDetected(false);
  }, []);

  const copyTranscript = useCallback(() => {
    if (transcriptLines.length === 0) {
      toast.info('No transcript to copy.');
      return;
    }
    const fullText = transcriptLines.map(line => `[${line.timestamp}] ${line.speaker}: ${line.text}`).join('\n');
    navigator.clipboard.writeText(fullText);
    toast.success('Transcript copied to clipboard!');
  }, [transcriptLines, toast]);

  const downloadTranscript = useCallback(() => {
    if (transcriptLines.length === 0) {
      toast.info('No transcript to download.');
      return;
    }
    const fullText = transcriptLines.map(line => `[${line.timestamp}] ${line.speaker}: ${line.text}`).join('\n');
    const blob = new Blob([fullText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    downloadFile(url, 'transcript', 'txt');
    URL.revokeObjectURL(url);
    toast.success('Transcript downloaded!');
  }, [transcriptLines, toast]);

  const downloadAudio = useCallback(() => {
    if (!audioUrl) {
      toast.info('No audio recording available.');
      return;
    }
    downloadFile(audioUrl, recordedAudioName, 'webm');
    toast.success('Audio downloaded!');
  }, [audioUrl, recordedAudioName, toast]);

  const clearTranscript = useCallback(() => {
    setTranscriptLines([]);
    setShowClearConfirm(false);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    toast.success('Transcript cleared.');
  }, [audioUrl, toast]);

  const wordCount = transcriptLines.reduce((count, line) => count + line.text.split(/\s+/).length, 0);
  const lineCount = transcriptLines.length;
  const pendingTasks = tasks.filter(t => t.status !== 'done');
  const completedTasks = tasks.filter(t => t.status === 'done');

  return (
    <div className={`min-h-screen flex transition-colors ${isDark ? 'bg-[#0f1419] text-slate-200' : 'bg-slate-50 text-slate-900'}`}>
      
      {/* SIDEBAR */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside initial={{ x: -280, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: -280, opacity: 0 }} className={`w-64 border-r flex flex-col flex-shrink-0 transition-colors ${
            isDark ? 'bg-bg-secondary border-white/10' : 'bg-white border-border-main'
          }`}>
            <div className={`p-6 border-b flex items-center justify-between transition-colors ${isDark ? 'border-white/10' : 'border-border-main'}`}>
              <button onClick={() => navigate('/')} className="flex items-center space-x-2 group">
                <div className="w-8 h-8 bg-gradient-to-br from-[#0EA5E9] to-[#22D3EE] rounded-lg flex items-center justify-center shadow-lg group-hover:shadow-cyan-500/50 transition">
                  <span className="text-white font-bold text-sm">MN</span>
                </div>
                <span className={`font-bold text-lg transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>MeetNova</span>
              </button>
            </div>

            {/* ★ Hero Action: Share Screen */}
            <div className="p-4 space-y-2">
              {!isRecording ? (
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={startRecording}
                  className="w-full bg-gradient-to-r from-[#0EA5E9] to-[#22D3EE] hover:from-[#38BDF8] hover:to-[#06B6D4] text-white py-3.5 rounded-xl text-sm font-bold flex items-center justify-center space-x-2 transition shadow-lg shadow-cyan-500/30"
                >
                  <ScreenShare size={18} />
                  <span>Share Screen</span>
                </motion.button>
              ) : (
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={stopRecording}
                  className="w-full bg-gradient-to-r from-red-500 to-rose-600 text-white py-3.5 rounded-xl text-sm font-bold flex items-center justify-center space-x-2 transition shadow-lg shadow-red-500/30 animate-pulse"
                >
                  <Square size={14} className="fill-white" />
                  <span>Stop</span>
                  <span className="bg-white/20 px-2 py-0.5 rounded-lg text-xs font-mono tabular-nums">{formatTime(elapsedTime)}</span>
                </motion.button>
              )}
              <button
                onClick={startScreenshotSession}
                className={`w-full py-2.5 rounded-xl text-sm font-medium flex items-center justify-center space-x-2 transition border ${
                  isDark ? 'bg-white/5 hover:bg-white/10 border-white/10 text-slate-300' : 'bg-slate-100 hover:bg-slate-200 border-slate-200 text-slate-700'
                }`}
              >
                <Camera size={16} />
                <span>Screenshot</span>
              </button>
            </div>

            <nav className="flex-1 px-4 space-y-1">
              {NAV_ITEMS.map(item => (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-medium transition ${activeSection === item.id ? 'bg-[#0EA5E9]/10 text-[#38BDF8] border border-[#0EA5E9]/20' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}
                >
                  <item.icon size={18} /><span>{item.label}</span>
                  {item.id === 'tasks' && <span className="ml-auto bg-[#0EA5E9]/20 text-[#38BDF8] text-[10px] px-1.5 py-0.5 rounded-full">{pendingTasks.length}</span>}
                </button>
              ))}
            </nav>

            <div className="p-4 border-t border-white/10">
              <div className="flex items-center space-x-3 p-3 rounded-xl hover:bg-white/5 cursor-pointer transition">
                <div className="w-9 h-9 bg-[#0EA5E9] rounded-full flex items-center justify-center text-white font-bold">
                  {currentUser?.name?.[0]?.toUpperCase() ?? 'U'}
                </div>
                <div className="flex-1 min-w-0 font-medium">
                   <p className="text-sm truncate">{currentUser?.name ?? 'User'}</p>
                   <p className="text-[10px] text-slate-500 uppercase">{currentUser?.email ?? ''}</p>
                </div>
                <button
                  onClick={() => { localStorage.removeItem('token'); localStorage.removeItem('user'); navigate('/'); }}
                  title="Logout"
                >
                  <Settings className="text-slate-500" size={16} />
                </button>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className={`backdrop-blur-md border-b px-6 py-4 flex items-center justify-between flex-shrink-0 transition-colors ${
          isDark ? 'bg-bg-secondary/50 border-white/10' : 'bg-white/80 border-border-main'
        }`}>
          <div className="flex items-center space-x-4">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className={`p-2 rounded-lg transition-colors ${isDark ? 'hover:bg-white/5 text-slate-400' : 'hover:bg-slate-100 text-slate-600'}`}>
              <Home size={18} />
            </button>
            <div className="hidden md:block w-72 lg:w-96">
              <AnimatedSearch />
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <AnimatePresence>
              {isRecording && (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="hidden sm:flex items-center space-x-2 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-xl text-sm font-medium"
                >
                  <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.6)]" />
                  <span className="font-mono tabular-nums">{formatTime(elapsedTime)}</span>
                  <button onClick={stopRecording} className="ml-1 bg-red-500 hover:bg-red-600 text-white px-2.5 py-1 rounded-lg text-xs font-bold transition">
                    Stop
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
            <div className="relative">
              <Bell className="text-slate-400" size={20} />
              <div className={`absolute top-0 right-0 w-2 h-2 rounded-full border-2 ${
                isDark ? 'bg-[#0EA5E9] border-[#0f1419]' : 'bg-[#0EA5E9] border-white'
              }`} />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8 space-y-8 scroll-smooth">

          {/* ═══════════════════════════════════════ */}
          {/* OVERVIEW — Screen Share as Hero         */}
          {/* ═══════════════════════════════════════ */}
          {activeSection === 'overview' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
              <div>
                <h1 className={`text-3xl font-bold transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  Welcome back, {currentUser?.name?.split(' ')[0] ?? 'there'} 👋
                </h1>
                <p className="text-slate-500">Share your screen to start capturing meeting intelligence.</p>
              </div>

              {/* ★ HERO SCREEN SHARE CARD */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className={`relative overflow-hidden rounded-3xl border p-8 md:p-10 ${
                  isDark ? 'bg-gradient-to-br from-[#0EA5E9]/10 via-[#111827] to-[#22D3EE]/5 border-[#0EA5E9]/20' : 'bg-gradient-to-br from-cyan-50 to-blue-50 border-cyan-200'
                }`}
              >
                <div className="absolute inset-0 bg-[linear-gradient(rgba(14,165,233,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(14,165,233,0.03)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />
                <div className="absolute -top-20 -right-20 w-72 h-72 bg-[#0EA5E9]/10 rounded-full blur-[100px] pointer-events-none" />

                <div className="relative z-10 flex flex-col lg:flex-row items-center gap-8">
                  <div className="flex-1 space-y-5">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 rounded-full bg-[#22D3EE] animate-pulse" />
                      <span className="text-xs font-bold uppercase tracking-widest text-[#38BDF8]">Core Feature</span>
                    </div>
                    <h2 className={`text-2xl md:text-3xl font-extrabold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                      Share Your Meeting Screen
                    </h2>
                    <p className="text-slate-400 leading-relaxed max-w-lg">
                      Share your Google Meet or Zoom window with system audio and microphone input, then let MeetNova AI transcribe meetings, action items, and summaries in real time.
                    </p>

                    <div className="flex flex-wrap gap-3 pt-2">
                      {!isRecording ? (
                        <motion.button
                          whileHover={{ scale: 1.03, boxShadow: '0 0 30px rgba(14,165,233,0.4)' }}
                          whileTap={{ scale: 0.97 }}
                          onClick={startRecording}
                          className="flex items-center space-x-3 bg-gradient-to-r from-[#0EA5E9] to-[#22D3EE] text-white px-8 py-4 rounded-2xl font-bold text-lg shadow-xl shadow-cyan-500/30 transition"
                        >
                          <ScreenShare size={24} />
                          <span>Start Screen + Audio</span>
                        </motion.button>
                      ) : (
                        <motion.button
                          whileHover={{ scale: 1.03 }}
                          whileTap={{ scale: 0.97 }}
                          onClick={stopRecording}
                          className="flex items-center space-x-3 bg-gradient-to-r from-red-500 to-rose-600 text-white px-8 py-4 rounded-2xl font-bold text-lg shadow-xl shadow-red-500/30 animate-pulse transition"
                        >
                          <Square size={20} className="fill-white" />
                          <span>Stop Recording</span>
                          <span className="ml-2 bg-white/20 px-3 py-1 rounded-xl text-base font-mono tabular-nums">{formatTime(elapsedTime)}</span>
                        </motion.button>
                      )}
                      <motion.button
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={startScreenshotSession}
                        className={`flex items-center space-x-2 px-6 py-4 rounded-2xl font-semibold transition border ${
                          isDark ? 'bg-white/5 hover:bg-white/10 border-white/10 text-white' : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-800'
                        }`}
                      >
                        <Camera size={20} />
                        <span>Screenshot</span>
                      </motion.button>
                    </div>
                  </div>

                  <div className="flex-shrink-0 hidden lg:flex flex-col items-center space-y-3">
                    <div className={`w-56 h-36 rounded-2xl border-2 border-dashed flex items-center justify-center relative ${
                      isDark ? 'border-[#0EA5E9]/30 bg-[#0EA5E9]/5' : 'border-cyan-300 bg-cyan-50'
                    }`}>
                      <div className="text-center">
                        <MonitorUp size={40} className="mx-auto mb-2 text-[#0EA5E9]/60" />
                        <p className="text-xs text-slate-500 font-medium">Your Google Meet /<br/>Zoom Window</p>
                      </div>
                      {isRecording && (
                        <div className="absolute top-2 right-2 bg-red-500 text-white text-[9px] uppercase font-bold px-2 py-0.5 rounded flex items-center space-x-1">
                          <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
                          <span>REC</span>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center space-x-3 text-xs text-slate-500">
                      <div className="flex items-center space-x-1"><Mic size={12} /><span>Audio</span></div>
                      <div className="flex items-center space-x-1"><Video size={12} /><span>Video</span></div>
                      <div className="flex items-center space-x-1"><Zap size={12} className="text-[#22D3EE]" /><span className="text-[#38BDF8] font-semibold">AI On</span></div>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Stats */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                  { label: 'Recordings', value: String(recordings.length), icon: Video, trend: recordings.length > 0 ? `+${recordings.length}` : '0', up: true, color: 'from-rose-500 to-rose-700' },
                  { label: 'Screenshots', value: String(screenshots.length), icon: Camera, trend: screenshots.length > 0 ? `+${screenshots.length}` : '0', up: true, color: 'from-cyan-500 to-cyan-700' },
                  { label: 'Meetings Tracked', value: String(recordings.length + screenshots.length), icon: Calendar, trend: '0%', up: true, color: 'from-indigo-500 to-indigo-700' },
                  { label: 'Tasks', value: tasksLoading ? '…' : String(tasks.length), icon: CheckSquare, trend: `${pendingTasks.length} pending`, up: pendingTasks.length === 0, color: 'from-amber-500 to-amber-700' },
                ].map((s, i) => <StatCard key={i} stat={s} index={i} />)}
              </div>

              {/* Recent Captures */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Recent Captures</h3>
                  <div className={`flex space-x-1 p-1 rounded-xl border ${isDark ? 'bg-white/5 border-white/10' : 'bg-slate-100 border-slate-200'}`}>
                    <button
                      onClick={() => setCaptureTab('recordings')}
                      className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                        captureTab === 'recordings' ? (isDark ? 'bg-white/10 text-white' : 'bg-white text-slate-900 shadow-sm') : 'text-slate-500'
                      }`}
                    >
                      <Video size={13} /><span>Recordings ({recordings.length})</span>
                    </button>
                    <button
                      onClick={() => setCaptureTab('screenshots')}
                      className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                        captureTab === 'screenshots' ? (isDark ? 'bg-white/10 text-white' : 'bg-white text-slate-900 shadow-sm') : 'text-slate-500'
                      }`}
                    >
                      <ImageIcon size={13} /><span>Screenshots ({screenshots.length})</span>
                    </button>
                  </div>
                </div>

                {captureTab === 'recordings' && (
                  <div className={`border rounded-2xl transition-colors ${isDark ? 'bg-bg-secondary/30 border-white/10' : 'bg-white border-border-main shadow-sm'}`}>
                    {recordings.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-16">
                        <Video size={40} className="text-slate-500/50 mb-3" />
                        <p className={`font-medium mb-1 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>No recordings yet</p>
                        <p className="text-sm text-slate-500">Start a screen share to begin capturing.</p>
                      </div>
                    ) : (
                      <div className="divide-y divide-white/5">
                        {recordings.map(rec => (
                          <div key={rec.id} className="flex items-center space-x-4 p-4 group hover:bg-white/5 transition">
                            <div onClick={() => { setPreviewUrl(rec.url); setPreviewType('video'); }} className="w-14 h-14 rounded-xl bg-gradient-to-br from-red-500/20 to-rose-500/10 flex items-center justify-center cursor-pointer hover:from-red-500/30 transition flex-shrink-0">
                              <Video size={22} className="text-red-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className={`font-semibold truncate ${isDark ? 'text-white' : 'text-slate-900'}`}>{rec.name}</p>
                              <div className="flex items-center space-x-3 text-xs text-slate-500 mt-0.5">
                                <span className="flex items-center space-x-1"><Clock size={11} /><span>{rec.duration}</span></span>
                                <span>•</span><span>{rec.size}</span><span>•</span><span>{rec.timestamp}</span>
                              </div>
                            </div>
                            <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition">
                              <button onClick={() => transcribeRecording(rec)} className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-blue-400 transition"><Mic size={16} /></button>
                              <button onClick={() => downloadFile(rec.url, rec.name, 'webm')} className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-emerald-400 transition"><Download size={16} /></button>
                              <button onClick={() => deleteRecording(rec.id)} className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-red-400 transition"><Trash2 size={16} /></button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {captureTab === 'screenshots' && (
                  <div>
                    {screenshots.length === 0 ? (
                      <div className={`border rounded-2xl flex flex-col items-center justify-center py-16 transition-colors ${isDark ? 'bg-bg-secondary/30 border-white/10' : 'bg-white border-border-main shadow-sm'}`}>
                        <Camera size={40} className="text-slate-500/50 mb-3" />
                        <p className={`font-medium mb-1 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>No screenshots yet</p>
                        <p className="text-sm text-slate-500">Click "Screenshot" to capture your meeting screen.</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {screenshots.map(ss => (
                          <motion.div key={ss.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className={`rounded-2xl border overflow-hidden group transition ${isDark ? 'bg-bg-secondary/30 border-white/10 hover:border-white/20' : 'bg-white border-slate-200 hover:shadow-md'}`}>
                            <div className="relative cursor-pointer" onClick={() => { setPreviewUrl(ss.url); setPreviewType('image'); }}>
                              <img src={ss.url} alt={ss.name} className="w-full h-36 object-cover" />
                              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition flex items-center justify-center">
                                <span className="text-white font-medium text-sm opacity-0 group-hover:opacity-100 transition bg-black/60 px-3 py-1 rounded-lg">View</span>
                              </div>
                            </div>
                            <div className="p-3 flex items-center justify-between">
                              <div className="min-w-0">
                                <p className={`text-sm font-medium truncate ${isDark ? 'text-white' : 'text-slate-900'}`}>{ss.name}</p>
                                <p className="text-[11px] text-slate-500">{ss.timestamp}</p>
                              </div>
                              <div className="flex items-center space-x-1">
                                <button onClick={() => downloadFile(ss.url, ss.name, 'png')} className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 transition"><Download size={14} /></button>
                                <button onClick={() => deleteScreenshot(ss.id)} className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-red-400 transition"><Trash2 size={14} /></button>
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Intelligence & Leaderboard */}
              <div className="grid lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className={`text-xl font-bold transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>Recent Intelligence</h3>
                    <button className="text-sm text-[#38BDF8] flex items-center space-x-1 hover:underline"><span>View All</span><ArrowUpRight size={14} /></button>
                  </div>
                  <div className={`border rounded-2xl p-2 divide-y transition-colors ${
                    isDark ? 'bg-bg-secondary/30 border-white/10 divide-white/5' : 'bg-white border-border-main divide-slate-100 shadow-sm'
                  }`}>
                    {MEETINGS.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-12">
                        <FileText size={36} className="text-slate-500/40 mb-2" />
                        <p className="text-sm text-slate-500">Meeting intelligence will appear here after your first screen share.</p>
                      </div>
                    ) : (
                      MEETINGS.slice(0, 3).map((m, i) => <MeetingRow key={m.id} meeting={m} index={i} />)
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* MEETINGS ARCHIVE */}
          {activeSection === 'meetings' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
               <div className="flex items-center justify-between">
                 <h1 className={`text-3xl font-bold transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>Meeting Archive</h1>
                 <div className="flex items-center space-x-2"><Filter size={16} className="text-slate-500" /><span className="text-sm text-slate-500">Filter by Date</span></div>
               </div>
               <div className={`border rounded-2xl p-2 divide-y transition-colors ${
                 isDark ? 'bg-bg-secondary/30 border-white/10 divide-white/5' : 'bg-white border-border-main divide-slate-100 shadow-sm'
               }`}>
                  {MEETINGS.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16">
                      <Calendar size={40} className="text-slate-500/40 mb-3" />
                      <p className="text-sm text-slate-500">No meetings recorded yet. Start by sharing your screen.</p>
                    </div>
                  ) : (
                    MEETINGS.map((m, i) => <MeetingRow key={m.id} meeting={m} index={i} />)
                  )}
               </div>
            </motion.div>
          )}

          {/* TASKS */}
          {activeSection === 'tasks' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
              <div className="flex items-center justify-between">
                <h1 className={`text-3xl font-bold transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>Action Center</h1>
                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={openCreateTask}
                  className="flex items-center space-x-2 bg-[#0EA5E9] hover:bg-[#38BDF8] text-white px-4 py-2 rounded-xl text-sm font-bold transition shadow-lg shadow-cyan-500/20"
                >
                  <Plus size={16} />
                  <span>New Task</span>
                </motion.button>
              </div>

              {tasksError && (
                <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                  {tasksError}
                </div>
              )}

              {tasksLoading ? (
                <div className="flex justify-center py-16">
                  <Loader2 size={32} className="animate-spin text-[#0EA5E9]" />
                </div>
              ) : (
                <div className="grid lg:grid-cols-2 gap-8">
                  <div className="space-y-4">
                    <h3 className="text-xs uppercase font-bold text-slate-500 tracking-widest flex items-center space-x-2">
                      <Circle size={10} className="text-orange-500 fill-orange-500" />
                      <span>Pending ({pendingTasks.length})</span>
                    </h3>
                    <div className="space-y-3">
                      {pendingTasks.length === 0 ? (
                        <div className={`border rounded-2xl py-12 flex flex-col items-center justify-center ${isDark ? 'bg-bg-secondary/30 border-white/10' : 'bg-white border-slate-200'}`}>
                          <CheckSquare size={32} className="text-slate-500/40 mb-2" />
                          <p className="text-sm text-slate-500">No pending tasks. Click "New Task" to add one.</p>
                        </div>
                      ) : (
                        pendingTasks.map(t => (
                          <div key={t.id} className="group relative">
                            <AnimatedCheckbox
                              checked={t.status === 'done'}
                              onChange={() => toggleTask(t.id)}
                              label={t.title}
                              owner={t.description || undefined}
                              priority={t.priority as any}
                            />
                            <div className="absolute top-3 right-3 flex space-x-1 opacity-0 group-hover:opacity-100 transition">
                              <button onClick={() => openEditTask(t)} className="p-1 rounded text-slate-400 hover:text-[#38BDF8] hover:bg-white/10 transition text-xs">Edit</button>
                              <button onClick={() => handleDeleteTask(t.id)} className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-white/10 transition text-xs">Del</button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                  <div className="space-y-4">
                    <h3 className="text-xs uppercase font-bold text-slate-500 tracking-widest flex items-center space-x-2">
                      <CheckCircle size={10} className="text-emerald-500 fill-emerald-500" />
                      <span>Completed ({completedTasks.length})</span>
                    </h3>
                    <div className="space-y-3 opacity-60">
                      {completedTasks.map(t => (
                        <div key={t.id} className="group relative">
                          <AnimatedCheckbox
                            checked={true}
                            onChange={() => toggleTask(t.id)}
                            label={t.title}
                            owner={t.description || undefined}
                            priority={t.priority as any}
                          />
                          <div className="absolute top-3 right-3 flex space-x-1 opacity-0 group-hover:opacity-100 transition">
                            <button onClick={() => handleDeleteTask(t.id)} className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-white/10 transition text-xs">Del</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* TRANSCRIPT — LIVE AUDIO TRANSCRIPTION */}
          {activeSection === 'transcript' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              {/* PAGE HEADER */}
              <div className="flex items-start justify-between">
                <div>
                  <h1 className={`text-3xl font-bold transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>Live Transcript</h1>
                  <p className="text-slate-500 mt-2">Audio is transcribed in real time. Summaries and action items are extracted automatically.</p>
                </div>
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-full border transition-colors ${
                    transcriptStatus === 'idle'
                      ? isDark ? 'bg-slate-500/10 border-slate-500/20 text-slate-400' : 'bg-slate-100 border-slate-200 text-slate-600'
                      : transcriptStatus === 'listening'
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                      : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                  }`}
                >
                  <div className={`w-2 h-2 rounded-full ${
                    transcriptStatus === 'idle' ? 'bg-slate-400' : transcriptStatus === 'listening' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                  }`} />
                  <span className="text-sm font-semibold">
                    {transcriptStatus === 'idle' ? 'Ready' : transcriptStatus === 'listening' ? 'Listening…' : 'Processing…'}
                  </span>
                </motion.div>
              </div>

              {/* AUDIO CONTROLS CARD */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className={`border rounded-3xl p-8 transition-colors ${
                  isDark ? 'bg-gradient-to-br from-slate-900 to-slate-800/50 border-white/10' : 'bg-gradient-to-br from-white to-slate-50 border-slate-200'
                }`}
              >
                <div className="flex flex-col lg:flex-row items-center gap-12">
                  {/* MIC BUTTON */}
                  <div className="flex flex-col items-center space-y-4">
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={isTranscribing ? stopTranscription : startTranscription}
                      className={`relative w-32 h-32 rounded-full flex items-center justify-center text-white font-bold transition-all shadow-2xl ${
                        isTranscribing
                          ? 'bg-gradient-to-br from-red-500 to-rose-600 shadow-red-500/50'
                          : 'bg-gradient-to-br from-[#0EA5E9] to-[#22D3EE] shadow-cyan-500/50 hover:shadow-cyan-500/70'
                      }`}
                    >
                      {isTranscribing ? <MicOff size={48} /> : <Mic size={48} />}
                      {isTranscribing && (
                        <motion.div
                          animate={{ scale: voiceDetected ? [1, 1.4, 1] : [1, 1.1, 1] }}
                          transition={{ duration: voiceDetected ? 0.8 : 2, repeat: Infinity }}
                          className={`absolute inset-0 rounded-full border-2 opacity-50 ${
                            voiceDetected ? 'border-green-400' : 'border-red-400'
                          }`}
                        />
                      )}
                      {isTranscribing && voiceDetected && (
                        <motion.div
                          animate={{ scale: [1, 1.6, 1] }}
                          transition={{ duration: 0.6, repeat: Infinity }}
                          className="absolute inset-0 rounded-full border-2 border-green-300 opacity-30"
                        />
                      )}
                    </motion.button>
                    <div className="text-center">
                      <p className={`text-sm font-semibold transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>
                        {isTranscribing ? 'Stop' : 'Start Transcription'}
                      </p>
                      {isTranscribing && (
                        <div className="space-y-1">
                          <p className="text-xs text-slate-500 font-mono">{formatTime(elapsedAudioTime)}</p>
                          <div className={`flex items-center justify-center space-x-1 text-xs ${
                            voiceDetected ? 'text-green-500' : 'text-slate-500'
                          }`}>
                            <div className={`w-1.5 h-1.5 rounded-full ${
                              voiceDetected ? 'bg-green-500 animate-pulse' : 'bg-slate-400'
                            }`} />
                            <span>{voiceDetected ? 'Voice detected' : 'Listening...'}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* FEATURE PILLS */}
                  <div className="flex-1 grid grid-cols-2 gap-4">
                    {[
                      { icon: '🎙', label: 'Real-time transcription', badge: null },
                      { icon: '📝', label: 'AI Summary', badge: 'Pending backend' },
                      { icon: '✅', label: 'Action Item Extraction', badge: 'Pending backend' },
                      { icon: '🌐', label: 'Speaker Diarization', badge: 'Coming Soon' },
                      { icon: '🔍', label: 'Keyword Highlights', badge: 'Coming Soon' },
                    ].map((feature, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.05 }}
                        className={`flex items-center space-x-3 p-3 rounded-xl border transition-colors ${
                          isDark ? 'bg-white/5 border-white/10' : 'bg-white border-slate-200'
                        }`}
                      >
                        <span className="text-xl">{feature.icon}</span>
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-medium transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>{feature.label}</p>
                          {feature.badge && (
                            <p className="text-[11px] text-slate-500 font-semibold">{feature.badge}</p>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </motion.div>

              {/* LIVE TRANSCRIPT AREA */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className={`border rounded-2xl h-96 flex flex-col transition-colors ${
                  isDark ? 'bg-slate-900/50 border-white/10' : 'bg-white border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between p-4 border-b border-white/10">
                  <h3 className={`font-semibold transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>Transcript</h3>
                  {isTranscribing && (
                    <div className="flex items-center space-x-1 text-red-500 text-xs font-bold">
                      <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                      <span>● Live</span>
                    </div>
                  )}
                </div>

                <div ref={transcriptContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                  {transcriptLines.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center space-y-4">
                      <AnimatedWaveform />
                      <p className={`text-lg font-semibold transition-colors ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Waiting for audio…</p>
                      <p className="text-sm text-slate-500">Press the mic button above to begin transcribing.</p>
                    </div>
                  ) : (
                    transcriptLines.map((line, idx) => (
                      <motion.div
                        key={line.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                        className="space-y-2"
                      >
                        <div className="flex items-start space-x-3">
                          <span className={`text-xs font-mono font-semibold px-2 py-1 rounded transition-colors ${
                            isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {line.timestamp}
                          </span>
                          <div className="flex items-center space-x-2">
                            <div className={`w-2.5 h-2.5 rounded-full ${SPEAKER_COLORS[line.speaker]?.dot || 'bg-slate-500'}`} />
                            <span className={`text-xs font-bold transition-colors ${
                              SPEAKER_COLORS[line.speaker]?.text || 'text-slate-400'
                            }`}>
                              {line.speaker}
                            </span>
                            {line.simulated && (
                              <span className="text-[10px] text-slate-500 italic">(simulated)</span>
                            )}
                          </div>
                        </div>
                        <p className={`text-sm leading-relaxed pl-14 transition-colors ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>
                          {line.text}
                        </p>
                        <div className="pl-14 h-1 bg-gradient-to-r rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${Math.round(line.confidence * 100)}%` }}
                            transition={{ duration: 0.5 }}
                            className={`h-full ${
                              line.confidence > 0.85 ? 'bg-emerald-500' : line.confidence > 0.7 ? 'bg-amber-500' : 'bg-red-500'
                            }`}
                          />
                        </div>
                      </motion.div>
                    ))
                  )}
                </div>
              </motion.div>

              {/* TRANSCRIPT ACTIONS BAR */}
              {(transcriptLines.length > 0 || audioUrl) && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className={`flex flex-col sm:flex-row items-center justify-between gap-4 p-4 border rounded-2xl transition-colors ${
                    isDark ? 'bg-slate-900/50 border-white/10' : 'bg-white border-slate-200'
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    {audioUrl && (
                      <button
                        onClick={downloadAudio}
                        className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          isDark ? 'hover:bg-white/10 text-emerald-300' : 'hover:bg-emerald-50 text-emerald-700'
                        }`}
                      >
                        <Download size={16} />
                        <span>Download Audio</span>
                      </button>
                    )}
                    {transcriptLines.length > 0 && (
                      <>
                        <button
                          onClick={copyTranscript}
                          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                            isDark ? 'hover:bg-white/10 text-slate-300' : 'hover:bg-slate-100 text-slate-700'
                          }`}
                        >
                          <Copy size={16} />
                          <span>Copy All</span>
                        </button>
                        <button
                          onClick={downloadTranscript}
                          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                            isDark ? 'hover:bg-white/10 text-slate-300' : 'hover:bg-slate-100 text-slate-700'
                          }`}
                        >
                          <Download size={16} />
                          <span>Download .txt</span>
                        </button>
                        <button
                          disabled
                          title="Coming soon"
                          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium opacity-50 cursor-not-allowed transition-colors ${
                            isDark ? 'hover:bg-white/10 text-slate-500' : 'hover:bg-slate-100 text-slate-500'
                          }`}
                        >
                          <Download size={16} />
                          <span>Download .srt</span>
                        </button>
                      </>
                    )}
                    {showClearConfirm ? (
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={clearTranscript}
                          className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => setShowClearConfirm(false)}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                            isDark ? 'hover:bg-white/10 text-slate-300' : 'hover:bg-slate-100 text-slate-700'
                          }`}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setShowClearConfirm(true)}
                        className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors text-red-400 ${
                          isDark ? 'hover:bg-red-500/20' : 'hover:bg-red-50'
                        }`}
                      >
                        <Trash2 size={16} />
                        <span>Clear</span>
                      </button>
                    )}
                  </div>
                  {transcriptLines.length > 0 && (
                    <div className={`text-xs font-mono px-3 py-1 rounded-lg transition-colors ${
                      isDark ? 'bg-white/5 text-slate-400' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {wordCount} words · {lineCount} lines
                    </div>
                  )}
                </motion.div>
              )}

              {/* AI SUMMARY PANEL */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="space-y-4"
              >
                <h3 className={`text-lg font-bold transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>AI Summary</h3>

                {summaryLoading ? (
                  <div className={`border rounded-2xl p-8 flex flex-col items-center justify-center text-center transition-colors ${isDark ? 'bg-slate-900/50 border-white/10' : 'bg-white border-slate-200'}`}>
                    <Loader2 size={32} className="animate-spin text-[#0EA5E9] mb-3" />
                    <p className="text-sm text-slate-500">Generating summary via AI…</p>
                  </div>
                ) : aiSummary ? (
                  <div className={`border rounded-2xl p-6 space-y-3 transition-colors ${isDark ? 'bg-slate-900/50 border-white/10' : 'bg-white border-slate-200'}`}>
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="text-xs font-mono font-semibold px-2 py-1 rounded bg-emerald-500/20 text-emerald-400">
                        ✓ Summary ready
                      </span>
                    </div>
                    <p className={`text-sm leading-relaxed whitespace-pre-wrap transition-colors ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>
                      {aiSummary}
                    </p>
                    <button
                      onClick={() => { navigator.clipboard.writeText(aiSummary); toast.success('Summary copied!'); }}
                      className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${isDark ? 'hover:bg-white/10 text-slate-400' : 'hover:bg-slate-100 text-slate-600'}`}
                    >
                      <Copy size={14} />
                      <span>Copy Summary</span>
                    </button>
                  </div>
                ) : transcriptLines.length === 0 ? (
                  <div className={`border rounded-2xl p-8 flex flex-col items-center justify-center text-center transition-colors ${isDark ? 'bg-slate-900/50 border-white/10' : 'bg-white border-slate-200'}`}>
                    <AlertCircle size={32} className="text-slate-500/50 mb-3" />
                    <p className="text-sm text-slate-500">Summary will appear after transcription.</p>
                  </div>
                ) : (
                  <div className={`border rounded-2xl p-8 flex flex-col items-center justify-center text-center transition-colors ${isDark ? 'bg-slate-900/50 border-white/10' : 'bg-white border-slate-200'}`}>
                    <AlertCircle size={32} className="text-slate-500/50 mb-3" />
                    <p className="text-sm text-slate-500">Summary generation failed or not yet available.</p>
                  </div>
                )}
              </motion.div>

            </motion.div>
          )}
        </main>
      </div>

      {/* pendingScreenshotStream UI */}
      <AnimatePresence>
        {isPendingScreenshot && (
          <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 shadow-2xl"
          >
            <div className={`flex flex-col sm:flex-row items-center gap-4 px-6 py-4 rounded-2xl border ${isDark ? 'bg-bg-secondary/90 backdrop-blur-xl border-white/10' : 'bg-white/90 backdrop-blur-xl border-slate-200'}`}>
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center text-cyan-500 animate-pulse">
                  <Camera size={20} />
                </div>
                <div>
                  <h4 className={`font-bold text-sm ${isDark ? 'text-white' : 'text-slate-900'}`}>Screen Selected</h4>
                  <p className="text-xs text-slate-500">Ready to capture a screenshot.</p>
                </div>
              </div>
              <div className="flex items-center space-x-2 w-full sm:w-auto">
                <button onClick={cancelScreenshot} className={`flex-1 sm:flex-none px-4 py-2 rounded-xl text-sm font-semibold transition ${isDark ? 'hover:bg-white/10 text-white' : 'hover:bg-slate-100 text-slate-700'}`}>
                  Cancel
                </button>
                <button onClick={confirmScreenshot} className="flex-1 sm:flex-none bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white px-6 py-2 rounded-xl text-sm font-bold shadow-lg transition">
                  Capture Now
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ★ Floating Screen Share FAB (visible when not on overview) */}
      {activeSection !== 'overview' && !isRecording && (
        <motion.button
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          whileHover={{ scale: 1.1, boxShadow: '0 0 40px rgba(14,165,233,0.5)' }}
          whileTap={{ scale: 0.95 }}
          onClick={startRecording}
          className="fixed bottom-8 right-8 z-50 w-16 h-16 bg-gradient-to-br from-[#0EA5E9] to-[#22D3EE] rounded-2xl flex items-center justify-center text-white shadow-2xl shadow-cyan-500/40"
          title="Start Screen Share"
        >
          <ScreenShare size={26} />
        </motion.button>
      )}

      {/* Full-screen Preview Modal */}
      <AnimatePresence>
        {previewUrl && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setPreviewUrl(null)} className="fixed inset-0 z-[200] bg-black/80 backdrop-blur-sm" />
            <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} className="fixed inset-4 md:inset-12 z-[201] flex items-center justify-center">
              <div className="relative w-full h-full flex items-center justify-center">
                <button onClick={() => setPreviewUrl(null)} className="absolute top-2 right-2 z-10 p-2 rounded-full bg-black/60 text-white hover:bg-black/80 transition"><X size={24} /></button>
                {previewType === 'video' ? (
                  <video src={previewUrl} controls autoPlay className="max-w-full max-h-full rounded-2xl shadow-2xl" />
                ) : (
                  <img src={previewUrl} alt="Preview" className="max-w-full max-h-full rounded-2xl shadow-2xl object-contain" />
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Task Create / Edit Modal */}
      <AnimatePresence>
        {taskModalOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setTaskModalOpen(false)}
              className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-x-4 md:inset-x-auto top-[10%] md:top-1/2 md:-translate-y-1/2 md:left-1/2 md:-translate-x-1/2 z-[201] md:w-[480px] bg-[#111827] border border-white/10 rounded-2xl shadow-2xl p-6"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-white">{editingTask ? 'Edit Task' : 'New Task'}</h2>
                <button onClick={() => setTaskModalOpen(false)} className="text-slate-400 hover:text-white transition"><X size={20} /></button>
              </div>
              <form onSubmit={handleTaskSubmit} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">Title *</label>
                  <input
                    required
                    value={taskForm.title}
                    onChange={e => setTaskForm(f => ({ ...f, title: e.target.value }))}
                    placeholder="What needs to be done?"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-[#38BDF8] focus:ring-1 focus:ring-[#38BDF8] outline-none transition text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">Description</label>
                  <textarea
                    rows={3}
                    value={taskForm.description}
                    onChange={e => setTaskForm(f => ({ ...f, description: e.target.value }))}
                    placeholder="Optional details…"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-[#38BDF8] focus:ring-1 focus:ring-[#38BDF8] outline-none transition text-sm resize-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-slate-300 block mb-1">Status</label>
                    <select
                      value={taskForm.status}
                      onChange={e => setTaskForm(f => ({ ...f, status: e.target.value as TaskItem['status'] }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:border-[#38BDF8] outline-none transition text-sm"
                    >
                      <option value="todo">To Do</option>
                      <option value="in-progress">In Progress</option>
                      <option value="done">Done</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-300 block mb-1">Priority</label>
                    <select
                      value={taskForm.priority}
                      onChange={e => setTaskForm(f => ({ ...f, priority: e.target.value as TaskItem['priority'] }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:border-[#38BDF8] outline-none transition text-sm"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={() => setTaskModalOpen(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white transition">Cancel</button>
                  <button
                    type="submit"
                    disabled={taskSubmitting}
                    className="flex items-center gap-2 px-5 py-2 text-sm bg-[#0EA5E9] hover:bg-[#38BDF8] disabled:opacity-60 text-white rounded-lg font-bold transition"
                  >
                    {taskSubmitting && <Loader2 size={14} className="animate-spin" />}
                    {editingTask ? 'Save Changes' : 'Create Task'}
                  </button>
                </div>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
