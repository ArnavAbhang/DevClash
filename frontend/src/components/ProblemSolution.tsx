import { motion } from 'motion/react';
import { XCircle, CheckCircle2 } from 'lucide-react';

const problems = [
  "Missed action items",
  "No proper notes",
  "Repeated discussions",
  "Poor accountability"
];

const solutions = [
  "AI transcription",
  "Auto summaries",
  "Smart task extraction",
  "Instant reports"
];

export default function ProblemSolution() {
  return (
    <section className="py-24 relative overflow-hidden bg-[#0a0f1f]" id="solutions">
      {/* Background Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-[#0EA5E9]/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-6">
            Meetings Shouldn't Be a <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-400 to-orange-400">Black Hole</span>
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            Stop losing critical context. MeetNova AI turns talk into tracked, actionable items effortlessly.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 lg:gap-12 items-stretch">
          {/* Problems */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="p-8 rounded-3xl border border-red-500/20 bg-red-500/5 relative overflow-hidden group"
          >
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <XCircle size={100} />
            </div>
            <h3 className="text-2xl font-semibold mb-8 text-red-400">The Problem</h3>
            <ul className="space-y-6">
              {problems.map((prob, idx) => (
                <li key={idx} className="flex items-center space-x-3 text-slate-300">
                  <XCircle className="text-red-500 shrink-0" size={24} />
                  <span className="text-lg">{prob}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Solutions */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="p-8 rounded-3xl border border-[#0EA5E9]/20 bg-[#0EA5E9]/5 relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <CheckCircle2 size={100} className="text-[#0EA5E9]" />
            </div>
            <h3 className="text-2xl font-semibold mb-8 text-[#0EA5E9]">The MeetNova Solution</h3>
            <ul className="space-y-6">
              {solutions.map((sol, idx) => (
                <li key={idx} className="flex items-center space-x-3 text-white">
                  <CheckCircle2 className="text-[#0EA5E9] shrink-0" size={24} />
                  <span className="text-lg font-medium">{sol}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
