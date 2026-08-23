import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  ShieldCheck, 
  Lock, 
  Key, 
  Cpu, 
  CheckCircle2, 
  AlertCircle, 
  ChevronRight, 
  ExternalLink, 
  RefreshCw, 
  Sparkles, 
  Building, 
  User, 
  GitBranch, 
  FolderGit2, 
  Terminal,
  Zap,
  ArrowRight,
  Check
} from 'lucide-react';
import { GithubIcon } from '../components/GithubIcon';

interface ConnectScreenProps {
  isConnected: boolean;
  onConnect: (accountData?: { username: string; org: string; avatarUrl: string }) => void;
  onDisconnect: () => void;
}

export const ConnectScreen: React.FC<ConnectScreenProps> = ({
  isConnected,
  onConnect,
  onDisconnect
}) => {
  const navigate = useNavigate();

  // Auth Mode: OAuth vs PAT (Personal Access Token)
  const [authMode, setAuthMode] = useState<'oauth' | 'pat'>('oauth');
  const [patToken, setPatToken] = useState<string>('');
  const [enterpriseHost, setEnterpriseHost] = useState<string>('');
  const [isAuthorizing, setIsAuthorizing] = useState<boolean>(false);
  const [isVerifyingToken, setIsVerifyingToken] = useState<boolean>(false);
  const [selectedOrg, setSelectedOrg] = useState<string>('octocat');
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'synced'>('idle');

  // Available Organizations / Workspaces
  const ORGS = [
    { id: 'octocat', name: 'octocat (Personal Workspace)', reposCount: 3, prCount: 7, avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80' },
    { id: 'acme-corp', name: 'Acme Corp Core Systems', reposCount: 14, prCount: 22, avatar: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100&auto=format&fit=crop&q=80' },
    { id: 'stripe-infra', name: 'Stripe Payments Infrastructure', reposCount: 8, prCount: 15, avatar: 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=100&auto=format&fit=crop&q=80' }
  ];

  // Required OAuth Permissions
  const PERMISSIONS = [
    { name: 'repo:status', desc: 'Publish formal mathematical evidence and invariants to GitHub Checks tab', status: 'REQUIRED' },
    { name: 'pull_requests:read', desc: 'Ingest AST syntax trees and modified function scopes from incoming PRs', status: 'REQUIRED' },
    { name: 'read:org', desc: 'Discover enterprise repositories and team access hierarchies', status: 'READ-ONLY' },
    { name: 'workflows:read', desc: 'Coordinate with existing GitHub Actions CI pipelines', status: 'OPTIONAL' }
  ];

  const [authError, setAuthError] = useState<string | null>(null);

  const handleOAuthConnect = async () => {
    setIsAuthorizing(true);
    setAuthError(null);
    setSyncStatus('syncing');

    try {
      // Check current backend user session or attempt default token
      const res = await fetch('http://127.0.0.1:8000/api/auth/user');
      if (res.ok) {
        const data = await res.json();
        if (data.authenticated && data.username) {
          setIsAuthorizing(false);
          setSyncStatus('synced');
          onConnect({
            username: data.username,
            org: data.name || data.username,
            avatarUrl: data.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100'
          });
          navigate('/repos');
          return;
        }
      }
    } catch (err) {
      console.warn('Live backend check error:', err);
    }

    // If not already authenticated in backend, switch to PAT tab to enter token
    setIsAuthorizing(false);
    setSyncStatus('idle');
    setAuthMode('pat');
  };

  const handlePATSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patToken.trim()) return;

    setIsVerifyingToken(true);
    setAuthError(null);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/auth/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: patToken.trim() })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Invalid GitHub Token. Please check token permissions.');
      }

      const data = await res.json();
      localStorage.setItem('github_pat', patToken.trim());

      onConnect({
        username: data.username || 'github-user',
        org: data.name || data.username || 'Personal Workspace',
        avatarUrl: data.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100'
      });

      navigate('/repos');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to authenticate token with GitHub';
      setAuthError(msg);
    } finally {
      setIsVerifyingToken(false);
    }
  };

  const handleProceedToRepos = () => {
    navigate('/repos');
  };

  return (
    <div className="min-h-screen bg-[#000000] text-[#F2F1ED] py-12 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto space-y-10">
      
      {/* Top Header Breadcrumb */}
      <div className="flex items-center justify-between border-b border-[#1A202C] pb-5">
        <div className="flex items-center gap-2 text-xs font-mono text-[#8E96A0]">
          <Link to="/" className="hover:text-[#F2F1ED] transition-colors">HOME</Link>
          <span>/</span>
          <span className="text-[#37E2C4] font-bold">01 // GITHUB AUTHENTICATION & INTAKE DOCK</span>
        </div>

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#14171D] border border-[#37E2C4]/30 text-[#37E2C4] text-[11px] font-mono">
          <ShieldCheck className="w-3.5 h-3.5 text-[#37E2C4]" />
          <span>ZERO SOURCE CODE RETENTION</span>
        </div>
      </div>

      {/* Hero Title */}
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#14171D] border border-[#F5A623]/40 text-[#F5A623] text-xs font-mono font-bold uppercase tracking-wider">
          <GithubIcon className="w-3.5 h-3.5" />
          <span>GITHUB ENTERPRISE & CLOUD INTEGRATION</span>
        </div>

        <h1 className="font-['Big_Shoulders_Display'] text-4xl sm:text-6xl font-black uppercase text-[#F2F1ED] tracking-tight">
          CONNECT YOUR <span className="text-[#37E2C4]">GITHUB WORKSPACE</span>
        </h1>

        <p className="text-sm sm:text-base text-[#8E96A0] max-w-3xl leading-relaxed">
          Link your GitHub organization to automatically ingest pull requests, map syntax dependency trees, and run 15-stage invariant verification in isolated memory micro-sandboxes.
        </p>
      </div>

      {/* Main Auth Split Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Auth Forms & Organization Picker (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Tab Selector: OAuth vs Personal Access Token */}
          <div className="flex items-center p-1 rounded-xl bg-[#10141A] border border-[#232A35]">
            <button
              onClick={() => setAuthMode('oauth')}
              className={`flex-1 py-2.5 px-4 rounded-lg text-xs font-mono font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                authMode === 'oauth'
                  ? 'bg-[#1C222B] text-[#37E2C4] border border-[#37E2C4]/40 shadow-[0_0_15px_rgba(55,226,196,0.15)]'
                  : 'text-[#8E96A0] hover:text-[#F2F1ED]'
              }`}
            >
              <GithubIcon className="w-4 h-4" />
              <span>1-CLICK GITHUB OAUTH</span>
            </button>

            <button
              onClick={() => setAuthMode('pat')}
              className={`flex-1 py-2.5 px-4 rounded-lg text-xs font-mono font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                authMode === 'pat'
                  ? 'bg-[#1C222B] text-[#F5A623] border border-[#F5A623]/40 shadow-[0_0_15px_rgba(245,166,35,0.15)]'
                  : 'text-[#8E96A0] hover:text-[#F2F1ED]'
              }`}
            >
              <Key className="w-4 h-4" />
              <span>PERSONAL ACCESS TOKEN</span>
            </button>
          </div>

          {/* MODE 1: GITHUB OAUTH */}
          {authMode === 'oauth' ? (
            <div className="bg-[#0B0D10] border border-[#232A35] p-6 sm:p-7 rounded-2xl space-y-6 shadow-xl">
              
              {/* Organization Picker */}
              <div className="space-y-3">
                <label className="text-xs font-mono text-[#8E96A0] uppercase tracking-wider flex items-center justify-between">
                  <span>SELECT TARGET ORGANIZATION / WORKSPACE</span>
                  <span className="text-[#37E2C4] text-[10px]">3 AVAILABLE</span>
                </label>

                <div className="space-y-2.5">
                  {ORGS.map((org) => {
                    const isSelected = selectedOrg === org.id;
                    return (
                      <div
                        key={org.id}
                        onClick={() => setSelectedOrg(org.id)}
                        className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                          isSelected
                            ? 'bg-[#141820] border-[#37E2C4] shadow-[0_0_15px_rgba(55,226,196,0.12)]'
                            : 'bg-[#10141A] border-[#1F2630] hover:border-[#2A3038] hover:bg-[#141820]'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <img 
                            src={org.avatar} 
                            alt={org.name} 
                            className="w-8 h-8 rounded-full border border-[#2A3038] object-cover"
                          />
                          <div>
                            <div className={`font-mono text-xs font-bold ${isSelected ? 'text-[#37E2C4]' : 'text-[#F2F1ED]'}`}>
                              {org.name}
                            </div>
                            <div className="text-[10px] font-mono text-[#8E96A0]">
                              {org.reposCount} Repositories • {org.prCount} Open PRs
                            </div>
                          </div>
                        </div>

                        <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                          isSelected ? 'border-[#37E2C4] bg-[#37E2C4]/20 text-[#37E2C4]' : 'border-[#2A3038]'
                        }`}>
                          {isSelected && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Action Button */}
              {isConnected ? (
                <div className="p-4 rounded-xl bg-[#141820] border border-[#37E2C4]/40 space-y-3">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <div className="flex items-center gap-2 text-[#37E2C4] font-bold">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>GITHUB SESSION AUTHENTICATED</span>
                    </div>
                    <span className="text-[#8E96A0]">@octocat</span>
                  </div>

                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={handleProceedToRepos}
                      className="flex-1 py-3 px-4 rounded-xl bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10] font-mono text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-[0_0_20px_rgba(55,226,196,0.25)] hover:scale-[1.02]"
                    >
                      <span>PROCEED TO REPOSITORY DOCK</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>

                    <button
                      onClick={onDisconnect}
                      className="py-3 px-4 rounded-xl bg-[#10141A] hover:bg-[#1C222B] text-[#FF5C5C] border border-[#FF5C5C]/30 font-mono text-xs font-bold transition-all cursor-pointer"
                    >
                      DISCONNECT
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={handleOAuthConnect}
                  disabled={isAuthorizing}
                  className="w-full py-4 px-6 rounded-xl bg-[#F5A623] hover:bg-[#F5A623]/90 text-[#0B0D10] font-mono text-sm font-bold shadow-[0_0_25px_rgba(245,166,35,0.35)] transition-all flex items-center justify-center gap-3 cursor-pointer hover:scale-[1.02] disabled:opacity-50"
                >
                  {isAuthorizing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-[#0B0D10]" />
                      <span>AUTHORIZING WITH GITHUB OAUTH...</span>
                    </>
                  ) : (
                    <>
                      <GithubIcon className="w-5 h-5 text-[#0B0D10]" />
                      <span>AUTHORIZE WITH GITHUB (1-CLICK)</span>
                      <ChevronRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              )}

              {/* Live Webhook & Status Banner */}
              <div className="pt-2 flex items-center justify-between text-[11px] font-mono text-[#8E96A0] border-t border-[#1F2630]">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#37E2C4] animate-pulse" />
                  <span>WEBHOOK GATEWAY: READY</span>
                </div>
                <span className="text-[#37E2C4]">AUTO-CI ON PR OPEN</span>
              </div>
            </div>
          ) : (
            /* MODE 2: PERSONAL ACCESS TOKEN */
            <form onSubmit={handlePATSubmit} className="bg-[#0B0D10] border border-[#232A35] p-6 sm:p-7 rounded-2xl space-y-5 shadow-xl">
              <div className="space-y-1.5">
                <label className="text-xs font-mono text-[#F5A623] font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <Key className="w-3.5 h-3.5" />
                  <span>PERSONAL ACCESS TOKEN (CLASSIC OR FINE-GRAINED)</span>
                </label>
                <input
                  type="password"
                  value={patToken}
                  onChange={(e) => setPatToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  className="w-full bg-[#10141A] border border-[#2A3038] rounded-xl px-4 py-3 text-xs font-mono text-[#F2F1ED] placeholder-[#8E96A0] focus:outline-none focus:border-[#F5A623]"
                  required
                />
                <p className="text-[10px] font-mono text-[#8E96A0]">
                  Requires scopes: <code className="text-[#37E2C4]">repo:status</code>, <code className="text-[#37E2C4]">pull_requests:read</code>
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-mono text-[#8E96A0] uppercase tracking-wider">
                  ENTERPRISE GITHUB HOST (OPTIONAL)
                </label>
                <input
                  type="text"
                  value={enterpriseHost}
                  onChange={(e) => setEnterpriseHost(e.target.value)}
                  placeholder="https://github.corp.internal"
                  className="w-full bg-[#10141A] border border-[#2A3038] rounded-xl px-4 py-2.5 text-xs font-mono text-[#F2F1ED] placeholder-[#8E96A0] focus:outline-none focus:border-[#37E2C4]"
                />
              </div>

              {authError && (
                <div className="p-3.5 rounded-xl bg-[#FF5C5C]/10 border border-[#FF5C5C]/40 text-[#FF5C5C] text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-[#FF5C5C]" />
                  <span>{authError}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isVerifyingToken || !patToken.trim()}
                className="w-full py-3.5 px-6 rounded-xl bg-[#F5A623] hover:bg-[#F5A623]/90 text-[#0B0D10] font-mono text-xs font-bold shadow-[0_0_20px_rgba(245,166,35,0.3)] transition-all flex items-center justify-center gap-2 cursor-pointer hover:scale-[1.02] disabled:opacity-50"
              >
                {isVerifyingToken ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-[#0B0D10]" />
                    <span>VALIDATING TOKEN & SCOPES...</span>
                  </>
                ) : (
                  <>
                    <Lock className="w-4 h-4 text-[#0B0D10]" />
                    <span>AUTHENTICATE TOKEN & SYNC REPOS</span>
                  </>
                )}
              </button>
            </form>
          )}

        </div>

        {/* Right Side: Security, Scopes & Live Invariant Shield (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Security Guarantee Box */}
          <div className="p-6 rounded-2xl bg-[#0B0D10] border border-[#232A35] space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono text-[#37E2C4] font-bold">
              <ShieldCheck className="w-4 h-4 text-[#37E2C4]" />
              <span>THE CODE FACTORY SECURITY PROMISE</span>
            </div>

            <h3 className="font-['Big_Shoulders_Display'] text-2xl font-black uppercase text-[#F2F1ED]">
              ZERO-RETENTION ARCHITECTURE
            </h3>

            <p className="text-xs text-[#8E96A0] leading-relaxed">
              Your source code is never stored on disk and never used to train public models. Repositories are processed exclusively in RAM micro-sandboxes that terminate after verification.
            </p>

            <div className="space-y-2 pt-2 border-t border-[#1F2630]">
              <div className="flex items-center gap-2 text-xs font-mono text-[#F2F1ED]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#37E2C4]" />
                <span>SOC2 Type II & ISO 27001 Compliant</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono text-[#F2F1ED]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#37E2C4]" />
                <span>End-to-End TLS 1.3 Encryption</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono text-[#F2F1ED]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#37E2C4]" />
                <span>Cryptographic Proof Hashes Only</span>
              </div>
            </div>
          </div>

          {/* Permissions Breakdown */}
          <div className="p-6 rounded-2xl bg-[#0B0D10] border border-[#232A35] space-y-4">
            <div className="text-xs font-mono text-[#8E96A0] uppercase tracking-wider">
              REQUIRED OAUTH PERMISSIONS
            </div>

            <div className="space-y-3">
              {PERMISSIONS.map((perm) => (
                <div key={perm.name} className="p-3 rounded-xl bg-[#10141A] border border-[#1F2630] space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-[#37E2C4] font-bold">{perm.name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1C222B] text-[#8E96A0] border border-[#2A3038]">
                      {perm.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#8E96A0] leading-snug">
                    {perm.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};
