import { motion } from 'framer-motion';
import { Mic, FileText, CheckSquare, Camera, BrainCircuit, CalendarClock, Grid3X3, MessageSquareText } from 'lucide-react';

const features = [
  {
    icon: Mic,
    title: "Real-Time Transcription",
    desc: "Capture every word with 99% accuracy across multiple languages."
  },
  {
    icon: FileText,
    title: "AI Summaries",
    desc: "Get instant executive summaries immediately after the call."
  },
  {
    icon: CheckSquare,
    title: "Auto Task Assignment",
    desc: "AI detects action items and assigns them to the right team members."
  },
  {
    icon: Camera,
    title: "Smart Screenshot Capture",
    desc: "Automatically grabs important slides and visual context."
  },
  {
    icon: BrainCircuit,
    title: "Cross-Meeting Insights",
    desc: "Connect the dots between different meetings and projects."
  },
  {
    icon: CalendarClock,
    title: "Calendar Sync",
    desc: "Seamlessly integrates with Google and Outlook calendars."
  },
  {
    icon: Grid3X3,
    title: "Jira / Notion Integration",
    desc: "Push updates directly to your favorite project management tools."
  },
  {
    icon: MessageSquareText,
    title: "Ask AI Anything",
    desc: "Chat with your meeting history to remember any detail."
  }
];

export default function FeaturesGrid() {
  return (
    <section className="py-24 relative bg-[#0a0f1f]" id="features">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Everything You Need for <span className="text-[#38BDF8]">Intelligent Meetings</span>
          </h2>
          <p className="text-slate-400 text-lg">
            A complete suite of tools designed to maximize productivity.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, idx) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
                whileHover={{ y: -5 }}
                className="glass rounded-2xl p-6 group hover:border-[#38BDF8]/50 transition-colors duration-300"
              >
                <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-6 group-hover:bg-[#0EA5E9]/20 transition-colors">
                  <Icon className="text-[#0EA5E9]" size={24} />
                </div>
                <h3 className="text-lg font-bold mb-2 text-white">{feature.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  {feature.desc}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
