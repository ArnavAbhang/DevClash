import { motion } from 'framer-motion';
import { Quote } from 'lucide-react';

const testimonials = [
  {
    quote: "This saved our weekly meetings. I no longer spend 30 minutes writing summaries.",
    name: "Alex Johnson",
    role: "Product Manager at TechFlow",
    avatar: "https://i.pravatar.cc/150?u=1"
  },
  {
    quote: "Best productivity tool for remote teams. Action items are always clear.",
    name: "Sarah Williams",
    role: "VP of Engineering at CloudSync",
    avatar: "https://i.pravatar.cc/150?u=2"
  },
  {
    quote: "We never miss tasks anymore. The integration with Jira works perfectly.",
    name: "Michael Chen",
    role: "Scrum Master at DevWorks",
    avatar: "https://i.pravatar.cc/150?u=3"
  }
];

export default function Testimonials() {
  return (
    <section className="py-24 relative bg-[#0a0f1f]">
      <div className="absolute top-0 right-0 w-1/2 h-1/2 bg-[#38BDF8]/5 blur-[120px] rounded-full pointer-events-none" />
      
      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Loved By <span className="text-[#38BDF8]">Modern Teams</span>
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {testimonials.map((t, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.2 }}
              className="glass p-8 rounded-3xl relative"
            >
              <Quote className="text-[#38BDF8]/20 absolute top-6 right-6" size={48} />
              
              <div className="mb-6 relative z-10 pt-4">
                <p className="text-lg text-slate-300 italic leading-relaxed">
                  "{t.quote}"
                </p>
              </div>

              <div className="flex items-center space-x-4">
                <img 
                  src={t.avatar} 
                  alt={t.name}
                  className="w-12 h-12 rounded-full border-2 border-[#111827]"
                />
                <div>
                  <div className="font-bold text-white">{t.name}</div>
                  <div className="text-sm text-slate-400">{t.role}</div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
