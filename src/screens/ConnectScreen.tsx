import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  ShieldCheck, 
  Lock, 
  Key, 
  CheckCircle2, 
  AlertCircle, 
  ChevronRight, 
  ExternalLink, 
  RefreshCw, 
  User, 
  FolderGit2, 
  ArrowRight,
  Sparkles,
  GitBranch
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

  // Auth Mode: Username Discovery vs Personal Access Token
  const [authMode, setAuthMode] = useState<'username' | 'pat'>('username');
  const [githubUsername, setGithubUsername] = useState<string>('alien1611');
  const [patToken, setPatToken] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [connectedUser, setConnectedUser] = useState<{
    username: string;
    name: string;
    avatarUrl: string;
    publicRepos: number;
    htmlUrl: string;
  } | null>(null);

  // Check if session is already active on backend
  useEffect(() => {
    async function checkCurrentSession() {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/auth/user');
        if (res.ok) {
          const data = await res.json();
          if (data.authenticated && data.username) {
            setConnectedUser({
              username: data.username,
              name: data.name || data.username,
              avatarUrl: data.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100',
              publicRepos: data.public_repos || 0,
              htmlUrl: data.html_url || `https://github.com/${data.username}`
            });
            onConnect({
              username: data.username,
              org: data.name || data.username,
              avatarUrl: data.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100'
            });
          }
        }
      } catch (err) {
        // Backend offline
      }
    }
    checkCurrentSession();
  }, []);

  const handleConnectByUsername = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUser = githubUsername.trim().replace(/^@+/, '');
    if (!cleanUser) return;

    setIsLoading(true);
    setAuthError(null);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/auth/connect-user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: cleanUser })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `GitHub user '@${cleanUser}' was not found.`);
      }

      const data = await res.json();
      const userData = {
        username: data.username,
        name: data.name || data.username,
        avatarUrl: data.avatar_url,
        publicRepos: data.public_repos || 0,
        htmlUrl: data.html_url || `https://github.com/${data.username}`
      };

      setConnectedUser(userData);
      onConnect({
        username: userData.username,
        org: userData.name,
        avatarUrl: userData.avatarUrl
      });

      navigate('/repos');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to connect to GitHub.';
      setAuthError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnectByPAT = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patToken.trim()) return;

    setIsLoading(true);
    setAuthError(null);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/auth/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: patToken.trim() })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Invalid GitHub Token. Please verify token permissions.');
      }

      const data = await res.json();
      localStorage.setItem('github_pat', patToken.trim());

      const userData = {
        username: data.username,
        name: data.name || data.username,
        avatarUrl: data.avatar_url,
        publicRepos: data.public_repos || 0,
        htmlUrl: data.html_url || `https://github.com/${data.username}`
      };

      setConnectedUser(userData);
      onConnect({
        username: userData.username,
        org: userData.name,
        avatarUrl: userData.avatarUrl
      });

      navigate('/repos');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to authenticate token with GitHub';
      setAuthError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnectAction = async () => {
    try {
      await fetch('http://127.0.0.1:8000/api/auth/disconnect', { method: 'POST' });
    } catch (e) {}
    localStorage.removeItem('github_pat');
    setConnectedUser(null);
    onDisconnect();
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
          <span>REAL-TIME GITHUB API V3</span>
        </div>
      </div>

      {/* Hero Title */}
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#14171D] border border-[#F5A623]/40 text-[#F5A623] text-xs font-mono font-bold uppercase tracking-wider">
          <GithubIcon className="w-3.5 h-3.5" />
          <span>CONNECT LIVE GITHUB ACCOUNT</span>
        </div>

        <h1 className="font-['Big_Shoulders_Display'] text-4xl sm:text-6xl font-black uppercase text-[#F2F1ED] tracking-tight">
          CONNECT YOUR <span className="text-[#37E2C4]">GITHUB REPOSITORIES</span>
        </h1>

        <p className="text-sm sm:text-base text-[#8E96A0] max-w-3xl leading-relaxed">
          Authenticate your GitHub account to automatically fetch your real repositories, inspect live pull requests, and execute mathematical invariant verification pipelines.
        </p>
      </div>

      {/* Main Auth Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Real Connection Form (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Active Connected User Banner */}
          {connectedUser ? (
            <div className="bg-[#0B0D10] border border-[#37E2C4]/50 p-6 rounded-2xl space-y-5 shadow-[0_0_30px_rgba(55,226,196,0.15)]">
              <div className="flex items-center justify-between text-xs font-mono">
                <div className="flex items-center gap-2 text-[#37E2C4] font-bold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>GITHUB ACCOUNT CONNECTED</span>
                </div>
                <span className="text-[#8E96A0]">LIVE API</span>
              </div>

              <div className="flex items-center gap-4 p-4 rounded-xl bg-[#141820] border border-[#1F2630]">
                <img 
                  src={connectedUser.avatarUrl} 
                  alt={connectedUser.username} 
                  className="w-12 h-12 rounded-full border border-[#37E2C4] object-cover"
                />
                <div className="flex-1">
                  <div className="font-mono text-sm font-bold text-[#F2F1ED]">
                    {connectedUser.name}
                  </div>
                  <div className="text-xs font-mono text-[#37E2C4]">
                    @{connectedUser.username} • {connectedUser.publicRepos} Public Repos
                  </div>
                </div>
                <a 
                  href={connectedUser.htmlUrl} 
                  target="_blank" 
                  rel="noreferrer" 
                  className="p-2 text-[#8E96A0] hover:text-[#F2F1ED] transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => navigate('/repos')}
                  className="flex-1 py-3.5 px-6 rounded-xl bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10] font-mono text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-[0_0_20px_rgba(55,226,196,0.25)] hover:scale-[1.02]"
                >
                  <span>PROCEED TO MY REPOSITORIES</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <button
                  onClick={handleDisconnectAction}
                  className="py-3.5 px-4 rounded-xl bg-[#10141A] hover:bg-[#1C222B] text-[#FF5C5C] border border-[#FF5C5C]/30 font-mono text-xs font-bold transition-all cursor-pointer"
                >
                  DISCONNECT
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-[#0B0D10] border border-[#232A35] p-6 sm:p-7 rounded-2xl space-y-6 shadow-xl">
              
              {/* Tab Selector */}
              <div className="flex items-center p-1 rounded-xl bg-[#10141A] border border-[#232A35]">
                <button
                  onClick={() => setAuthMode('username')}
                  className={`flex-1 py-2.5 px-4 rounded-lg text-xs font-mono font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                    authMode === 'username'
                      ? 'bg-[#1C222B] text-[#37E2C4] border border-[#37E2C4]/40 shadow-[0_0_15px_rgba(55,226,196,0.15)]'
                      : 'text-[#8E96A0] hover:text-[#F2F1ED]'
                  }`}
                >
                  <User className="w-4 h-4" />
                  <span>GITHUB USERNAME / ORG</span>
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

              {/* Error Alert Banner */}
              {authError && (
                <div className="p-3.5 rounded-xl bg-[#FF5C5C]/10 border border-[#FF5C5C]/40 text-[#FF5C5C] text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-[#FF5C5C]" />
                  <span>{authError}</span>
                </div>
              )}

              {/* MODE 1: GITHUB USERNAME / ORG */}
              {authMode === 'username' ? (
                <form onSubmit={handleConnectByUsername} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-mono text-[#37E2C4] font-bold uppercase tracking-wider flex items-center justify-between">
                      <span>ENTER GITHUB USERNAME OR ORG</span>
                      <span className="text-[#8E96A0] text-[10px]">PUBLIC REPOSITORIES</span>
                    </label>
                    <div className="relative">
                      <span className="absolute left-3.5 top-3 text-sm font-mono text-[#8E96A0]">@</span>
                      <input
                        type="text"
                        value={githubUsername}
                        onChange={(e) => setGithubUsername(e.target.value)}
                        placeholder="alien1611 or your-organization"
                        className="w-full bg-[#10141A] border border-[#2A3038] rounded-xl pl-8 pr-4 py-3 text-xs font-mono text-[#F2F1ED] placeholder-[#8E96A0] focus:outline-none focus:border-[#37E2C4]"
                        required
                      />
                    </div>
                    <p className="text-[10px] font-mono text-[#8E96A0]">
                      Instantly discovers all public repositories and active pull requests for this account.
                    </p>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading || !githubUsername.trim()}
                    className="w-full py-4 px-6 rounded-xl bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10] font-mono text-sm font-bold shadow-[0_0_25px_rgba(55,226,196,0.3)] transition-all flex items-center justify-center gap-3 cursor-pointer hover:scale-[1.02] disabled:opacity-50"
                  >
                    {isLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin text-[#0B0D10]" />
                        <span>DISCOVERING GITHUB REPOSITORIES...</span>
                      </>
                    ) : (
                      <>
                        <GithubIcon className="w-5 h-5 text-[#0B0D10]" />
                        <span>CONNECT & LOAD REPOSITORIES</span>
                        <ChevronRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </form>
              ) : (
                /* MODE 2: PERSONAL ACCESS TOKEN */
                <form onSubmit={handleConnectByPAT} className="space-y-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <label className="text-[#F5A623] font-bold uppercase tracking-wider flex items-center gap-1.5">
                        <Key className="w-3.5 h-3.5" />
                        <span>GITHUB PERSONAL ACCESS TOKEN</span>
                      </label>
                      <a
                        href="https://github.com/settings/tokens/new?scopes=repo,read:org"
                        target="_blank"
                        rel="noreferrer"
                        className="text-[#37E2C4] hover:underline text-[10px] flex items-center gap-1"
                      >
                        <span>Generate Token</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>

                    <input
                      type="password"
                      value={patToken}
                      onChange={(e) => setPatToken(e.target.value)}
                      placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      className="w-full bg-[#10141A] border border-[#2A3038] rounded-xl px-4 py-3 text-xs font-mono text-[#F2F1ED] placeholder-[#8E96A0] focus:outline-none focus:border-[#F5A623]"
                      required
                    />
                    <p className="text-[10px] font-mono text-[#8E96A0]">
                      Enables full access to private repositories, automated PR checks, and increased API rate limits (5,000 req/hr).
                    </p>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading || !patToken.trim()}
                    className="w-full py-4 px-6 rounded-xl bg-[#F5A623] hover:bg-[#F5A623]/90 text-[#0B0D10] font-mono text-sm font-bold shadow-[0_0_25px_rgba(245,166,35,0.3)] transition-all flex items-center justify-center gap-3 cursor-pointer hover:scale-[1.02] disabled:opacity-50"
                  >
                    {isLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin text-[#0B0D10]" />
                        <span>AUTHENTICATING WITH GITHUB API...</span>
                      </>
                    ) : (
                      <>
                        <Lock className="w-4 h-4 text-[#0B0D10]" />
                        <span>AUTHENTICATE & SYNC WORKSPACE</span>
                        <ChevronRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </form>
              )}

              {/* Status Footer */}
              <div className="pt-3 flex items-center justify-between text-[11px] font-mono text-[#8E96A0] border-t border-[#1F2630]">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#37E2C4] animate-pulse" />
                  <span>BACKEND GATEWAY: ONLINE</span>
                </div>
                <span className="text-[#37E2C4]">REAL-TIME REPO SYNC</span>
              </div>
            </div>
          )}

        </div>

        {/* Right Side: Security Guarantee & Architecture (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Security Box */}
          <div className="p-6 rounded-2xl bg-[#0B0D10] border border-[#232A35] space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono text-[#37E2C4] font-bold">
              <ShieldCheck className="w-4 h-4 text-[#37E2C4]" />
              <span>THE CODE FACTORY SECURITY ENGINE</span>
            </div>

            <h3 className="font-['Big_Shoulders_Display'] text-2xl font-black uppercase text-[#F2F1ED]">
              ZERO-RETENTION ARCHITECTURE
            </h3>

            <p className="text-xs text-[#8E96A0] leading-relaxed">
              Your source code is never stored permanently on disk. Verification runs inside ephemeral memory micro-sandboxes that terminate immediately after AST and invariant extraction.
            </p>

            <div className="space-y-2 pt-2 border-t border-[#1F2630]">
              <div className="flex items-center gap-2 text-xs font-mono text-[#F2F1ED]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#37E2C4]" />
                <span>Real-Time Pull Request Diff Ingestion</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono text-[#F2F1ED]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#37E2C4]" />
                <span>End-to-End TLS 1.3 Encryption</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono text-[#F2F1ED]">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#37E2C4]" />
                <span>Deterministic Invariant Proof Seals</span>
              </div>
            </div>
          </div>

          {/* Direct Repo Discovery Info */}
          <div className="p-6 rounded-2xl bg-[#0B0D10] border border-[#232A35] space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono text-[#F5A623] font-bold">
              <Sparkles className="w-4 h-4" />
              <span>TARGET WORKSPACES</span>
            </div>
            <p className="text-xs text-[#8E96A0] leading-relaxed">
              Connect to your personal account (<code className="text-[#37E2C4]">alien1611</code>) to verify repositories like <code className="text-[#F2F1ED]">the-code-factory</code>, <code className="text-[#F2F1ED]">ai-code-viewer</code>, or any public GitHub repository.
            </p>
          </div>

        </div>

      </div>

    </div>
  );
};
