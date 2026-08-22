import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ShieldCheck, 
  AlertOctagon, 
  RotateCcw, 
  Copy, 
  Check, 
  Share2, 
  Download, 
  ExternalLink, 
  FileCode, 
  FlaskConical, 
  CheckCircle2, 
  XCircle, 
  Sparkles, 
  Flame,
  ArrowRight,
  Filter
} from 'lucide-react';
import { VerifyResult, VerificationIssue } from '../lib/types';
import { getVerifyResult } from '../lib/api';
import { VerdictStamp } from '../components/VerdictStamp';
import { SummaryGrid } from '../components/SummaryGrid';
import { IssueCard } from '../components/IssueCard';
import { TestList } from '../components/TestList';

interface ResultsScreenProps {
  forcedScenario?: 'verified' | 'violation';
  onSwitchScenario?: (scenario: 'verified' | 'violation') => void;
}

export const ResultsScreen: React.FC<ResultsScreenProps> = ({
  forcedScenario,
  onSwitchScenario
}) => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [result, setResult] = useState<VerifyResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [currentScenario, setCurrentScenario] = useState<'verified' | 'violation' | undefined>(forcedScenario);
  const [copiedSummary, setCopiedSummary] = useState<boolean>(false);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  useEffect(() => {
    async function loadResult() {
      setIsLoading(true);
      try {
        const activeId = jobId || 'job-vfy-live';
        const res = await getVerifyResult(activeId, currentScenario);
        setResult(res);
        if (!currentScenario) {
          setCurrentScenario(res.verdict === 'VERIFIED' ? 'verified' : 'violation');
        }
      } catch (err) {
        console.error('Failed to load result:', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadResult();
  }, [jobId, currentScenario]);

  const handleScenarioToggle = (scenario: 'verified' | 'violation') => {
    setCurrentScenario(scenario);
    if (onSwitchScenario) {
      onSwitchScenario(scenario);
    }
  };

  const handleCopyMarkdownSummary = () => {
    if (!result) return;
    const isPass = result.verdict === 'VERIFIED';
    const issuesText = result.issues.length > 0 
      ? `### Flagged Violations (${result.issues.length})\n` + result.issues.map(i => `- **[${i.severity.toUpperCase()}]** ${i.title} (\`${i.file}:${i.line || 1}\`)\n  - *Evidence:* ${i.evidence}\n  - *Suggested Fix:* Available in dashboard`).join('\n')
      : '✅ All invariants mathematically proved and sealed.';

    const md = `## 🏭 Factory AI Code Verification Report

**Verdict:** ${isPass ? '✅ VERIFIED' : '❌ REQUIREMENT VIOLATION'}
**Repository:** \`${result.repo_full_name}#${result.pr_number}\`
**Commit:** \`${result.commit_hash}\`

### Summary Metrics
- **Tests:** ${result.summary.tests.passed}/${result.summary.tests.total} ${result.summary.tests.status}
- **Security:** ${result.summary.security.issue_count} issues (${result.summary.security.status})
- **AI Adversarial Check:** ${result.summary.ai_check.status}
- **Requirements Compliance:** ${result.summary.requirements.status}

${issuesText}
`;
    navigator.clipboard.writeText(md);
    setCopiedSummary(true);
    setTimeout(() => setCopiedSummary(false), 2500);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0B0D10] flex items-center justify-center p-8">
        <div className="text-center space-y-4 font-mono">
          <div className="w-12 h-12 border-2 border-[#37E2C4] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-[#8E96A0]">Generating Verification Certificate & Evidence Diff...</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="min-h-screen bg-[#0B0D10] text-[#F2F1ED] p-8 max-w-7xl mx-auto">
        <p>No verification result found for this job ID.</p>
        <Link to="/repos" className="text-[#37E2C4] underline text-xs font-mono mt-4 block">
          Return to repository selector
        </Link>
      </div>
    );
  }

  const isVerified = result.verdict === 'VERIFIED';
  const activeScenarioState = currentScenario || (isVerified ? 'verified' : 'violation');

  const filteredIssues = result.issues.filter(issue => {
    if (categoryFilter !== 'all' && issue.category !== categoryFilter) return false;
    if (severityFilter !== 'all' && issue.severity !== severityFilter) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#0B0D10] text-[#F2F1ED] py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-10">
      {/* Top Action Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#232A35] pb-4">
        {/* Scenario Switcher for Fast Hackathon Evaluation */}
        <div className="flex items-center gap-2 bg-[#14171D] border border-[#2A3038] p-1.5 rounded-lg">
          <span className="text-xs font-mono text-[#8E96A0] px-2 font-semibold">
            SWITCH DEMO PATH:
          </span>
          <button
            onClick={() => handleScenarioToggle('verified')}
            className={`px-3 py-1 text-xs font-mono font-bold rounded flex items-center gap-1.5 transition-all cursor-pointer ${
              activeScenarioState === 'verified'
                ? 'bg-[#37E2C4] text-[#0B0D10] shadow-[0_0_15px_rgba(55,226,196,0.4)]'
                : 'text-[#8E96A0] hover:text-[#37E2C4] hover:bg-[#1C222B]'
            }`}
            data-testid="toggle-verified-scenario"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            100% VERIFIED
          </button>
          <button
            onClick={() => handleScenarioToggle('violation')}
            className={`px-3 py-1 text-xs font-mono font-bold rounded flex items-center gap-1.5 transition-all cursor-pointer ${
              activeScenarioState === 'violation'
                ? 'bg-[#FF5C5C] text-[#0B0D10] shadow-[0_0_15px_rgba(255,92,92,0.4)]'
                : 'text-[#8E96A0] hover:text-[#FF5C5C] hover:bg-[#1C222B]'
            }`}
            data-testid="toggle-violation-scenario"
          >
            <AlertOctagon className="w-3.5 h-3.5" />
            REQUIREMENT VIOLATION
          </button>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleCopyMarkdownSummary}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded bg-[#14171D] hover:bg-[#1C222B] text-xs font-mono text-[#F2F1ED] border border-[#2A3038] transition-colors cursor-pointer"
            title="Copy PR Comment Markdown"
            data-testid="copy-summary-btn"
          >
            {copiedSummary ? (
              <>
                <Check className="w-3.5 h-3.5 text-[#37E2C4]" />
                <span className="text-[#37E2C4]">COPIED PR COMMENT</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-[#8E96A0]" />
                <span>COPY GITHUB PR COMMENT</span>
              </>
            )}
          </button>

          <button
            onClick={() => navigate('/repos')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded bg-[#14171D] hover:bg-[#1C222B] text-xs font-mono text-[#8E96A0] hover:text-[#F2F1ED] border border-[#2A3038] transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>VERIFY ANOTHER PR</span>
          </button>
        </div>
      </div>

      {/* 1. Big Top-Level Verdict Stamp */}
      <VerdictStamp
        verdict={result.verdict}
        repoFullName={result.repo_full_name}
        prNumber={result.pr_number}
        prTitle={result.pr_title}
        commitHash={result.commit_hash}
        branch={result.branch}
        durationSec={result.duration_sec}
        timestamp={result.timestamp}
      />

      {/* 2. Four-Row Summary Grid */}
      <SummaryGrid summary={result.summary} />

      {/* 3. Extracted Requirements Compliance Checklist */}
      {result.requirements_checked && result.requirements_checked.length > 0 && (
        <div className="rounded-lg border border-[#2A3038] bg-[#14171D] p-6 space-y-4" data-testid="requirements-checklist">
          <div className="flex items-center justify-between border-b border-[#232A35] pb-3">
            <div>
              <span className="text-xs font-mono text-[#F5A623] uppercase tracking-wider font-bold">
                PR SPECIFICATION INVARIANTS
              </span>
              <h3 className="font-sans font-bold text-lg text-[#F2F1ED] mt-0.5">
                Extracted Requirements & Proof Status
              </h3>
            </div>
            <span className="text-xs font-mono text-[#8E96A0]">
              {result.requirements_checked.filter(r => r.status === 'PASS').length} / {result.requirements_checked.length} PASSED
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {result.requirements_checked.map((req) => {
              const isPass = req.status === 'PASS';
              return (
                <div
                  key={req.id}
                  className={`p-3.5 rounded-md border text-xs font-mono flex items-start gap-3 ${
                    isPass 
                      ? 'bg-[#0B0D10] border-[#232A35] text-[#F2F1ED]' 
                      : 'bg-[#FF5C5C]/5 border-[#FF5C5C]/40 text-[#F2F1ED]'
                  }`}
                >
                  {isPass ? (
                    <CheckCircle2 className="w-4 h-4 text-[#37E2C4] shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-4 h-4 text-[#FF5C5C] shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-[#F5A623]">{req.id}</span>
                      <span className={`px-1.5 py-0.2 rounded text-[10px] uppercase font-bold ${
                        isPass ? 'bg-[#37E2C4]/20 text-[#37E2C4]' : 'bg-[#FF5C5C]/20 text-[#FF5C5C]'
                      }`}>
                        {req.status}
                      </span>
                    </div>
                    <p className="text-xs text-[#8E96A0] leading-relaxed">
                      {req.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. Violation Issues List (If Flaws Found) */}
      {!isVerified && result.issues.length > 0 && (
        <div className="space-y-4" data-testid="issues-container">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#232A35] pb-3">
            <div>
              <span className="text-xs font-mono text-[#FF5C5C] font-bold uppercase tracking-wider">
                BLOCKING FINDINGS
              </span>
              <h2 className="font-['Big_Shoulders_Display'] text-3xl font-black uppercase text-[#F2F1ED]">
                IDENTIFIED VIOLATIONS & FIX PATCHES ({result.issues.length})
              </h2>
            </div>

            {/* Filter toolbar */}
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
              <span className="text-[#8E96A0] flex items-center gap-1">
                <Filter className="w-3 h-3" />
                FILTER:
              </span>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="bg-[#14171D] border border-[#2A3038] rounded px-2 py-1 text-xs font-mono text-[#F2F1ED] focus:outline-none focus:border-[#37E2C4]"
              >
                <option value="all">All Categories</option>
                <option value="requirement_violation">Requirement Violations</option>
                <option value="security">Security</option>
                <option value="ai_finding">AI Findings</option>
                <option value="static_analysis">Static Analysis</option>
              </select>

              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-[#14171D] border border-[#2A3038] rounded px-2 py-1 text-xs font-mono text-[#F2F1ED] focus:outline-none focus:border-[#37E2C4]"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
              </select>
            </div>
          </div>

          <div className="space-y-4" data-testid="issue-cards-list">
            {filteredIssues.map((issue) => (
              <IssueCard key={issue.id} issue={issue} defaultExpanded={true} />
            ))}
          </div>
        </div>
      )}

      {/* 5. Dynamic Test Suite List */}
      <TestList 
        tests={result.tests} 
        defaultExpanded={isVerified} 
      />
    </div>
  );
};
