import { motion } from 'framer-motion';

const stats = [
  { value: "500+", label: "Teams" },
  { value: "10K+", label: "Meetings Processed" },
  { value: "98%", label: "Time Saved" },
  { value: "4.9/5", label: "User Rating" }
];

export default function SocialProof() {
  return (
    <section className="py-16 border-y border-white/5 bg-[#111827]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              className="text-center"
            >
              <div className="text-4xl md:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-[#0EA5E9] to-[#22D3EE] mb-2">
                {stat.value}
              </div>
              <div className="text-sm text-slate-400 uppercase tracking-widest font-semibold">
                {stat.label}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
