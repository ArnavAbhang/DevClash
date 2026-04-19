import { motion } from 'framer-motion';
import { ArrowRight, Play, CheckCircle2, Zap, MessageSquare, Plus } from 'lucide-react';
import { usePopup } from '../context/PopupContext';

export default function Hero() {
  const { openPopup } = usePopup();

  return (
    <section className="relative min-h-screen pt-32 pb-20 overflow-hidden bg-[#0A0F1F]">
      
      {/* Background Particles / Glows */}
      <div className="absolute top-40 right-20 w-96 h-96 rounded-full blur-[150px] opacity-40 bg-[#0EA5E9]/30 pointer-events-none" />
      <div className="absolute bottom-40 left-10 w-96 h-96 rounded-full blur-[150px] opacity-30 bg-[#22D3EE]/20 pointer-events-none" />
      
      {/* Light Particles */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4IiBoZWlnaHQ9IjgiPgo8Y2lyY2xlIGN4PSI0IiBjeT0iNCIgcj0iMSIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjAyKSIvPgpcjwvc3ZnPg==')] pointer-events-none opacity-50" />

      <div className="relative max-w-7xl mx-auto px-6">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          
          {/* LEFT SIDE */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            {/* Small Badge */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center space-x-2 border border-white/10 rounded-full px-4 py-2 mb-6 bg-white/5 backdrop-blur-md"
            >
              <Zap className="text-[#38BDF8]" size={16} />
              <span className="text-xs font-bold tracking-widest uppercase text-slate-300">Smart Workflow Automation</span>
            </motion.div>

            {/* Large headline */}
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold leading-tight mb-6">
              Turn Every Meeting Into{' '}
              <span className="bg-gradient-to-r from-[#0EA5E9] to-[#22D3EE] bg-clip-text text-transparent">
                Actionable Intelligence.
              </span>
            </h1>

            {/* Subheadline */}
            <p className="text-lg md:text-xl text-slate-400 mb-8 leading-relaxed max-w-lg">
              The AI assistant that listens to your meetings, captures screenshots, extracts tasks, writes summaries, tracks decisions, and keeps your team aligned in real time.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 mb-10">
              <motion.button
                onClick={() => openPopup()}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="bg-[#0EA5E9] hover:bg-[#38BDF8] text-white px-8 py-4 rounded-xl font-bold flex items-center justify-center space-x-3 transition shadow-[0_0_20px_rgba(14,165,233,0.4)]"
              >
                <span>Get Started Free</span>
                <ArrowRight size={20} />
              </motion.button>

              <motion.button
                onClick={() => openPopup()}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="glass hover:bg-white/10 text-white border-white/20 px-8 py-4 rounded-xl font-bold flex items-center justify-center space-x-3 transition"
              >
                <Play size={20} className="text-[#38BDF8]" />
                <span>Watch Demo</span>
              </motion.button>
            </div>

            {/* Feature pills below buttons */}
            <div className="flex flex-wrap items-center gap-4">
              {['Live Capture', 'Dynamic Sync', 'Predictive Risks'].map((feat, i) => (
                <div key={i} className="flex items-center space-x-2 text-slate-400 text-sm">
                  <CheckCircle2 size={16} className="text-[#22C55E]" />
                  <span>{feat}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* RIGHT SIDE: Product Mockup */}
          <div className="relative h-[600px] lg:h-[700px] flex items-center justify-center">
            
            {/* Floating Cards */}
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="absolute top-10 -left-10 z-30 glass border-white/10 rounded-xl px-4 py-3 shadow-2xl flex items-center space-x-3"
            >
              <div className="w-8 h-8 rounded-full bg-[#0EA5E9]/20 flex items-center justify-center">
                <CheckCircle2 size={16} className="text-[#0EA5E9]" />
              </div>
              <div>
                <div className="text-sm font-semibold text-white">Task Detected</div>
                <div className="text-xs text-slate-400">Assigned to Rahul</div>
              </div>
            </motion.div>

            <motion.div
              animate={{ y: [0, 10, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
              className="absolute bottom-20 -right-4 z-30 glass border-white/10 rounded-xl px-4 py-3 shadow-2xl flex items-center space-x-3"
            >
              <div className="w-8 h-8 rounded-full bg-[#22C55E]/20 flex items-center justify-center">
                <MessageSquare size={16} className="text-[#22C55E]" />
              </div>
              <div>
                <div className="text-sm font-semibold text-white">Summary Generated</div>
                <div className="text-xs text-slate-400">Sync complete</div>
              </div>
            </motion.div>

            {/* Main Mockup Browser Frame */}
            <div className="absolute inset-0 glass rounded-3xl border-white/10 shadow-2xl overflow-hidden flex flex-col transform perspective-1000 rotateY-[-5deg] rotateX-[2deg]">
              
              <div className="h-10 border-b border-white/10 flex items-center px-4 space-x-2 bg-[#202124]">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
                <div className="ml-4 bg-[#3C4043] rounded px-3 py-1 flex items-center w-full max-w-sm">
                  <span className="text-[10px] text-white/70 font-medium tracking-wide">meet.google.com/xqz-vjmp-qas</span>
                </div>
              </div>

              {/* Layout: Left = Google Meet Video Area, Right = MeetNova Extension Overlay */}
              <div className="flex-1 flex overflow-hidden relative bg-[#202124]">
                {/* Google Meet Video Area */}
                <div className="flex-1 p-4 flex flex-col pb-20 relative">
                  <div className="grid grid-cols-2 gap-4 flex-1">
                    <div className="rounded-xl bg-[#3C4043] overflow-hidden border border-transparent relative">
                       <img src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=500&h=400&fit=crop" alt="person" className="w-full h-full object-cover" />
                       <div className="absolute bottom-3 left-3 bg-black/60 px-2 py-1 flex items-center space-x-2 rounded">
                         <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                         <span className="text-xs text-white">Sarah (Product)</span>
                       </div>
                    </div>
                    <div className="rounded-xl bg-[#3C4043] overflow-hidden border border-transparent relative">
                       <img src="https://images.unsplash.com/photo-1560250097-0b93528c311a?w=500&h=400&fit=crop" alt="person" className="w-full h-full object-cover" />
                       <div className="absolute bottom-3 left-3 bg-black/60 px-2 py-1 rounded">
                         <span className="text-xs text-white">Rahul (Engineering)</span>
                       </div>
                    </div>
                    {/* Bot Participant */}
                    <div className="col-span-2 rounded-xl bg-gradient-to-br from-[#0EA5E9]/20 to-[#38BDF8]/10 overflow-hidden border border-[#0EA5E9]/30 relative flex items-center justify-center">
                       <div className="flex flex-col items-center">
                         <div className="w-12 h-12 bg-[#0EA5E9] rounded-full flex items-center justify-center mb-2 shadow-[0_0_15px_rgba(14,165,233,0.5)]">
                           <span className="text-white font-bold text-xl">MN</span>
                         </div>
                         <div className="text-white font-medium text-sm">MeetNova Notetaker</div>
                       </div>
                       <div className="absolute top-3 right-3 bg-red-500 text-white text-[10px] uppercase font-bold px-2 py-0.5 rounded flex items-center space-x-1">
                         <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse-slow"/>
                         <span>Rec</span>
                       </div>
                    </div>
                  </div>

                  {/* Mock Google Meet Bottom Bar */}
                  <div className="absolute bottom-0 left-0 w-full h-16 border-t border-white/5 flex items-center justify-center space-x-4 bg-[#202124]">
                    <div className="w-10 h-10 rounded-full bg-[#3C4043] flex items-center justify-center border border-transparent hover:bg-[#4d5154]" />
                    <div className="w-10 h-10 rounded-full bg-[#3C4043] flex items-center justify-center border border-transparent hover:bg-[#4d5154]" />
                    <div className="w-10 h-10 rounded-full bg-[#3C4043] flex items-center justify-center border border-transparent hover:bg-[#4d5154]" />
                    <div className="w-12 h-10 rounded-3xl bg-red-500/90 flex items-center justify-center text-white font-medium mx-2" />
                  </div>
                </div>

                {/* Floating MeetNova Extension Chrome Extension style */}
                <div className="absolute top-4 right-4 bottom-4 w-72 rounded-2xl shadow-2xl glass border border-white/10 flex flex-col overflow-hidden bg-[#0A0F1F]/90 backdrop-blur-2xl">
                  <div className="p-3 border-b border-white/10 bg-[#111827]/80">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center space-x-2">
                        <div className="w-6 h-6 rounded bg-[#0EA5E9] flex items-center justify-center">
                          <span className="text-white font-bold text-[10px]">MN</span>
                        </div>
                        <span className="text-xs font-bold text-slate-200 tracking-wide">MeetNova AI</span>
                      </div>
                      <span className="text-[10px] text-[#0EA5E9] border border-[#0EA5E9]/30 bg-[#0EA5E9]/10 px-2 py-0.5 rounded font-medium flex items-center gap-1">
                        <div className="w-1 h-1 bg-[#0EA5E9] rounded-full animate-pulse"/> Tracking
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex-1 p-3 overflow-y-auto space-y-4 font-sans no-scrollbar">
                    {/* Live Transcript / Insights */}
                    <div className="space-y-2">
                      <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Live Insights</div>
                      <div className="bg-white/5 rounded-lg p-2.5 text-[11px] text-slate-300 leading-relaxed border border-white/5 relative">
                        <div className="absolute -left-[1px] top-2 bottom-2 w-0.5 bg-[#0EA5E9] rounded-full" />
                        <span className="text-[#38BDF8] font-semibold">Sarah:</span> "Let's ensure the dashboard handles Zoom links smoothly."
                      </div>
                    </div>

                    {/* Action Items */}
                    <div className="space-y-2">
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex justify-between">
                        <span>Action Items</span>
                        <span className="text-[#38BDF8]">2 Open</span>
                      </div>
                      <div className="bg-[#0EA5E9]/10 border border-[#0EA5E9]/20 rounded-lg p-3 text-xs text-white flex items-start space-x-2">
                        <CheckCircle2 size={14} className="text-[#0EA5E9] mt-0.5 shrink-0" />
                        <span>Rahul to schedule DevOps sync by Thursday</span>
                      </div>
                      <div className="bg-white/5 border border-white/5 rounded-lg p-3 text-xs text-slate-400 flex items-start space-x-2">
                        <CheckCircle2 size={14} className="text-slate-500 mt-0.5 shrink-0" />
                        <span>Sarah to finalize copy</span>
                      </div>
                    </div>

                    {/* Screenshot Captured */}
                    <div className="space-y-2">
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Visual Context</div>
                      <div className="border border-white/5 rounded-lg overflow-hidden relative">
                        <div className="h-16 bg-gradient-to-tr from-indigo-900 to-slate-800 flex items-center justify-center">
                          <span className="text-[10px] text-white/50">Roadmap Chart</span>
                        </div>
                        <div className="absolute top-1 right-1 bg-black/60 px-1 rounded text-[8px] text-white">Captured</div>
                      </div>
                    </div>
                  </div>

                  {/* Ask Box */}
                  <div className="p-3 border-t border-white/10 bg-[#111827]">
                    <div className="bg-black/50 border border-white/10 rounded-lg p-2 flex items-center justify-between">
                      <span className="text-xs text-slate-500">Ask AI about this meeting...</span>
                      <Plus size={14} className="text-slate-400" />
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
