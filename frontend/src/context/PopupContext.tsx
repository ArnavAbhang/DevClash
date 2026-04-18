import { createContext, useContext, useState, ReactNode, FormEvent } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, CheckCircle, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// ── API base URL (injected by Vite from .env / .env.production) ──────────────
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

type PopupType = 'login' | 'signup';

interface PopupContextType {
  isOpen: boolean;
  type: PopupType;
  openPopup: (type?: PopupType) => void;
  closePopup: () => void;
}

const PopupContext = createContext<PopupContextType | undefined>(undefined);

export function PopupProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [type, setType] = useState<PopupType>('signup');

  const openPopup = (newType: PopupType = 'signup') => {
    setType(newType);
    setIsOpen(true);
  };

  const closePopup = () => setIsOpen(false);

  return (
    <PopupContext.Provider value={{ isOpen, type, openPopup, closePopup }}>
      {children}
    </PopupContext.Provider>
  );
}

export function usePopup() {
  const context = useContext(PopupContext);
  if (context === undefined) {
    throw new Error('usePopup must be used within a PopupProvider');
  }
  return context;
}

// ── Auth helpers ──────────────────────────────────────────────────────────────

async function apiRegister(name: string, email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? 'Registration failed');
  return data; // { success, message, data: { user, token } }
}

async function apiLogin(email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? 'Login failed');
  return data; // { success, message, data: { user, token } }
}

// ── Modal ─────────────────────────────────────────────────────────────────────

export function PopupModal() {
  const { isOpen, type, closePopup, openPopup } = usePopup();
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    const form = e.target as HTMLFormElement;
    if (!form.checkValidity()) { form.reportValidity(); return; }

    const formData = new FormData(form);
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;

    setIsLoading(true);
    try {
      if (type === 'login') {
        const result = await apiLogin(email, password);
        localStorage.setItem('token', result.data.token);
        localStorage.setItem('user', JSON.stringify(result.data.user));
        closePopup();
        navigate('/dashboard');
      } else {
        const name = formData.get('name') as string;
        await apiRegister(name, email, password);
        setIsSubmitted(true);
        setTimeout(() => {
          setIsSubmitted(false);
          openPopup('login');
        }, 3000);
      }
    } catch (err: any) {
      setError(err.message ?? 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closePopup}
            className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-md"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-x-4 md:inset-x-auto top-[10%] md:top-1/2 md:-translate-y-1/2 md:left-1/2 md:-translate-x-1/2 z-[101] md:w-[450px] max-h-[80vh] overflow-y-auto glass rounded-2xl shadow-2xl p-6 md:p-8 border border-white/10"
          >
            <button
              onClick={closePopup}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition z-10"
            >
              <X size={24} />
            </button>

            {isSubmitted && type === 'signup' ? (
              <div className="flex flex-col items-center justify-center py-10 space-y-4">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 200, damping: 10 }}
                >
                  <CheckCircle size={64} className="text-[#22C55E]" />
                </motion.div>
                <h3 className="text-2xl font-bold text-center">Account Created!</h3>
                <p className="text-slate-400 text-center">
                  You can now log in with your credentials.
                </p>
                <button
                  onClick={() => { setIsSubmitted(false); openPopup('login'); }}
                  className="mt-6 w-full py-3 rounded-lg bg-[#0EA5E9] hover:bg-[#38BDF8] text-white font-medium transition"
                >
                  Go to Login
                </button>
              </div>
            ) : (
              <>
                <h2 className="text-2xl font-bold mb-2">
                  {type === 'login' ? 'Welcome Back' : 'Create an Account'}
                </h2>
                <p className="text-slate-400 mb-6 text-sm">
                  {type === 'login'
                    ? 'Enter your credentials to access your dashboard.'
                    : 'Sign up to experience the future of meetings.'}
                </p>

                {error && (
                  <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                    {error}
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                  {type === 'signup' && (
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-slate-300">Full Name</label>
                      <input
                        required
                        name="name"
                        type="text"
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-[#38BDF8] focus:ring-1 focus:ring-[#38BDF8] outline-none transition"
                        placeholder="John Doe"
                      />
                    </div>
                  )}

                  <div className="space-y-1">
                    <label className="text-xs font-medium text-slate-300">Email Address</label>
                    <input
                      required
                      name="email"
                      type="email"
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-[#38BDF8] focus:ring-1 focus:ring-[#38BDF8] outline-none transition"
                      placeholder="john@example.com"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-medium text-slate-300">Password</label>
                    <input
                      required
                      name="password"
                      type="password"
                      minLength={6}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-[#38BDF8] focus:ring-1 focus:ring-[#38BDF8] outline-none transition"
                      placeholder="••••••••"
                    />
                  </div>

                  {type === 'signup' && (
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-slate-300">Company Name (Optional)</label>
                      <input
                        name="company"
                        type="text"
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-[#38BDF8] focus:ring-1 focus:ring-[#38BDF8] outline-none transition"
                        placeholder="Acme Corp"
                      />
                    </div>
                  )}

                  <div className="pt-4 flex flex-col space-y-4">
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="w-full bg-[#0EA5E9] hover:bg-[#38BDF8] disabled:opacity-60 disabled:cursor-not-allowed text-white py-3 rounded-lg font-bold shadow-[0_0_15px_rgba(14,165,233,0.5)] transition flex items-center justify-center gap-2"
                    >
                      {isLoading && <Loader2 size={16} className="animate-spin" />}
                      {type === 'login' ? 'Login' : 'Sign Up'}
                    </button>

                    <div className="text-center text-sm text-slate-400">
                      {type === 'login' ? (
                        <>
                          Don't have an account?{' '}
                          <button type="button" onClick={() => { setError(''); openPopup('signup'); }} className="text-[#38BDF8] hover:text-white transition font-medium">
                            Sign up
                          </button>
                        </>
                      ) : (
                        <>
                          Already have an account?{' '}
                          <button type="button" onClick={() => { setError(''); openPopup('login'); }} className="text-[#38BDF8] hover:text-white transition font-medium">
                            Login
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </form>
              </>
            )}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
