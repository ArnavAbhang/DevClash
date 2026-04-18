import { motion, AnimatePresence } from 'motion/react';
import { Check } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import React from 'react';

interface AnimatedCheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  owner?: string;
  priority?: 'high' | 'medium' | 'low';
}

const AnimatedCheckbox: React.FC<AnimatedCheckboxProps> = ({
  checked,
  onChange,
  label,
  owner,
  priority = 'medium',
}) => {
  const { isDark } = useTheme();

  const checkboxColor = checked
    ? 'bg-app-primary border-app-primary'
    : isDark
      ? 'bg-transparent border-slate-600 hover:border-app-primary/50'
      : 'bg-transparent border-slate-300 hover:border-app-primary/50';

  return (
    <motion.label
      className={`flex items-start space-x-3 p-4 rounded-xl border cursor-pointer transition-all duration-200 group ${
        checked
          ? isDark
            ? 'bg-emerald-900/10 border-emerald-500/20 opacity-70'
            : 'bg-emerald-50 border-emerald-200 opacity-70 shadow-sm'
          : isDark
            ? 'bg-white/3 border-white/10 hover:border-app-primary/30 hover:bg-white/5'
            : 'bg-white border-slate-200 hover:border-app-primary/30 hover:shadow-md'
      }`}
      whileHover={{ scale: 1.005 }}
      whileTap={{ scale: 0.998 }}
    >
      {/* Checkbox */}
      <button
        type="button"
        onClick={(e) => { e.preventDefault(); onChange(!checked); }}
        className={`relative w-5 h-5 rounded-md border-2 flex-shrink-0 mt-0.5 flex items-center justify-center transition-all duration-200 ${checkboxColor}`}
      >
        <AnimatePresence>
          {checked && (
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            >
              <Check className="text-white" size={12} strokeWidth={3} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Ripple effect */}
        <AnimatePresence>
          {checked && (
            <motion.div
              initial={{ scale: 1, opacity: 0.4 }}
              animate={{ scale: 2.5, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
              className="absolute inset-0 rounded-md bg-app-primary"
            />
          )}
        </AnimatePresence>
      </button>

      {/* Task Content */}
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium transition-all duration-300 ${
          checked
            ? 'line-through text-slate-500'
            : isDark ? 'text-white' : 'text-slate-900'
        }`}>
          {label}
        </p>
        {owner && (
          <p className="text-[10px] uppercase font-bold text-slate-500 mt-1 opacity-60">
            {owner}
          </p>
        )}
      </div>

      {/* Priority Dot */}
      <div className={`w-2 h-2 rounded-full flex-shrink-0 mt-2 ${
        priority === 'high' ? 'bg-rose-500' :
        priority === 'medium' ? 'bg-amber-500' :
        'bg-emerald-500'
      }`} />
    </motion.label>
  );
};

export default AnimatedCheckbox;
