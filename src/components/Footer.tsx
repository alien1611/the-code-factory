import React from 'react';
import { Cpu, ShieldCheck, Terminal, Sparkles, Radio } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-[#232A35] bg-[#0B0D10] py-8 text-[#8E96A0]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6 text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded bg-[#14171D] border border-[#2A3038] flex items-center justify-center text-[#F5A623]">
            <Cpu className="w-3.5 h-3.5" />
          </div>
          <div>
            <span className="font-['Big_Shoulders_Display'] text-base font-bold tracking-wider text-[#F2F1ED] uppercase">
              FACTORY // AI CODE VERIFICATION
            </span>
            <p className="text-[11px] text-[#8E96A0]">
              Mathematical & Invariant Proof Pipeline for Pull Requests
            </p>
          </div>
        </div>

        {/* Engine status indicators */}
        <div className="flex flex-wrap items-center gap-4 text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#37E2C4] inline-block animate-pulse" />
            <span className="text-[#F2F1ED]">SANDBOX CLUSTER: ONLINE</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Radio className="w-3 h-3 text-[#F5A623]" />
            <span>AST SOLVER: READY</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-purple-400" />
            <span>ADVERSARIAL AI: ACTIVE</span>
          </div>
        </div>

        <div className="text-[11px] text-[#8E96A0]">
          HACKATHON BUILD • PROVISIONAL API v1.0
        </div>
      </div>
    </footer>
  );
};
