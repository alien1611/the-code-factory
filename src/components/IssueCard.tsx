import React, { useState } from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  Bug, 
  FileCode, 
  Check, 
  Copy, 
  ChevronDown, 
  ChevronUp, 
  Sparkles, 
  Terminal,
  ArrowRight,
  ExternalLink,
  Flame
} from 'lucide-react';
import { VerificationIssue } from '../lib/types';

interface IssueCardProps {
  issue: VerificationIssue;
  defaultExpanded?: boolean;
}

export const IssueCard: React.FC<IssueCardProps> = ({ 
  issue, 
  defaultExpanded = true 
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  const handleCopyFix = () => {
    navigator.clipboard.writeText(issue.suggested_fix);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getSeverityStyle = (severity: VerificationIssue['severity']) => {
    switch (severity) {
      case 'critical':
        return 'bg-[#FF5C5C]/20 text-[#FF5C5C] border-[#FF5C5C]/50';
      case 'high':
        return 'bg-[#F5A623]/20 text-[#F5A623] border-[#F5A623]/50';
      case 'medium':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'low':
        return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
    }
  };

  const getCategoryIcon = (category: VerificationIssue['category']) => {
    switch (category) {
      case 'security':
        return <ShieldAlert className="w-4 h-4 text-[#FF5C5C]" />;
      case 'requirement_violation':
        return <AlertTriangle className="w-4 h-4 text-[#FF5C5C]" />;
      case 'ai_finding':
        return <Sparkles className="w-4 h-4 text-[#F5A623]" />;
      case 'static_analysis':
        return <Bug className="w-4 h-4 text-amber-400" />;
    }
  };

  return (
    <div 
      className="rounded-lg border border-[#2A3038] bg-[#14171D] overflow-hidden transition-all duration-200 hover:border-[#37E2C4]/30"
      data-testid={`issue-card-${issue.id}`}
    >
      {/* Header Bar */}
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className="p-4 sm:p-5 flex items-start sm:items-center justify-between gap-4 cursor-pointer select-none bg-[#181C23] border-b border-[#232A35]"
      >
        <div className="flex items-start sm:items-center gap-3">
          <div className="mt-0.5 sm:mt-0 p-2 rounded bg-[#0B0D10] border border-[#2A3038]">
            {getCategoryIcon(issue.category)}
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${getSeverityStyle(issue.severity)}`}>
                {issue.severity}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase tracking-wider bg-[#2A3038] text-[#8E96A0]">
                {issue.category.replace('_', ' ')}
              </span>
              <span className="text-xs font-mono text-[#8E96A0]">
                #{issue.id}
              </span>
            </div>
            <h3 className="font-sans font-bold text-base sm:text-lg text-[#F2F1ED] leading-snug">
              {issue.title}
            </h3>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* File location badge */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#0B0D10] border border-[#232A35] font-mono text-xs text-[#8E96A0]">
            <FileCode className="w-3.5 h-3.5 text-[#F5A623]" />
            <span className="text-[#F2F1ED]">{issue.file}</span>
            {issue.line && <span className="text-[#F5A623]">:{issue.line}</span>}
          </div>

          <button 
            type="button"
            className="p-1 rounded text-[#8E96A0] hover:text-[#F2F1ED] transition-colors"
            aria-label={isExpanded ? "Collapse issue" : "Expand issue"}
          >
            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4 sm:p-6 space-y-6">
          {/* Mobile File location */}
          <div className="md:hidden flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-[#0B0D10] border border-[#232A35] font-mono text-xs text-[#8E96A0]">
            <FileCode className="w-3.5 h-3.5 text-[#F5A623]" />
            <span className="text-[#F2F1ED]">{issue.file}</span>
            {issue.line && <span className="text-[#F5A623]">:{issue.line}</span>}
          </div>

          {/* Section 1: Code Context / Offending Snippet if present */}
          {issue.code_snippet && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#8E96A0] flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-[#FF5C5C]" />
                  OFFENDING IMPLEMENTATION (WHERE)
                </span>
                <span className="text-[11px] font-mono text-[#8E96A0]">
                  Line {issue.line || 1}
                </span>
              </div>
              <div className="relative rounded-md bg-[#0B0D10] border border-[#232A35] p-3.5 font-mono text-xs text-[#F2F1ED] overflow-x-auto">
                <pre className="leading-relaxed text-red-200/90 font-mono">
                  {issue.code_snippet}
                </pre>
              </div>
            </div>
          )}

          {/* Section 2: Evidence & Proof */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-md border border-[#232A35] bg-[#0E1116] p-4">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#37E2C4] flex items-center gap-1.5 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-[#37E2C4]" />
                THE PROOF // EVIDENCE
              </span>
              <p className="text-xs sm:text-sm text-[#F2F1ED] leading-relaxed">
                {issue.evidence}
              </p>
            </div>

            {/* Section 3: Why It Matters */}
            <div className="rounded-md border border-[#232A35] bg-[#0E1116] p-4">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#F5A623] flex items-center gap-1.5 mb-2">
                <Flame className="w-3.5 h-3.5 text-[#F5A623]" />
                WHY IT MATTERS // RISK
              </span>
              <p className="text-xs sm:text-sm text-[#F2F1ED] leading-relaxed">
                {issue.why_it_matters}
              </p>
            </div>
          </div>

          {/* Section 4: Suggested Fix */}
          <div className="rounded-md border border-[#37E2C4]/30 bg-[#0E1116] overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 bg-[#14171D] border-b border-[#232A35]">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#37E2C4] flex items-center gap-1.5">
                <Check className="w-3.5 h-3.5 text-[#37E2C4]" />
                SUGGESTED VERIFICATION PATCH
              </span>
              <button
                onClick={handleCopyFix}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#232A35] hover:bg-[#2A3038] text-xs font-mono text-[#F2F1ED] transition-colors cursor-pointer"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[#37E2C4]" />
                    <span>COPIED</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-[#8E96A0]" />
                    <span>COPY PATCH</span>
                  </>
                )}
              </button>
            </div>
            <div className="p-4 font-mono text-xs text-[#37E2C4] overflow-x-auto bg-[#0B0D10]">
              <pre className="leading-relaxed font-mono">
                {issue.suggested_fix}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
