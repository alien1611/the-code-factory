import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Cpu, 
  FlaskConical, 
  Sparkles, 
  ShieldCheck, 
  CheckCircle2, 
  Clock, 
  ArrowRight, 
  Layers, 
  FastForward, 
  RotateCcw, 
  Terminal, 
  FileCode, 
  Zap, 
  Activity 
} from 'lucide-react';
import { useVerificationStatus } from '../hooks/useVerificationStatus';
import { TerminalLogs } from '../components/TerminalLogs';
import { PipelineStep } from '../lib/types';
import { PIPELINE_STEPS_META } from '../lib/mockData';

interface ProgressScreenProps {
  currentJobId?: string | null;
  repoFullName?: string;
  prNumber?: number;
  onVerificationComplete?: (jobId: string) => void;
}

export const ProgressScreen: React.FC<ProgressScreenProps> = ({
  currentJobId,
  repoFullName = 'acme-corp/auth-core',
  prNumber = 89,
  onVerificationComplete,
}) => {
  const { jobId: routeJobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const activeJobId = routeJobId || currentJobId || 'job-vfy-live';

  const {
    status,
    isLoading,
    isComplete,
    isFailed,
    error,
    refetch
  } = useVerificationStatus(activeJobId, {
    pollingIntervalMs: 800,
    onComplete: (res) => {
      if (onVerificationComplete) {
        onVerificationComplete(res.job_id);
      }
    }
  });

  const currentStep = status?.status || 'queued';
  const progressPct = status?.progress_pct ?? 15;
  const currentStepLabel = status?.current_step_label || 'Allocating Isolated Verification Sandbox';
  const logs = status?.logs || [];

  const handleViewResults = () => {
    navigate(`/results/${activeJobId}`);
  };

  const getStepIndex = (step: PipelineStep): number => {
    const idx = PIPELINE_STEPS_META.findIndex(s => s.key === step);
    return idx >= 0 ? idx : 0;
  };

  const activeIndex = getStepIndex(currentStep);

  return (
    <div className="min-h-screen bg-[#0B0D10] text-[#F2F1ED] py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8">
      {/* Top Banner */}
      <div className="border-b border-[#232A35] pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#F5A623] uppercase tracking-wider mb-1">
            <Activity className="w-4 h-4 animate-pulse" />
            STATION 03 // ACTIVE PIPELINE
          </div>
          <h1 className="font-['Big_Shoulders_Display'] text-4xl sm:text-5xl font-black uppercase text-[#F2F1ED]">
            VERIFICATION IN PROGRESS
          </h1>
          <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-[#8E96A0] mt-1">
            <span>JOB #{activeJobId.substring(0, 14)}</span>
            <span>•</span>
            <span className="text-[#F5A623]">{repoFullName} #{prNumber}</span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-3">
          {isComplete ? (
            <button
              onClick={handleViewResults}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10] font-mono font-bold text-xs shadow-[0_0_20px_rgba(55,226,196,0.4)] transition-all cursor-pointer animate-pulse"
              data-testid="view-results-btn"
            >
              <span>VIEW FINAL VERDICT</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleViewResults}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#14171D] hover:bg-[#1C222B] text-xs font-mono text-[#8E96A0] hover:text-[#F2F1ED] border border-[#2A3038] transition-colors cursor-pointer"
              title="Skip wait for testing"
              data-testid="view-results-btn"
            >
              <FastForward className="w-3.5 h-3.5 text-[#F5A623]" />
              <span>SKIP TO RESULT</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Progress Bar & Live Metric */}
      <div className="p-6 sm:p-8 rounded-xl border border-[#2A3038] bg-[#14171D] shadow-2xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs font-mono text-[#F5A623] font-bold uppercase tracking-wider mb-1">
              CURRENT OPERATION
            </div>
            <h2 className="font-mono text-lg sm:text-xl font-bold text-[#F2F1ED]" data-testid="current-step-label">
              {currentStepLabel}
            </h2>
          </div>

          <div className="text-right">
            <span className="font-['Big_Shoulders_Display'] text-4xl sm:text-5xl font-black text-[#37E2C4]" data-testid="progress-pct">
              {progressPct}%
            </span>
            <div className="text-[11px] font-mono text-[#8E96A0]">TOTAL PIPELINE PROGRESS</div>
          </div>
        </div>

        {/* Bar */}
        <div className="w-full bg-[#0B0D10] h-3 rounded-full overflow-hidden border border-[#232A35] p-0.5">
          <div 
            className="h-full bg-gradient-to-r from-[#F5A623] via-[#37E2C4] to-[#37E2C4] rounded-full transition-all duration-500 relative"
            style={{ width: `${progressPct}%` }}
          >
            <div className="absolute right-0 top-0 bottom-0 w-2 bg-white rounded-full animate-ping" />
          </div>
        </div>

        {/* Step by Step Visual Pipeline */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-4">
          {PIPELINE_STEPS_META.slice(0, 6).map((stepMeta, idx) => {
            const isFinished = activeIndex > idx || isComplete;
            const isCurrent = activeIndex === idx && !isComplete;

            return (
              <div
                key={stepMeta.key}
                className={`p-3 rounded-md border text-xs font-mono transition-all ${
                  isCurrent 
                    ? 'bg-[#181C23] border-[#F5A623] shadow-[0_0_15px_rgba(245,166,35,0.2)]' 
                    : isFinished
                      ? 'bg-[#0B0D10] border-[#37E2C4]/40 text-[#37E2C4]'
                      : 'bg-[#0B0D10] border-[#232A35] text-[#8E96A0] opacity-50'
                }`}
                data-testid={`pipeline-step-${stepMeta.key}`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-bold">0{idx + 1}</span>
                  {isFinished ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#37E2C4]" />
                  ) : isCurrent ? (
                    <span className="w-2 h-2 rounded-full bg-[#F5A623] animate-ping" />
                  ) : (
                    <Clock className="w-3 h-3 text-[#8E96A0]" />
                  )}
                </div>
                <div className="font-bold text-[11px] uppercase truncate text-[#F2F1ED]">
                  {stepMeta.stationName.replace('STATION ', '').replace('// ', '')}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Real-time Sandbox Terminal Stream */}
      <div className="space-y-3">
        <TerminalLogs 
          logs={logs} 
          activeSubtask={status?.active_subtask} 
          isStreaming={!isComplete} 
        />
      </div>
    </div>
  );
};
