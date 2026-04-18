import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Mic, FileText, CheckSquare, Image as ImageIcon } from 'lucide-react';

const tabs = [
  { id: 'transcript', label: 'Transcript', icon: Mic },
  { id: 'tasks', label: 'Tasks', icon: CheckSquare },
  { id: 'summary', label: 'Summary', icon: FileText },
  { id: 'screenshots', label: 'Screenshots', icon: ImageIcon },
];

export default function DashboardPreview() {
  const [activeTab, setActiveTab] = useState('transcript');

  return (
    <section className="py-24 relative bg-[#0a0f1f]" id="insights">
      {/* Background element */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-[#0EA5E9]/10 blur-[150px] pointer-events-none" />

      <div className="max-w-6xl mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Interactive <span className="text-[#38BDF8]">Demo</span>
          </h2>
          <p className="text-slate-400 text-lg">
            See exactly what MeetNova AI generates after every call.
          </p>
        </div>

        <div className="glass rounded-[2rem] border-white/10 p-4 md:p-8 shadow-2xl relative overflow-hidden">
          {/* Tab Navigation */}
          <div className="flex flex-wrap md:flex-nowrap items-center gap-2 mb-8 bg-[#111827] p-2 rounded-2xl border border-white/5">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl font-medium transition-all duration-300 ${
                    isActive 
                      ? 'bg-[#0EA5E9] text-white shadow-[0_4px_15px_rgba(14,165,233,0.3)]' 
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Icon size={18} />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content Area */}
          <div className="bg-[#111827]/80 rounded-2xl border border-white/5 min-h-[400px] p-6 md:p-10 relative overflow-hidden">
            <AnimatePresence mode="wait">
              
              {activeTab === 'transcript' && (
                <motion.div
                  key="transcript"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="space-y-6"
                >
                  <div className="flex items-start space-x-4">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex shrink-0 items-center justify-center text-white font-bold">A</div>
                    <div>
                      <div className="flex items-center space-x-2 mb-1">
                        <span className="font-bold text-white">Alex Johnson</span>
                        <span className="text-xs text-slate-500">10:02 AM</span>
                      </div>
                      <p className="text-slate-300 leading-relaxed">
                        So, regarding the next quarter targets, I believe we should focus heavily on user retention. The churn rate last month was higher than expected.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-4">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-teal-500 to-emerald-500 flex shrink-0 items-center justify-center text-white font-bold">S</div>
                    <div>
                      <div className="flex items-center space-x-2 mb-1">
                        <span className="font-bold text-white">Sarah Williams</span>
                        <span className="text-xs text-slate-500">10:04 AM</span>
                      </div>
                      <p className="text-slate-300 leading-relaxed">
                        I agree. I will start drafting a new onboarding flow to help users find value faster. I can have a mockup ready by Thursday.
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}

              {activeTab === 'tasks' && (
                <motion.div
                  key="tasks"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="space-y-4"
                >
                  <div className="glass p-5 rounded-xl flex items-center justify-between hover:border-[#38BDF8]/30 transition group">
                    <div className="flex items-center space-x-4">
                      <div className="w-6 h-6 rounded border-2 border-slate-500 group-hover:border-[#38BDF8] transition" />
                      <div>
                        <p className="font-bold text-white mb-1">Draft new onboarding flow mockups</p>
                        <p className="text-xs text-slate-400">Due: Thursday</p>
                      </div>
                    </div>
                    <div className="bg-[#111827] px-3 py-1 rounded-lg text-xs font-medium text-slate-300 border border-white/10 border-l-[#0EA5E9] border-l-2">
                      Assignee: Sarah
                    </div>
                  </div>
                  <div className="glass p-5 rounded-xl flex items-center justify-between hover:border-[#38BDF8]/30 transition group">
                    <div className="flex items-center space-x-4">
                      <div className="w-6 h-6 rounded border-2 border-slate-500 group-hover:border-[#38BDF8] transition" />
                      <div>
                        <p className="font-bold text-white mb-1">Review churn rate analytics report</p>
                        <p className="text-xs text-slate-400">Due: Tomorrow</p>
                      </div>
                    </div>
                    <div className="bg-[#111827] px-3 py-1 rounded-lg text-xs font-medium text-slate-300 border border-white/10 border-l-[#22C55E] border-l-2">
                      Assignee: Alex
                    </div>
                  </div>
                </motion.div>
              )}

              {activeTab === 'summary' && (
                <motion.div
                  key="summary"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="prose prose-invert max-w-none text-slate-300"
                >
                  <h3 className="text-xl font-bold text-white mb-4">Executive Summary</h3>
                  <p>
                    The team discussed Q4 strategies with a primary focus on improving user retention.
                    Alex highlighted the recent unexpected spike in churn rate.
                    To counter this, Sarah proposed rebuilding the initial user onboarding flow to quickly demonstrate core value.
                  </p>
                  <h4 className="text-lg font-bold text-white mt-6 mb-2">Key Decisions</h4>
                  <ul className="list-disc pl-5 space-y-2">
                    <li>Prioritize user retention over acquisition for Q4.</li>
                    <li>Overhaul the existing onboarding process.</li>
                  </ul>
                </motion.div>
              )}

              {activeTab === 'screenshots' && (
                <motion.div
                  key="screenshots"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="grid grid-cols-2 gap-4"
                >
                  <div className="rounded-xl overflow-hidden border border-white/10 relative group">
                    <div className="absolute inset-0 bg-[#0EA5E9]/20 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                      <span className="bg-black/80 px-3 py-1 rounded text-white text-sm font-bold">View Full</span>
                    </div>
                    <img src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&h=400&fit=crop" alt="Graph" className="w-full h-48 object-cover" />
                    <div className="absolute bottom-0 w-full bg-black/60 p-2 text-xs text-white">Churn Rate Graph.png</div>
                  </div>
                  <div className="rounded-xl overflow-hidden border border-white/10 relative group">
                    <div className="absolute inset-0 bg-[#0EA5E9]/20 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                      <span className="bg-black/80 px-3 py-1 rounded text-white text-sm font-bold">View Full</span>
                    </div>
                    <img src="https://images.unsplash.com/photo-1557804506-669a67965ba0?w=600&h=400&fit=crop" alt="Strategy" className="w-full h-48 object-cover" />
                    <div className="absolute bottom-0 w-full bg-black/60 p-2 text-xs text-white">Q4 Strategy Deck.png</div>
                  </div>
                </motion.div>
              )}

            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
