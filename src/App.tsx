import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { LandingScreen } from './screens/LandingScreen';
import { ConnectScreen } from './screens/ConnectScreen';
import { RepoSelectionScreen } from './screens/RepoSelectionScreen';
import { ProgressScreen } from './screens/ProgressScreen';
import { ResultsScreen } from './screens/ResultsScreen';
import { createVerifyJob } from './lib/api';

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const isLanding = location.pathname === '/';

  const [isConnected, setIsConnected] = useState<boolean>(true);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [currentRepo, setCurrentRepo] = useState<string>('acme-corp/auth-core');
  const [currentPR, setCurrentPR] = useState<number>(89);
  const [forcedScenario, setForcedScenario] = useState<'verified' | 'violation' | undefined>(undefined);

  const [showNavbarOnLanding, setShowNavbarOnLanding] = useState<boolean>(false);

  React.useEffect(() => {
    if (!isLanding) {
      setShowNavbarOnLanding(true);
      return;
    }

    const handleScroll = () => {
      // Navbar appears when user scrolls towards the end of the 3D sequence
      const scrolled = window.scrollY > window.innerHeight * 2.5;
      setShowNavbarOnLanding(scrolled);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isLanding]);

  const handleConnect = () => {
    setIsConnected(true);
  };

  const handleDisconnect = () => {
    setIsConnected(false);
  };

  const handleStartVerify = (jobId: string, repoFullName: string, prNumber: number) => {
    setCurrentJobId(jobId);
    setCurrentRepo(repoFullName);
    setCurrentPR(prNumber);
    setForcedScenario(prNumber === 142 || repoFullName.includes('payment') ? 'verified' : (prNumber === 89 ? 'violation' : undefined));
  };

  const handleSelectScenario = async (type: 'verified' | 'violation') => {
    setForcedScenario(type);
    setIsConnected(true);

    const repoFullName = type === 'verified' ? 'octocat/payment-gateway-service' : 'acme-corp/auth-core';
    const prNumber = type === 'verified' ? 142 : 89;
    
    try {
      const job = await createVerifyJob({ repo_full_name: repoFullName, pr_number: prNumber }, type);
      setCurrentJobId(job.job_id);
      setCurrentRepo(repoFullName);
      setCurrentPR(prNumber);
      navigate(`/verify/${job.job_id}`);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSwitchResultScenario = (scenario: 'verified' | 'violation') => {
    setForcedScenario(scenario);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#000000] text-[#F2F1ED] font-sans selection:bg-[#37E2C4]/20 selection:text-[#37E2C4]">
      <Navbar 
        isConnected={isConnected} 
        onDisconnect={handleDisconnect}
        onQuickScenario={handleSelectScenario}
        isLanding={isLanding}
        showOnLanding={showNavbarOnLanding}
      />

      <main className="flex-1">
        <Routes>
          <Route 
            path="/" 
            element={
              <LandingScreen 
                isConnected={isConnected}
                onConnect={handleConnect}
                onSelectScenario={handleSelectScenario}
              />
            } 
          />
          <Route 
            path="/connect" 
            element={
              <ConnectScreen 
                isConnected={isConnected}
                onConnect={handleConnect}
                onDisconnect={handleDisconnect}
              />
            } 
          />
          <Route 
            path="/login" 
            element={
              <ConnectScreen 
                isConnected={isConnected}
                onConnect={handleConnect}
                onDisconnect={handleDisconnect}
              />
            } 
          />
          <Route 
            path="/repos" 
            element={
              <RepoSelectionScreen 
                onStartVerify={handleStartVerify}
              />
            } 
          />
          <Route 
            path="/verify" 
            element={
              <ProgressScreen 
                currentJobId={currentJobId}
                repoFullName={currentRepo}
                prNumber={currentPR}
                onVerificationComplete={(jobId) => setCurrentJobId(jobId)}
              />
            } 
          />
          <Route 
            path="/verify/:jobId" 
            element={
              <ProgressScreen 
                currentJobId={currentJobId}
                repoFullName={currentRepo}
                prNumber={currentPR}
                onVerificationComplete={(jobId) => setCurrentJobId(jobId)}
              />
            } 
          />
          <Route 
            path="/results" 
            element={
              <ResultsScreen 
                forcedScenario={forcedScenario}
                onSwitchScenario={handleSwitchResultScenario}
              />
            } 
          />
          <Route 
            path="/results/:jobId" 
            element={
              <ResultsScreen 
                forcedScenario={forcedScenario}
                onSwitchScenario={handleSwitchResultScenario}
              />
            } 
          />
        </Routes>
      </main>

      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
