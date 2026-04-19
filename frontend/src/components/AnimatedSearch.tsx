import { motion, AnimatePresence } from 'framer-motion';
import { Search, X, Clock, FileText, CheckSquare } from 'lucide-react';
import { useState, useRef } from 'react';
import { useTheme } from '../context/ThemeContext';

const RECENT_SEARCHES = [
  'Q4 planning decisions',
  'Mike Rodriguez tasks',
  'November launch',
  'Design system review',
];

const QUICK_RESULTS = [
  { type: 'meeting', icon: FileText, title: 'Q4 Planning Session', subtitle: 'Today • 52 min' },
  { type: 'task', icon: CheckSquare, title: 'Pricing analysis draft', subtitle: 'Mike Rodriguez • Wed' },
  { type: 'meeting', icon: FileText, title: 'Engineering Sync', subtitle: 'Yesterday • 38 min' },
];

export default function AnimatedSearch() {
  const { isDark } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleOpen = () => {
    setIsOpen(true);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  return (
    <div className="relative w-full max-w-md">

      {/* Search Input */}
      <motion.div
        animate={{ width: isOpen ? '100%' : '100%' }}
        className={`flex items-center space-x-3 px-4 py-2.5 rounded-xl border transition-all duration-300 ${
          isDark
            ? isOpen
              ? 'bg-[#1a1f2e] border-app-primary/50 shadow-lg shadow-app-primary/10'
              : 'bg-white/5 border-white/10 hover:border-white/20'
            : isOpen
              ? 'bg-white border-app-primary shadow-lg shadow-app-primary/10'
              : 'bg-slate-100 border-slate-200 hover:border-slate-300'
        }`}
        onClick={handleOpen}
      >
        <motion.div animate={{ scale: isOpen ? 1.1 : 1 }}>
          <Search className={isOpen ? 'text-app-primary' : 'text-slate-500'} size={18} />
        </motion.div>

        <input
          ref={inputRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={handleOpen}
          placeholder="Search items..."
          className={`flex-1 bg-transparent text-sm outline-none placeholder-slate-500 transition-colors ${
            isDark ? 'text-white' : 'text-slate-900'
          }`}
        />

        <AnimatePresence>
          {query && (
            <motion.button
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
              onClick={e => { e.stopPropagation(); setQuery(''); }}
              className={`w-5 h-5 rounded-full flex items-center justify-center transition-colors ${
                isDark ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'
              }`}
            >
              <X size={12} />
            </motion.button>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Search Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Results */}
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.97 }}
              transition={{ duration: 0.2 }}
              className={`absolute top-full mt-2 w-full rounded-xl border shadow-2xl z-50 overflow-hidden transition-colors ${
                isDark
                  ? 'bg-[#1a1f2e] border-white/10'
                  : 'bg-white border-slate-200'
              }`}
            >
              {!query ? (
                // Recent Searches
                <div className="p-4">
                  <p className="text-[10px] font-bold uppercase tracking-widest mb-3 text-slate-500">
                    Recent Searches
                  </p>
                  <div className="space-y-1">
                    {RECENT_SEARCHES.map((search, i) => (
                      <motion.button
                        key={i}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.05 }}
                        onClick={() => setQuery(search)}
                        className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm transition ${
                          isDark
                            ? 'hover:bg-white/5 text-slate-300'
                            : 'hover:bg-slate-50 text-slate-700'
                        }`}
                      >
                        <Clock className="text-slate-500" size={16} />
                        <span>{search}</span>
                      </motion.button>
                    ))}
                  </div>
                </div>
              ) : (
                // Quick Results
                <div className="p-4">
                  <p className="text-[10px] font-bold uppercase tracking-widest mb-3 text-slate-500">
                    Quick Results
                  </p>
                  <div className="space-y-1">
                    {QUICK_RESULTS.map((result, i) => (
                      <motion.button
                        key={i}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition ${
                          isDark ? 'hover:bg-white/5' : 'hover:bg-slate-50'
                        }`}
                      >
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          result.type === 'meeting' ? 'bg-indigo-500/20' : 'bg-teal-500/20'
                        }`}>
                          <result.icon className={result.type === 'meeting' ? 'text-indigo-400' : 'text-teal-400'} size={16} />
                        </div>
                        <div className="flex-1 text-left">
                          <p className={`font-medium transition-colors ${isDark ? 'text-white' : 'text-slate-900'}`}>
                            {result.title}
                          </p>
                          <p className="text-slate-500 text-xs">
                            {result.subtitle}
                          </p>
                        </div>
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
