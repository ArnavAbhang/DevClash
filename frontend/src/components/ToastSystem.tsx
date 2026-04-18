import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle, AlertCircle, Info, X, Zap, Brain } from 'lucide-react';
import { useState, useEffect, createContext, useContext, ReactNode } from 'react';

type ToastType = 'success' | 'error' | 'info' | 'ai' | 'task';

interface Toast {
  id: number;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastContextType {
  addToast: (toast: Omit<Toast, 'id'>) => number;
  removeToast: (id: number) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

const TOAST_ICONS = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
  ai: Brain,
  task: Zap,
};

const TOAST_STYLES = {
  success: {
    dark: 'bg-emerald-900/90 border-emerald-500/40 text-emerald-100',
    light: 'bg-emerald-50 border-emerald-300 text-emerald-900',
    icon: 'text-emerald-400',
  },
  error: {
    dark: 'bg-rose-900/90 border-rose-500/40 text-rose-100',
    light: 'bg-rose-50 border-rose-300 text-rose-900',
    icon: 'text-rose-400',
  },
  info: {
    dark: 'bg-blue-900/90 border-blue-500/40 text-blue-100',
    light: 'bg-blue-50 border-blue-300 text-blue-900',
    icon: 'text-blue-400',
  },
  ai: {
    dark: 'bg-indigo-900/90 border-indigo-500/40 text-indigo-100',
    light: 'bg-indigo-50 border-indigo-300 text-indigo-900',
    icon: 'text-indigo-400',
  },
  task: {
    dark: 'bg-teal-900/90 border-teal-500/40 text-teal-100',
    light: 'bg-teal-50 border-teal-300 text-teal-900',
    icon: 'text-teal-400',
  },
};

function ToastItem({ toast, onRemove, isDark }: { toast: Toast; onRemove: (id: number) => void; isDark: boolean }) {
  const Icon = TOAST_ICONS[toast.type] || Info;
  const styles = TOAST_STYLES[toast.type] || TOAST_STYLES.info;
  const style = isDark ? styles.dark : styles.light;

  useEffect(() => {
    const timer = setTimeout(() => onRemove(toast.id), toast.duration || 4000);
    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, onRemove]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -20, scale: 0.95, x: 20 }}
      animate={{ opacity: 1, y: 0, scale: 1, x: 0 }}
      exit={{ opacity: 0, scale: 0.95, x: 20 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`relative flex items-start space-x-3 p-4 rounded-xl border backdrop-blur-xl shadow-2xl max-w-sm w-full transition-colors ${style}`}
    >
      {/* Progress Bar */}
      <motion.div
        className="absolute bottom-0 left-0 h-0.5 bg-current opacity-30 rounded-full"
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: (toast.duration || 4000) / 1000, ease: 'linear' }}
      />

      {/* Icon */}
      <div className={`flex-shrink-0 mt-0.5 ${styles.icon}`}>
        <Icon size={20} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {toast.title && (
          <p className="font-semibold text-sm">{toast.title}</p>
        )}
        <p className="text-sm opacity-90">{toast.message}</p>
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            className="mt-2 text-xs font-semibold underline underline-offset-2 hover:opacity-70 transition"
          >
            {toast.action.label}
          </button>
        )}
      </div>

      {/* Close */}
      <button
        onClick={() => onRemove(toast.id)}
        className="flex-shrink-0 opacity-50 hover:opacity-100 transition"
      >
        <X size={16} />
      </button>
    </motion.div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'));
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains('dark'));
    });
    observer.observe(document.documentElement, { attributes: true });
    return () => observer.disconnect();
  }, []);

  const addToast = (toast: Omit<Toast, 'id'>) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [{ ...toast, id }, ...prev]);
    return id;
  };

  const removeToast = (id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      
      {/* Toast Container */}
      <div className="fixed top-6 right-6 z-[9999] flex flex-col space-y-3 pointer-events-none">
        <AnimatePresence mode="popLayout">
          {toasts.map(toast => (
            <div key={toast.id} className="pointer-events-auto">
              <ToastItem
                toast={toast}
                onRemove={removeToast}
                isDark={isDark}
              />
            </div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');

  const add = context.addToast;

  return {
    success: (message: string, options: Partial<Omit<Toast, 'id' | 'type' | 'message'>> = {}) =>
      add({ type: 'success', message, ...options }),
    error: (message: string, options: Partial<Omit<Toast, 'id' | 'type' | 'message'>> = {}) =>
      add({ type: 'error', message, ...options }),
    info: (message: string, options: Partial<Omit<Toast, 'id' | 'type' | 'message'>> = {}) =>
      add({ type: 'info', message, ...options }),
    ai: (message: string, options: Partial<Omit<Toast, 'id' | 'type' | 'message'>> = {}) =>
      add({ type: 'ai', message, ...options }),
    task: (message: string, options: Partial<Omit<Toast, 'id' | 'type' | 'message'>> = {}) =>
      add({ type: 'task', message, ...options }),
  };
}
