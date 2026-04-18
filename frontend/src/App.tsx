import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'motion/react';
import { ToastProvider } from './components/ToastSystem';
import PageTransition from './components/PageTransition';

import Navbar from './components/Navbar';
import Hero from './components/Hero';
import SocialProof from './components/SocialProof';
import ProblemSolution from './components/ProblemSolution';
import FeaturesGrid from './components/FeaturesGrid';
import HowItWorks from './components/HowItWorks';
import DashboardPreview from './components/DashboardPreview';
import Pricing from './components/Pricing';
import Testimonials from './components/Testimonials';
import FAQ from './components/FAQ';
import FinalCTA from './components/FinalCTA';
import Footer from './components/Footer';

import Dashboard from './pages/Dashboard';

import { PopupProvider, PopupModal } from './context/PopupContext';
import { ThemeProvider } from './context/ThemeContext';

// Landing Page Wrapper
function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0A0F1F] overflow-x-hidden text-[#F8FAFC]">
      <Navbar />
      <Hero />
      <SocialProof />
      <ProblemSolution />
      <FeaturesGrid />
      <HowItWorks />
      <DashboardPreview />
      <Pricing />
      <Testimonials />
      <FAQ />
      <FinalCTA />
      <Footer />
    </div>
  );
}

function AppContent() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <div key={location.pathname}>
        <Routes location={location}>
          <Route path="/" element={
            <PageTransition variant="fade">
              <LandingPage />
            </PageTransition>
          } />
          <Route path="/dashboard" element={
            <PageTransition variant="slideRight">
              <Dashboard />
            </PageTransition>
          } />
        </Routes>
      </div>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <PopupProvider>
        <ToastProvider>
          <BrowserRouter>
            <AppContent />
            <PopupModal />
          </BrowserRouter>
        </ToastProvider>
      </PopupProvider>
    </ThemeProvider>
  );
}
