import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../components/ToastSystem';

export default function DashboardTest() {
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const toast = useToast();

  return (
    <div className={`min-h-screen flex transition-colors ${isDark ? 'bg-[#0f1419] text-slate-200' : 'bg-slate-50 text-slate-900'}`}>
      <div className="flex-1 p-8">
        <h1 className="text-3xl font-bold text-white">Dashboard Test</h1>
        <p className="text-slate-400 mt-4">If you can see this, the Dashboard is rendering!</p>
        <button 
          onClick={() => toast.success('Dashboard is working!')}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
        >
          Test Toast
        </button>
        <button 
          onClick={() => navigate('/')}
          className="mt-4 ml-4 px-4 py-2 bg-red-500 text-white rounded"
        >
          Go Home
        </button>
      </div>
    </div>
  );
}