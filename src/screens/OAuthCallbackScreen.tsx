import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { RefreshCw, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react';
import { GithubIcon } from '../components/GithubIcon';

interface OAuthCallbackScreenProps {
  onConnect: (accountData?: { username: string; org: string; avatarUrl: string }) => void;
}

export const OAuthCallbackScreen: React.FC<OAuthCallbackScreenProps> = ({ onConnect }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'exchanging' | 'success' | 'error'>('exchanging');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      setStatus('error');
      setErrorMessage('No GitHub authorization code was provided in callback URL.');
      return;
    }

    async function exchangeOAuthCode() {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/auth/oauth/callback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'OAuth token exchange failed.');
        }

        const data = await res.json();
        if (data.token) {
          localStorage.setItem('github_pat', data.token);
        }

        onConnect({
          username: data.username || 'github-user',
          org: data.name || data.username || 'Personal Workspace',
          avatarUrl: data.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100'
        });

        setStatus('success');
        setTimeout(() => {
          navigate('/repos');
        }, 1200);
      } catch (err) {
        setStatus('error');
        setErrorMessage(err instanceof Error ? err.message : 'Failed to complete OAuth authentication.');
      }
    }

    exchangeOAuthCode();
  }, [searchParams, navigate, onConnect]);

  return (
    <div className="min-h-screen bg-[#000000] text-[#F2F1ED] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-[#0B0D10] border border-[#232A35] rounded-2xl p-8 space-y-6 shadow-2xl text-center">
        <div className="flex justify-center">
          <div className="w-16 h-16 rounded-2xl bg-[#141820] border border-[#2A3038] flex items-center justify-center">
            <GithubIcon className="w-8 h-8 text-[#37E2C4]" />
          </div>
        </div>

        {status === 'exchanging' && (
          <div className="space-y-4">
            <h2 className="font-['Big_Shoulders_Display'] text-3xl font-black uppercase text-[#F2F1ED]">
              CONNECTING TO GITHUB...
            </h2>
            <p className="text-xs font-mono text-[#8E96A0]">
              Completing cryptographic OAuth handshake and syncing repositories...
            </p>
            <div className="flex justify-center pt-2">
              <RefreshCw className="w-6 h-6 animate-spin text-[#37E2C4]" />
            </div>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4">
            <div className="flex justify-center text-[#37E2C4]">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h2 className="font-['Big_Shoulders_Display'] text-3xl font-black uppercase text-[#37E2C4]">
              GITHUB AUTHENTICATED!
            </h2>
            <p className="text-xs font-mono text-[#8E96A0]">
              Redirecting to your repository dock...
            </p>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-5">
            <div className="flex justify-center text-[#FF5C5C]">
              <AlertCircle className="w-8 h-8" />
            </div>
            <h2 className="font-['Big_Shoulders_Display'] text-2xl font-black uppercase text-[#FF5C5C]">
              AUTHENTICATION ERROR
            </h2>
            <p className="text-xs font-mono text-[#8E96A0] leading-relaxed">
              {errorMessage}
            </p>

            <div className="pt-2 flex flex-col gap-2.5">
              <Link
                to="/connect"
                className="py-3 px-4 rounded-xl bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10] font-mono text-xs font-bold transition-all flex items-center justify-center gap-2"
              >
                <span>RETURN TO CONNECT WITH TOKEN</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
