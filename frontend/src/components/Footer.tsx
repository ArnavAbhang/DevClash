import { Globe, X, ExternalLink, Code } from 'lucide-react';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-[#0A0F1F] border-t border-white/10 pt-16 pb-8">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8 mb-12">
          
          <div className="col-span-2 lg:col-span-2">
            <a href="/" className="inline-flex items-center space-x-2 mb-6 cursor-pointer">
              <div className="w-8 h-8 bg-gradient-to-br from-[#0EA5E9] to-[#22D3EE] rounded flex items-center justify-center shadow-[0_0_10px_rgba(14,165,233,0.5)]">
                <span className="text-white font-bold text-sm tracking-tighter">MN</span>
              </div>
              <span className="font-bold text-lg uppercase tracking-widest text-[#F8FAFC]">
                MeetNova AI
              </span>
            </a>
            <p className="text-slate-400 text-sm max-w-sm leading-relaxed mb-6">
              Empowering modern teams to extract maximum value from every conversation through state-of-the-art AI intelligence.
            </p>
            <div className="flex space-x-4">
              <a href="#" className="text-slate-400 hover:text-[#38BDF8] transition"><X size={20} /></a>
              <a href="#" className="text-slate-400 hover:text-[#38BDF8] transition"><ExternalLink size={20} /></a>
              <a href="#" className="text-slate-400 hover:text-[#38BDF8] transition"><Globe size={20} /></a>
              <a href="#" className="text-slate-400 hover:text-[#38BDF8] transition"><Code size={20} /></a>
            </div>
          </div>

          <div>
            <h4 className="font-bold text-white mb-4 tracking-wide">Product</h4>
            <ul className="space-y-3">
              <li><a href="#features" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">Features</a></li>
              <li><a href="#insights" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">AI Insights</a></li>
              <li><a href="#" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">Integrations</a></li>
              <li><a href="#" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">Changelog</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-bold text-white mb-4 tracking-wide">Company</h4>
            <ul className="space-y-3">
              <li><a href="#about" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">About Us</a></li>
              <li><a href="#pricing" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">Pricing</a></li>
              <li><a href="#" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">Careers</a></li>
              <li><a href="#contact" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">Contact</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-bold text-white mb-4 tracking-wide">Legal</h4>
            <ul className="space-y-3">
              <li><a href="#" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">Privacy Policy</a></li>
              <li><a href="#" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">Terms of Service</a></li>
              <li><a href="#" className="text-sm text-slate-400 hover:text-[#38BDF8] transition">Cookie Policy</a></li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-white/10 flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
          <p className="text-sm text-slate-500">
            &copy; {currentYear} MeetNova AI Inc. All rights reserved.
          </p>
          <div className="flex space-x-6 text-sm text-slate-500">
            <span>Status: Operational</span>
            <span>Made in USA</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
