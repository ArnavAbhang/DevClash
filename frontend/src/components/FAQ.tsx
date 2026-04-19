import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';

const faqs = [
  {
    q: "Is MeetNova AI secure?",
    a: "Yes. We use enterprise-grade encryption and ensure your meeting notes are kept private. We do not use your private data to train our AI models."
  },
  {
    q: "Does it work with Zoom?",
    a: "MeetNova AI works out-of-the-box with Zoom, Google Meet, and Microsoft Teams. No complex setup is required."
  },
  {
    q: "Can I export reports?",
    a: "Absolutely. You can export summaries and action items to Notion, Slack, Jira, or download them as PDF/CSV files."
  },
  {
    q: "Does it support mobile?",
    a: "Our responsive dashboard allows you to access meeting transcripts and action items on any device on the go."
  }
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="py-24 bg-[#0a0f1f]">
      <div className="max-w-3xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Frequently Asked <span className="text-[#38BDF8]">Questions</span>
          </h2>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, idx) => (
            <div 
              key={idx}
              className="glass rounded-2xl overflow-hidden border border-white/10"
            >
              <button
                onClick={() => setOpenIndex(openIndex === idx ? null : idx)}
                className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-white/5 transition"
              >
                <span className="font-semibold text-lg">{faq.q}</span>
                <motion.div
                  animate={{ rotate: openIndex === idx ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <ChevronDown className="text-[#38BDF8]" size={20} />
                </motion.div>
              </button>
              <AnimatePresence>
                {openIndex === idx && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="px-6 pb-5 text-slate-400">
                      {faq.a}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
