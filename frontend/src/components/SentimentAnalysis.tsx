import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { TrendingUp, User, Zap } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface SpeakerSentiment {
  speaker: string;
  avatar: string;
  color: string;
  overallSentiment: 'positive' | 'negative' | 'neutral';
  sentimentScore: number;
  sentiments: { timestamp: string, sentiment: string, score: number, quote: string }[];
}

const MOCK_SPEAKER_SENTIMENT: SpeakerSentiment[] = [
  {
    speaker: 'Sarah Chen',
    avatar: 'SC',
    color: 'from-indigo-500 to-indigo-700',
    overallSentiment: 'positive',
    sentimentScore: 72,
    sentiments: [
      { timestamp: '00:00', sentiment: 'positive', score: 75, quote: '"Alright everyone, let\'s kick off..."' },
      { timestamp: '01:52', sentiment: 'positive', score: 80, quote: '"Let\'s target November 15th..."' },
    ]
  },
  {
    speaker: 'Emily Johnson',
    avatar: 'EJ',
    color: 'from-purple-500 to-purple-700',
    overallSentiment: 'neutral',
    sentimentScore: 45,
    sentiments: [
      { timestamp: '00:41', sentiment: 'neutral', score: 50, quote: '"I need to follow up..."' },
      { timestamp: '01:35', sentiment: 'negative', score: 40, quote: '"...we still haven\'t made a decision..."' },
    ]
  },
];

const TIMELINE = [
  { time: '00:00', val: 70 },
  { time: '00:45', val: 60 },
  { time: '01:30', val: 45 },
  { time: '02:00', val: 75 },
  { time: '02:45', val: 65 },
];

function SpeakerCard({ speaker, index }: { speaker: SpeakerSentiment, index: number, key?: any }) {
  const [expanded, setExpanded] = useState(false);
  const { isDark } = useTheme();
  
  const colorMap = {
    positive: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20',
    negative: 'text-rose-500 bg-rose-500/10 border-rose-500/20',
    neutral: 'text-slate-500 bg-slate-500/10 border-slate-500/20',
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }} 
      animate={{ opacity: 1, y: 0 }} 
      transition={{ delay: index * 0.1 }} 
      className={`border rounded-2xl p-5 transition-all ${
        isDark ? 'bg-bg-secondary/50 border-white/10 hover:border-white/20' : 'bg-white border-border-main shadow-sm hover:shadow-md'
      }`}
    >
      <div className="flex items-center justify-between mb-4 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${speaker.color} flex items-center justify-center text-xs font-bold text-white shadow-sm`}>{speaker.avatar}</div>
          <div>
            <h4 className="text-sm font-bold">{speaker.speaker}</h4>
            <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border ${colorMap[speaker.overallSentiment]}`}>{speaker.overallSentiment}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold">{speaker.sentimentScore}%</div>
          <div className="text-[10px] text-slate-500 uppercase tracking-widest font-mono">Index</div>
        </div>
      </div>
      <div className={`w-full h-1.5 rounded-full overflow-hidden transition-colors ${isDark ? 'bg-white/5' : 'bg-slate-100'}`}>
         <motion.div initial={{ width: 0 }} animate={{ width: `${speaker.sentimentScore}%` }} className={`h-full bg-gradient-to-r ${speaker.color}`} />
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }} 
            animate={{ opacity: 1, height: 'auto' }} 
            exit={{ opacity: 0, height: 0 }} 
            className={`mt-4 pt-4 border-t space-y-3 transition-colors ${isDark ? 'border-white/5' : 'border-slate-100'}`}
          >
            {speaker.sentiments.map((s, i) => (
              <div key={i} className="flex items-start space-x-3 text-[11px]">
                 <span className="text-slate-500 font-mono flex-shrink-0">{s.timestamp}</span>
                 <p className="text-slate-500 italic leading-relaxed">{s.quote}</p>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function SentimentAnalysis() {
  const { isDark } = useTheme();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Sentiment Intelligence</h1>
        <p className="text-slate-500">Emotional mapping of the conversation dynamics.</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
           <div className={`border rounded-2xl p-6 transition-colors ${
             isDark ? 'bg-bg-secondary border-white/10' : 'bg-white border-border-main shadow-sm'
           }`}>
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-lg font-bold flex items-center space-x-2">
                  <TrendingUp size={18} className="text-app-primary" />
                  <span>Mood Timeline</span>
                </h3>
                <div className="text-3xl font-bold">72% <span className="text-xs font-medium text-slate-500 uppercase tracking-widest ml-1">AVG POSITIVITY</span></div>
              </div>
              <div className="flex items-end justify-between h-40 px-4 group">
                 {TIMELINE.map((p, i) => (
                   <div key={i} className="relative flex flex-col items-center flex-1">
                      <motion.div 
                        initial={{ height: 0 }} 
                        animate={{ height: `${p.val}%` }} 
                        transition={{ delay: i * 0.1 }} 
                        className={`w-4 rounded-t-lg transition-all relative ${
                          isDark ? 'bg-app-primary/40 hover:bg-app-primary' : 'bg-app-primary/60 hover:bg-app-primary shadow-sm shadow-app-primary/20'
                        }`}
                      >
                         <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] font-mono text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity">{p.val}%</div>
                      </motion.div>
                      <span className="text-[10px] text-slate-500 font-mono mt-3 uppercase">{p.time}</span>
                   </div>
                 ))}
              </div>
           </div>

           <div className="grid md:grid-cols-2 gap-6">
             {MOCK_SPEAKER_SENTIMENT.map((s, i) => <SpeakerCard key={s.speaker} speaker={s} index={i} />)}
           </div>
        </div>

        <div className="space-y-6">
           <div className={`border rounded-2xl p-6 transition-colors ${
             isDark ? 'bg-app-primary/10 border-indigo-500/20' : 'bg-indigo-50 border-indigo-100'
           }`}>
              <h3 className="text-lg font-bold flex items-center space-x-2 mb-4">
                <Zap size={18} className="text-app-primary" />
                <span>Key Observations</span>
              </h3>
              <div className="space-y-4">
                {[
                  'Sentiment peaked during the launch target discussion (+15% surge).',
                  'Emily Johnson showed repeated hesitation about the design system.',
                  'Momentum remains high for Q4 goals, current baseline is positive.'
                ].map((text, i) => (
                  <div key={i} className="flex items-start space-x-3">
                     <div className="w-1.5 h-1.5 rounded-full bg-app-primary mt-1.5 flex-shrink-0" />
                     <p className="text-xs text-slate-500 leading-relaxed font-medium">{text}</p>
                  </div>
                ))}
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
