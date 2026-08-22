import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  ShieldCheck, 
  GitPullRequest, 
  Cpu, 
  Layers, 
  CheckCircle2, 
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Play
} from 'lucide-react';

interface NavbarProps {
  isConnected?: boolean;
  onDisconnect?: () => void;
  onQuickScenario?: (type: 'verified' | 'violation') => void;
  isLanding?: boolean;
  showOnLanding?: boolean;
  className?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ 
  isConnected = false, 
  onDisconnect,
  onQuickScenario,
  className = ''
}) => {
  const location = useLocation();

  return (
    <header className={`sticky top-0 z-50 w-full bg-[#000000]/95 border-b border-[#161B22]/80 backdrop-blur-md transition-all duration-300 pointer-events-auto ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-3 group pointer-events-auto">
          <div className="w-10 h-10 rounded-sm bg-[#14171D] border border-[#2A3038] group-hover:border-[#F5A623] flex items-center justify-center transition-all duration-300">
            <Cpu className="w-5 h-5 text-[#F5A623] group-hover:scale-110 transition-transform" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-['Big_Shoulders_Display'] text-2xl font-black tracking-wider uppercase text-[#F2F1ED] group-hover:text-[#F5A623] transition-colors duration-300">
                THE CODE FACTORY
              </span>
              <span className="text-[10px] uppercase font-mono tracking-widest px-1.5 py-0.5 rounded bg-[#2A3038] text-[#F5A623] border border-[#F5A623]/30">
                v1.0-alpha
              </span>
            </div>
            <p className="text-[11px] font-mono tracking-tight text-[#8E96A0]">
              AI Code Verification Engine
            </p>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="hidden md:flex items-center gap-1">
          <Link
            to="/"
            className={`px-3 py-1.5 text-xs font-mono tracking-wide rounded transition-colors ${
              location.pathname === '/' 
                ? 'bg-[#14171D] text-[#37E2C4] border border-[#37E2C4]/30' 
                : 'text-[#8E96A0] hover:text-[#F2F1ED] hover:bg-[#14171D]'
            }`}
          >
            01 // FACTORY OVERVIEW
          </Link>
          <Link
            to="/repos"
            className={`px-3 py-1.5 text-xs font-mono tracking-wide rounded transition-colors ${
              location.pathname.startsWith('/repos') 
                ? 'bg-[#14171D] text-[#37E2C4] border border-[#37E2C4]/30' 
                : 'text-[#8E96A0] hover:text-[#F2F1ED] hover:bg-[#14171D]'
            }`}
          >
            02 // SELECT TARGET
          </Link>
          <Link
            to="/verify"
            className={`px-3 py-1.5 text-xs font-mono tracking-wide rounded transition-colors ${
              location.pathname.startsWith('/verify') 
                ? 'bg-[#14171D] text-[#37E2C4] border border-[#37E2C4]/30' 
                : 'text-[#8E96A0] hover:text-[#F2F1ED] hover:bg-[#14171D]'
            }`}
          >
            03 // PIPELINE
          </Link>
          <Link
            to="/results"
            className={`px-3 py-1.5 text-xs font-mono tracking-wide rounded transition-colors ${
              location.pathname.startsWith('/results') 
                ? 'bg-[#14171D] text-[#37E2C4] border border-[#37E2C4]/30' 
                : 'text-[#8E96A0] hover:text-[#F2F1ED] hover:bg-[#14171D]'
            }`}
          >
            04 // VERDICT
          </Link>
        </nav>

        {/* Action / Auth Badge */}
        <div className="flex items-center gap-3">
          {/* Quick Scenario Tester for Hackathon Evaluators */}
          {onQuickScenario && (
            <div className="hidden lg:flex items-center gap-1.5 bg-[#14171D] border border-[#232A35] p-1 rounded">
              <span className="text-[10px] font-mono text-[#8E96A0] px-1">DEMO:</span>
              <button
                onClick={() => onQuickScenario('verified')}
                className="px-2 py-0.5 text-[11px] font-mono font-medium rounded bg-[#37E2C4]/10 text-[#37E2C4] hover:bg-[#37E2C4]/20 border border-[#37E2C4]/40 flex items-center gap-1 transition-colors cursor-pointer"
                title="Test Happy Path: All Invariants Verified"
              >
                <CheckCircle2 className="w-3 h-3" />
                VERIFIED
              </button>
              <button
                onClick={() => onQuickScenario('violation')}
                className="px-2 py-0.5 text-[11px] font-mono font-medium rounded bg-[#FF5C5C]/10 text-[#FF5C5C] hover:bg-[#FF5C5C]/20 border border-[#FF5C5C]/40 flex items-center gap-1 transition-colors cursor-pointer"
                title="Test Failure Path: Requirement Violation"
              >
                <AlertTriangle className="w-3 h-3" />
                VIOLATION
              </button>
            </div>
          )}

          <Link
            to="/verify"
            data-testid="navbar-launch-btn"
            className="inline-flex items-center gap-2 bg-[#F5A623] hover:bg-[#F5A623]/90 text-[#0B0D10] font-mono text-xs font-bold px-3.5 py-1.5 rounded shadow-sm hover:shadow-[0_0_15px_rgba(245,166,35,0.4)] transition-all cursor-pointer hover:scale-[1.02]"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>LAUNCH VERIFIER</span>
          </Link>
        </div>
      </div>
    </header>
  );
};
