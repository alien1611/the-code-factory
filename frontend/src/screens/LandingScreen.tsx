import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Cpu, 
  ShieldCheck, 
  AlertTriangle, 
  FileCode2, 
  Zap, 
  Layers, 
  CheckCircle2, 
  ArrowRight,
  Terminal,
  Search,
  Sparkles,
  Play
} from 'lucide-react';
import { FactorySequence } from '../components/FactorySequence';

interface LandingScreenProps {
  isConnected: boolean;
  onConnect: () => void;
  onSelectScenario: (type: 'verified' | 'violation') => void;
}

export const LandingScreen: React.FC<LandingScreenProps> = ({
  isConnected,
  onConnect,
  onSelectScenario
}) => {
  const navigate = useNavigate();
  const [activeCodeTab, setActiveCodeTab] = useState<'verified' | 'violation'>('verified');

  const handleLaunchVerifier = () => {
    navigate('/verify');
  };

  const handleDemoLaunch = (type: 'verified' | 'violation') => {
    onConnect();
    onSelectScenario(type);
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#000000] text-[#F2F1ED] overflow-x-clip">
      {/* 1. Full Pinned Physical Factory Assembly Line Animation */}
      <FactorySequence 
        onConnectClick={handleLaunchVerifier} 
        onSelectScenario={handleDemoLaunch}
      />

      {/* 2. Functional Content Stream at End of Animation */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full space-y-24">
        
        {/* Core Value Proposition & AST Code Simulator */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#14171D] border border-[#F5A623]/30 text-[#F5A623] text-xs font-mono font-bold uppercase tracking-wider shadow-lg">
              <Zap className="w-3.5 h-3.5" />
              <span>BACKED BY EVIDENCE, NOT VIBES</span>
            </div>

            <h2 className="font-['Big_Shoulders_Display'] text-4xl sm:text-5xl lg:text-6xl font-black uppercase text-[#F2F1ED] leading-none">
              STOP GUESSING IF PRS <span className="text-[#37E2C4]">ACTUALLY WORK</span>
            </h2>

            <p className="text-base sm:text-lg text-[#8E96A0] leading-relaxed">
              Standard CI tests what developers <span className="text-[#F2F1ED] font-semibold">remembered</span> to test. Factory extracts what the PR <span className="text-[#37E2C4] font-semibold">claims to do</span>, synthesizes adversarial edge cases, and verifies mathematical invariants before code hits production.
            </p>

            <div className="flex flex-wrap gap-4 pt-2">
              <button
                onClick={handleLaunchVerifier}
                className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl bg-[#F5A623] hover:bg-[#F5A623]/90 text-[#0B0D10] font-mono font-bold text-sm shadow-[0_0_25px_rgba(245,166,35,0.4)] transition-all cursor-pointer hover:scale-[1.02]"
                data-testid="section-connect-btn"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>LAUNCH CODE VERIFIER</span>
              </button>

              <button
                onClick={() => handleDemoLaunch('violation')}
                className="inline-flex items-center gap-2 px-5 py-3.5 rounded-xl bg-[#14171D] hover:bg-[#1C222B] text-[#FF5C5C] border border-[#FF5C5C]/40 font-mono text-sm font-semibold transition-all cursor-pointer"
              >
                <AlertTriangle className="w-4 h-4" />
                <span>DEMO: VIOLATION PR #89</span>
              </button>
            </div>
          </div>

          {/* Interactive Code Simulator */}
          <div className="p-6 rounded-2xl border-2 border-[#2A3038] bg-[#0E1116] shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#232A35] pb-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveCodeTab('verified')}
                  className={`px-3 py-1 text-xs font-mono rounded font-bold transition-all cursor-pointer ${
                    activeCodeTab === 'verified'
                      ? 'bg-[#37E2C4]/20 text-[#37E2C4] border border-[#37E2C4]/50 shadow-[0_0_12px_rgba(55,226,196,0.2)]'
                      : 'text-[#8E96A0] hover:text-[#F2F1ED]'
                  }`}
                >
                  PR #142 (VERIFIED)
                </button>
                <button
                  onClick={() => setActiveCodeTab('violation')}
                  className={`px-3 py-1 text-xs font-mono rounded font-bold transition-all cursor-pointer ${
                    activeCodeTab === 'violation'
                      ? 'bg-[#FF5C5C]/20 text-[#FF5C5C] border border-[#FF5C5C]/50 shadow-[0_0_12px_rgba(255,92,92,0.2)]'
                      : 'text-[#8E96A0] hover:text-[#F2F1ED]'
                  }`}
                >
                  PR #89 (VIOLATION)
                </button>
              </div>

              <span className="text-[10px] font-mono text-[#8E96A0] uppercase flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${activeCodeTab === 'verified' ? 'bg-[#37E2C4] animate-pulse' : 'bg-[#FF5C5C]'}`} />
                {activeCodeTab === 'verified' ? 'PROOF SEALED' : '4 HAZARDS DETECTED'}
              </span>
            </div>

            <div className="font-mono text-xs p-4 rounded-xl bg-[#0B0D10] border border-[#1F2630] space-y-1.5 overflow-x-auto">
              {activeCodeTab === 'verified' ? (
                <>
                  <div className="text-[#8E96A0]">{'// webhook_handler.ts:48-56 (HMAC Validation)'}</div>
                  <div className="text-[#37E2C4]">{"+ const signature = req.headers['stripe-signature'];"}</div>
                  <div className="text-[#37E2C4]">{'+ const isValid = crypto.timingSafeEqual(computed, signature);'}</div>
                  <div className="text-[#37E2C4]">{'+ if (!isValid) throw new UnauthorizedException();'}</div>
                  <div className="text-[#8E96A0]">{'+ await recordIdempotencyKey(req.idempotencyKey);'}</div>
                  <div className="pt-2 text-[11px] text-[#37E2C4] flex items-center gap-1.5 font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>INVARIANTS REQ-01..05 VERIFIED (18/18 TESTS PASS)</span>
                  </div>
                </>
              ) : (
                <>
                  <div className="text-[#8E96A0]">{'// token_refresh.go:112-118 (Race Condition)'}</div>
                  <div className="text-[#FF5C5C]">{'- session := db.GetSession(refreshToken)'}</div>
                  <div className="text-[#FF5C5C]">{'- if session.IsRevoked { return ErrRevoked }'}</div>
                  <div className="text-[#FF5C5C]">{'- // BUG: Missing child session cascade revocation!'}</div>
                  <div className="text-[#FF5C5C]">{'- newToken := generateToken(session.UserID, session.Scopes)'}</div>
                  <div className="pt-2 text-[11px] text-[#FF5C5C] flex items-center gap-1.5 font-bold">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>VIOLATION: REQ-03 CASCADE REVOCATION FAILED</span>
                  </div>
                </>
              )}
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-[11px] font-mono text-[#8E96A0]">
                {activeCodeTab === 'verified' ? 'octocat/payment-gateway-service' : 'acme-corp/auth-core'}
              </span>
              <button
                onClick={() => handleDemoLaunch(activeCodeTab)}
                className={`px-4 py-1.5 text-xs font-mono font-bold rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
                  activeCodeTab === 'verified'
                    ? 'bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10]'
                    : 'bg-[#FF5C5C] hover:bg-[#FF5C5C]/90 text-[#0B0D10]'
                }`}
              >
                <span>RUN PIPELINE</span>
                <Play className="w-3 h-3 fill-current" />
              </button>
            </div>
          </div>
        </div>

        {/* 4 Pipeline Stations Breakdown */}
        <div className="space-y-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#232A35] pb-4">
            <div>
              <span className="text-xs font-mono text-[#F5A623] tracking-widest uppercase">
                THE AUTOMATED ASSEMBLY LINE
              </span>
              <h2 className="font-['Big_Shoulders_Display'] text-3xl sm:text-4xl font-black uppercase text-[#F2F1ED] mt-1">
                FOUR STATIONS OF VERIFICATION
              </h2>
            </div>
            <span className="text-xs font-mono text-[#8E96A0]">
              ZERO-CONFIGURATION • DYNAMIC CONTAINER SANDBOX
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-xl border border-[#2A3038] bg-[#14171D] hover:border-[#F5A623]/50 transition-all space-y-3 group">
              <div className="w-10 h-10 rounded-lg bg-[#0B0D10] border border-[#2A3038] group-hover:border-[#F5A623] flex items-center justify-center text-[#F5A623]">
                <Cpu className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </div>
              <div className="text-xs font-mono text-[#F5A623] font-bold">STATION 01</div>
              <h3 className="font-['Big_Shoulders_Display'] text-xl font-bold uppercase text-[#F2F1ED]">
                AST & CONTROL FLOW
              </h3>
              <p className="text-xs text-[#8E96A0] leading-relaxed">
                Parses modified AST nodes, maps dependency call graphs, and verifies type boundaries across packages.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-[#2A3038] bg-[#14171D] hover:border-[#F5A623]/50 transition-all space-y-3 group">
              <div className="w-10 h-10 rounded-lg bg-[#0B0D10] border border-[#2A3038] group-hover:border-[#F5A623] flex items-center justify-center text-[#F5A623]">
                <FileCode2 className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </div>
              <div className="text-xs font-mono text-[#F5A623] font-bold">STATION 02</div>
              <h3 className="font-['Big_Shoulders_Display'] text-xl font-bold uppercase text-[#F2F1ED]">
                REQUIREMENT SYNTHESIS
              </h3>
              <p className="text-xs text-[#8E96A0] leading-relaxed">
                Extracts invariant contracts from PR title, description, and tickets to define exact behavioral expectations.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-[#2A3038] bg-[#14171D] hover:border-[#37E2C4]/50 transition-all space-y-3 group">
              <div className="w-10 h-10 rounded-lg bg-[#0B0D10] border border-[#2A3038] group-hover:border-[#37E2C4] flex items-center justify-center text-[#37E2C4]">
                <Sparkles className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </div>
              <div className="text-xs font-mono text-[#37E2C4] font-bold">STATION 03</div>
              <h3 className="font-['Big_Shoulders_Display'] text-xl font-bold uppercase text-[#F2F1ED]">
                ADVERSARIAL ENGINE
              </h3>
              <p className="text-xs text-[#8E96A0] leading-relaxed">
                Synthesizes property tests, race condition vectors, and injection fuzzing to probe edge boundaries.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-[#2A3038] bg-[#14171D] hover:border-[#37E2C4]/50 transition-all space-y-3 group">
              <div className="w-10 h-10 rounded-lg bg-[#0B0D10] border border-[#2A3038] group-hover:border-[#37E2C4] flex items-center justify-center text-[#37E2C4]">
                <ShieldCheck className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </div>
              <div className="text-xs font-mono text-[#37E2C4] font-bold">STATION 04</div>
              <h3 className="font-['Big_Shoulders_Display'] text-xl font-bold uppercase text-[#F2F1ED]">
                EVIDENCE SEAL
              </h3>
              <p className="text-xs text-[#8E96A0] leading-relaxed">
                Outputs cryptographic inspection seal: VERIFIED or REQUIREMENT VIOLATION with exact file/line fix patches.
              </p>
            </div>
          </div>
        </div>

        {/* Side Comparison: Vibes vs Factory Evidence */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="p-6 rounded-2xl border border-[#232A35] bg-[#0E1116] space-y-4">
            <div className="text-xs font-mono text-[#8E96A0] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#FF5C5C]" />
              TRADITIONAL CODE REVIEW
            </div>
            <h3 className="font-['Big_Shoulders_Display'] text-2xl font-bold uppercase text-[#FF5C5C]">
              LGTM & VIBES
            </h3>
            <ul className="text-xs text-[#8E96A0] space-y-2 font-mono">
              <li className="flex items-start gap-2">
                <span className="text-[#FF5C5C]">✕</span>
                Reviewer skims 400 lines of diff in 3 minutes
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#FF5C5C]">✕</span>
                Misses silent token reuse race conditions
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#FF5C5C]">✕</span>
                Unit tests only check happy paths written by author
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#FF5C5C]">✕</span>
                Production outage 2 weeks later
              </li>
            </ul>
          </div>

          <div className="p-6 rounded-2xl border border-[#37E2C4]/40 bg-[#14171D] shadow-[0_0_30px_rgba(55,226,196,0.1)] space-y-4">
            <div className="text-xs font-mono text-[#37E2C4] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#37E2C4] animate-pulse" />
              FACTORY VERIFICATION
            </div>
            <h3 className="font-['Big_Shoulders_Display'] text-2xl font-bold uppercase text-[#37E2C4]">
              FORMAL EVIDENCE
            </h3>
            <ul className="text-xs text-[#F2F1ED] space-y-2 font-mono">
              <li className="flex items-start gap-2">
                <span className="text-[#37E2C4]">✓</span>
                Extracts architectural invariants from PR description
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#37E2C4]">✓</span>
                Fuzzes AST with 15 adversarial concurrency payloads
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#37E2C4]">✓</span>
                Generates verifiable proofs & code fix patches
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[#37E2C4]">✓</span>
                Decision sealed in &lt; 6 seconds
              </li>
            </ul>
          </div>
        </div>

        {/* Interactive Quick-Launch Panel */}
        <div className="p-8 rounded-3xl border-2 border-[#2A3038] bg-[#14171D] space-y-6 shadow-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-xs font-mono text-[#F5A623] font-bold uppercase tracking-wider">
                INTERACTIVE DEMO SANDBOX
              </span>
              <h3 className="font-['Big_Shoulders_Display'] text-3xl font-black uppercase text-[#F2F1ED]">
                EXPLORE SAMPLE SCENARIOS INSTANTLY
              </h3>
            </div>
            <span className="text-xs font-mono text-[#8E96A0]">
              NO SETUP REQUIRED • INSTANT REPLAY
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Verified Scenario Card */}
            <div 
              onClick={() => handleDemoLaunch('verified')}
              className="p-6 rounded-2xl border border-[#37E2C4]/40 bg-[#0B0D10] hover:bg-[#181C23] hover:border-[#37E2C4] transition-all cursor-pointer space-y-3 group"
              data-testid="quick-demo-verified"
            >
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-[#37E2C4]/20 text-[#37E2C4] border border-[#37E2C4]/40">
                  SCENARIO A: 100% VERIFIED
                </span>
                <ArrowRight className="w-4 h-4 text-[#37E2C4] group-hover:translate-x-1 transition-transform" />
              </div>
              <h4 className="font-sans font-bold text-lg text-[#F2F1ED]">
                octocat/payment-gateway-service #142
              </h4>
              <p className="text-xs text-[#8E96A0] leading-relaxed">
                Idempotent Stripe webhook handler with HMAC-SHA256 signature verification & jittered exponential retry. All 18 tests and 5 requirement invariants pass.
              </p>
            </div>

            {/* Violation Scenario Card */}
            <div 
              onClick={() => handleDemoLaunch('violation')}
              className="p-6 rounded-2xl border border-[#FF5C5C]/40 bg-[#0B0D10] hover:bg-[#181C23] hover:border-[#FF5C5C] transition-all cursor-pointer space-y-3 group"
              data-testid="quick-demo-violation"
            >
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-[#FF5C5C]/20 text-[#FF5C5C] border border-[#FF5C5C]/40">
                  SCENARIO B: REQUIREMENT VIOLATION
                </span>
                <ArrowRight className="w-4 h-4 text-[#FF5C5C] group-hover:translate-x-1 transition-transform" />
              </div>
              <h4 className="font-sans font-bold text-lg text-[#F2F1ED]">
                acme-corp/auth-core #89
              </h4>
              <p className="text-xs text-[#8E96A0] leading-relaxed">
                Token refresh PR containing silent session revocation failure (REQ-03), replay attack race conditions, and scope privilege escalation flaws.
              </p>
            </div>
          </div>
        </div>

      </section>
    </div>
  );
};
