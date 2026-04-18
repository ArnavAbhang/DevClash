import { motion } from 'motion/react';
import { UploadCloud, Brain, CheckSquare } from 'lucide-react';

const steps = [
  {
    num: "01",
    icon: UploadCloud,
    title: "Start or Upload Meeting",
    desc: "Invite the MeetNova bot to your live call or simply upload an existing recording.",
  },
  {
    num: "02",
    icon: Brain,
    title: "AI Understands Discussion",
    desc: "Our engine accurately transcribes, identifies speakers, and extracts key contextual meaning.",
  },
  {
    num: "03",
    icon: CheckSquare,
    title: "Receive Notes, Tasks & Reports",
    desc: "Instantly get formatted summaries, assigned tasks in Jira/Notion, and shareable reports.",
  }
];

export default function HowItWorks() {
  return (
    <section className="py-24 relative bg-[#111827]" id="how-it-works">
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            How It <span className="text-[#38BDF8]">Works</span>
          </h2>
          <p className="text-slate-400 text-lg">
            From chaotic meeting to structured intelligence in three simple steps.
          </p>
        </div>

        <div className="relative">
          {/* Connecting Line */}
          <div className="absolute top-1/2 left-0 w-full h-1 bg-white/5 -translate-y-1/2 hidden md:block rounded-full" />
          
          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((step, idx) => {
              const Icon = step.icon;
              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.2 }}
                  className="relative z-10 glass p-8 rounded-3xl text-center group hover:border-[#0EA5E9]/50 transition duration-300"
                >
                  <div className="text-[100px] md:text-[120px] font-black absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white/[0.02] z-0 pointer-events-none group-hover:text-white/[0.04] transition">
                    {step.num}
                  </div>
                  
                  <div className="w-16 h-16 rounded-2xl bg-[#0EA5E9]/10 mx-auto mb-6 flex items-center justify-center relative z-10 text-[#0EA5E9]">
                    <Icon size={32} />
                  </div>
                  
                  <h3 className="text-xl font-bold mb-3 text-white relative z-10">{step.title}</h3>
                  <p className="text-slate-400 relative z-10">{step.desc}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
