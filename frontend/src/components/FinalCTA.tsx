import { motion } from 'framer-motion';
import { ArrowRight, Calendar } from 'lucide-react';
import { usePopup } from '../context/PopupContext';

export default function FinalCTA() {
  const { openPopup } = usePopup();

  return (
    <section className="py-24 relative overflow-hidden bg-[#0A0F1F]">
      <div className="absolute inset-0 bg-gradient-to-b from-[#111827] to-[#0A0F1F]" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl h-[400px] bg-[#0EA5E9]/20 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-4xl mx-auto px-6 relative z-10 text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass rounded-3xl p-12 md:p-16 border-white/10 shadow-2xl relative overflow-hidden"
        >
          {/* Subtle Grid Background */}
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none opacity-50" />

          <h2 className="text-4xl md:text-5xl font-extrabold mb-6 text-white relative z-10">
            Your Meetings Deserve <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#0EA5E9] to-[#22D3EE]">
              Better Intelligence.
            </span>
          </h2>
          <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto relative z-10">
            Join thousands of teams who have stopped taking notes and started taking action.
          </p>

          <div className="flex flex-col sm:flex-row justify-center items-center gap-4 relative z-10">
            <motion.button
              onClick={() => openPopup()}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="w-full sm:w-auto bg-[#0EA5E9] hover:bg-[#38BDF8] text-white px-8 py-4 rounded-xl font-bold flex items-center justify-center space-x-2 transition shadow-[0_0_20px_rgba(14,165,233,0.4)]"
            >
              <span>Start Free Today</span>
              <ArrowRight size={20} />
            </motion.button>
            <motion.button
              onClick={() => openPopup()}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="w-full sm:w-auto bg-white/10 hover:bg-white/20 text-white px-8 py-4 rounded-xl font-bold flex items-center justify-center space-x-2 transition border border-white/10"
            >
              <Calendar size={20} />
              <span>Book Demo</span>
            </motion.button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
