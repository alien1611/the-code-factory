import React from 'react';
import { CheckCircle2, XCircle, ShieldCheck, AlertOctagon, GitCommit, Clock, GitBranch } from 'lucide-react';

interface VerdictStampProps {
  verdict: 'VERIFIED' | 'REQUIREMENT_VIOLATION';
  repoFullName?: string;
  prNumber?: number;
  prTitle?: string;
  commitHash?: string;
  branch?: string;
  durationSec?: number;
  timestamp?: string;
}

export const VerdictStamp: React.FC<VerdictStampProps> = ({
  verdict,
  repoFullName,
  prNumber,
  prTitle,
  commitHash = '9a7e3b1c',
  branch = 'main',
  durationSec = 4.8,
  timestamp = 'Just now',
}) => {
  const isVerified = verdict === 'VERIFIED';

  return (
    <div 
      className={`relative overflow-hidden rounded-lg border-2 p-6 sm:p-8 transition-all duration-300 ${
        isVerified 
          ? 'bg-[#14171D] border-[#37E2C4] shadow-[0_0_40px_rgba(55,226,196,0.18)]' 
          : 'bg-[#14171D] border-[#FF5C5C] shadow-[0_0_40px_rgba(255,92,92,0.18)]'
      }`}
      data-testid="verdict-banner"
    >
      {/* Background industrial watermark */}
      <div className="absolute right-4 -bottom-6 select-none pointer-events-none opacity-5">
        <span className="font-['Big_Shoulders_Display'] text-9xl font-black tracking-tighter uppercase">
          {isVerified ? 'VERIFIED' : 'VIOLATION'}
        </span>
      </div>

      {/* Industrial top status bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#232A35] pb-4 mb-6">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${isVerified ? 'bg-[#37E2C4] shadow-[0_0_8px_#37E2C4]' : 'bg-[#FF5C5C] shadow-[0_0_8px_#FF5C5C]'}`} />
          <span className="font-mono text-xs uppercase tracking-widest text-[#8E96A0]">
            INSPECTION CERTIFICATE // SEAL #{commitHash.substring(0, 6).toUpperCase()}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-[#8E96A0]">
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-[#F5A623]" />
            {durationSec}s run
          </span>
          <span className="flex items-center gap-1">
            <GitCommit className="w-3.5 h-3.5 text-[#8E96A0]" />
            {commitHash}
          </span>
          {branch && (
            <span className="hidden sm:flex items-center gap-1">
              <GitBranch className="w-3.5 h-3.5 text-[#8E96A0]" />
              {branch}
            </span>
          )}
        </div>
      </div>

      {/* Main Stamp & Verdict Heading */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className={`p-3.5 rounded-md border ${
            isVerified 
              ? 'bg-[#37E2C4]/10 border-[#37E2C4]/40 text-[#37E2C4]' 
              : 'bg-[#FF5C5C]/10 border-[#FF5C5C]/40 text-[#FF5C5C]'
          }`}>
            {isVerified ? (
              <ShieldCheck className="w-10 h-10 stroke-[2.5]" />
            ) : (
              <AlertOctagon className="w-10 h-10 stroke-[2.5]" />
            )}
          </div>

          <div>
            <div className="flex items-center gap-3">
              <h1 
                className={`font-['Big_Shoulders_Display'] text-4xl sm:text-5xl md:text-6xl font-black uppercase tracking-tight ${
                  isVerified ? 'text-[#37E2C4]' : 'text-[#FF5C5C]'
                }`}
                data-testid="verdict-title"
              >
                {isVerified ? 'VERIFIED' : 'REQUIREMENT VIOLATION'}
              </h1>
              <span className={`px-2 py-1 rounded text-xs font-mono font-bold tracking-wider uppercase border ${
                isVerified 
                  ? 'bg-[#37E2C4]/10 text-[#37E2C4] border-[#37E2C4]/30' 
                  : 'bg-[#FF5C5C]/10 text-[#FF5C5C] border-[#FF5C5C]/30'
              }`}>
                {isVerified ? 'PASSED 100%' : 'ACTION REQUIRED'}
              </span>
            </div>

            <p className="text-sm sm:text-base text-[#F2F1ED] font-medium mt-1">
              {isVerified ? (
                <>All architectural invariants, security policies, and AI edge cases <span className="text-[#37E2C4] font-semibold">proven correct</span>.</>
              ) : (
                <>PR introduces <span className="text-[#FF5C5C] font-semibold">critical contract violations</span> and security regressions against specifications.</>
              )}
            </p>

            {repoFullName && (
              <div className="mt-2 text-xs font-mono text-[#8E96A0] flex items-center gap-2">
                <span className="text-[#F5A623]">{repoFullName}</span>
                {prNumber && <span>#{prNumber}</span>}
                {prTitle && <span className="text-[#F2F1ED]/80 truncate max-w-md">— {prTitle}</span>}
              </div>
            )}
          </div>
        </div>

        {/* Industrial Mechanical Seal Badge */}
        <div className={`hidden lg:flex flex-col items-center justify-center p-3 rounded-lg border border-dashed ${
          isVerified ? 'border-[#37E2C4]/50 bg-[#37E2C4]/5 text-[#37E2C4]' : 'border-[#FF5C5C]/50 bg-[#FF5C5C]/5 text-[#FF5C5C]'
        }`}>
          <div className="text-[10px] font-mono tracking-widest uppercase">FACTORY ENGINE SEAL</div>
          <div className="font-['Big_Shoulders_Display'] text-xl font-bold tracking-wider uppercase">
            {isVerified ? 'STAMPED: READY TO MERGE' : 'BLOCKED: REJECTED'}
          </div>
          <div className="text-[9px] font-mono text-[#8E96A0] mt-0.5">SHA256 EVIDENCE CHAIN LOCKED</div>
        </div>
      </div>
    </div>
  );
};
