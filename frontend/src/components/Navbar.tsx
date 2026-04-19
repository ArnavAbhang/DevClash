import { motion } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { usePopup } from '../context/PopupContext';

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const { openPopup } = usePopup();

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 w-full glass z-50 !bg-[#0A0F1F]/80"
    >
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        
        {/* Logo */}
        <a href="/" className="flex items-center space-x-2 group">
          <div className="w-10 h-10 bg-gradient-to-br from-[#0EA5E9] to-[#22D3EE] rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(14,165,233,0.5)] group-hover:shadow-[0_0_25px_rgba(14,165,233,0.7)] transition">
            <span className="text-white font-bold text-xl tracking-tighter">MN</span>
          </div>
          <span className="font-bold text-xl uppercase tracking-widest text-[#F8FAFC]">
            MeetNova AI
          </span>
        </a>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center space-x-8">
          <a href="#features" className="text-slate-400 hover:text-white transition text-sm font-medium tracking-wide">Features</a>
          <a href="#solutions" className="text-slate-400 hover:text-white transition text-sm font-medium tracking-wide">Solutions</a>
          <a href="#pricing" className="text-slate-400 hover:text-white transition text-sm font-medium tracking-wide">Pricing</a>
          <a href="#insights" className="text-slate-400 hover:text-white transition text-sm font-medium tracking-wide">AI Insights</a>
        </div>

        {/* CTA Buttons */}
        <div className="hidden md:flex items-center space-x-4">
          <button onClick={() => openPopup('login')} className="text-slate-400 hover:text-white transition text-sm font-medium">
            Login
          </button>
          <motion.button
            onClick={() => openPopup()}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="bg-[#0EA5E9] hover:bg-[#38BDF8] text-white px-6 py-2.5 rounded-xl font-bold transition shadow-[0_0_15px_rgba(14,165,233,0.5)]"
          >
            Get Started
          </motion.button>
        </div>

        {/* Mobile Menu Toggle */}
        <div className="flex items-center md:hidden">
          <button 
            onClick={() => setIsOpen(!isOpen)}
            className="text-white hover:text-[#38BDF8] transition"
          >
            {isOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="md:hidden border-t border-white/10 bg-[#0A0F1F]"
        >
          <div className="px-6 py-6 space-y-4">
            <a href="#features" className="block text-slate-400 hover:text-[#38BDF8] font-medium">Features</a>
            <a href="#solutions" className="block text-slate-400 hover:text-[#38BDF8] font-medium">Solutions</a>
            <a href="#pricing" className="block text-slate-400 hover:text-[#38BDF8] font-medium">Pricing</a>
            <a href="#insights" className="block text-slate-400 hover:text-[#38BDF8] font-medium">AI Insights</a>
            <div className="pt-4 border-t border-white/10 space-y-4">
              <button onClick={() => { setIsOpen(false); openPopup('login'); }} className="block w-full text-left text-slate-400 hover:text-white font-medium">
                Login
              </button>
              <button onClick={() => openPopup()} className="w-full bg-[#0EA5E9] text-white py-3 rounded-xl font-bold">
                Get Started
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </motion.nav>
  );
}
