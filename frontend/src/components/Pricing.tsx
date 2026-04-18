import { motion } from 'motion/react';
import { usePopup } from '../context/PopupContext';
import { Check } from 'lucide-react';

const plans = [
  {
    name: "Starter",
    price: "$0",
    period: "/ forever",
    desc: "For individuals trying out AI meetings.",
    features: [
      "5 meetings per month",
      "Standard summaries",
      "30-day history retention",
      "Email support"
    ],
    highlighted: false,
    btn: "Start Free"
  },
  {
    name: "Pro",
    price: "$29",
    period: "/ user / month",
    desc: "Everything you need for productive teams.",
    features: [
      "Unlimited meetings",
      "Advanced AI tasks & screenshots",
      "Unlimited history retention",
      "Jira & Notion integrations",
      "Priority support"
    ],
    highlighted: true,
    btn: "Get Pro"
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    desc: "Advanced security and admin controls.",
    features: [
      "Everything in Pro",
      "Custom integrations API",
      "SSO & advanced security",
      "Dedicated account manager",
      "On-premise option"
    ],
    highlighted: false,
    btn: "Contact Sales"
  }
];

export default function Pricing() {
  const { openPopup } = usePopup();

  return (
    <section className="py-24 relative bg-[#0a0f1f]" id="pricing">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Simple, Transparent <span className="text-[#38BDF8]">Pricing</span>
          </h2>
          <p className="text-slate-400 text-lg">
            Invest in a tool that pays for itself in time saved.
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((plan, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              className={`rounded-3xl p-8 relative flex flex-col ${
                plan.highlighted 
                  ? 'bg-gradient-to-br from-[#111827] to-[#0A0F1F] border-2 border-[#0EA5E9] shadow-[0_0_30px_rgba(14,165,233,0.15)]' 
                  : 'glass border border-white/10'
              }`}
            >
              {plan.highlighted && (
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[#0EA5E9] text-white px-4 py-1 rounded-full text-xs font-bold tracking-wide uppercase">
                  Most Popular
                </div>
              )}
              
              <div className="mb-8">
                <h3 className="text-xl font-medium text-white mb-2">{plan.name}</h3>
                <p className="text-slate-400 text-sm mb-6 h-10">{plan.desc}</p>
                <div className="flex items-end space-x-1">
                  <span className="text-4xl font-bold text-white">{plan.price}</span>
                  <span className="text-slate-400 font-medium mb-1">{plan.period}</span>
                </div>
              </div>

              <div className="flex-1">
                <ul className="space-y-4 mb-8">
                  {plan.features.map((feat, fidx) => (
                    <li key={fidx} className="flex items-start space-x-3">
                      <Check className="text-[#38BDF8] shrink-0 mt-0.5" size={18} />
                      <span className="text-slate-300 text-sm">{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <button
                onClick={openPopup}
                className={`w-full py-3 rounded-xl font-bold transition-all ${
                  plan.highlighted
                    ? 'bg-[#0EA5E9] hover:bg-[#38BDF8] text-white shadow-[0_0_15px_rgba(14,165,233,0.4)]'
                    : 'bg-white/5 hover:bg-white/10 text-white border border-white/10'
                }`}
              >
                {plan.btn}
              </button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
