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
  Filter,
  AlertTriangle,
  RefreshCw,
  Key
} from 'lucide-react';
import { VerifyResult, VerificationIssue } from '../lib/types';
import { getVerifyResult, createVerifyJob } from '../lib/api';
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
  const [isRetrying, setIsRetrying] = useState<boolean>(false);
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
        if (!currentScenario && res.verdict !== 'UNABLE_TO_VERIFY' && res.verdict !== 'FAILED') {
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

  const handleRetry = async () => {
    if (!result) return;
    setIsRetrying(true);
    try {
      const newJob = await createVerifyJob({
        repo_full_name: result.repo_full_name || 'acme-corp/auth-core',
        pr_number: result.pr_number || 1
      });
      navigate(`/verify/${newJob.job_id}`);
    } catch (err) {
      console.error('Failed to retry verification:', err);
      setIsRetrying(false);
    }
  };

  const handleCopyMarkdownSummary = () => {
    if (!result) return;
    const isPass = result.verdict === 'VERIFIED';
    const isUnable = result.verdict === 'UNABLE_TO_VERIFY' || result.verdict === 'FAILED';

    if (isUnable) {
      const md = `## 🏭 Factory AI Code Verification Report

**Verdict:** ⚠️ UNABLE TO VERIFY
**Repository:** \`${result.repo_full_name}#${result.pr_number}\`
**Status:** Verification could not be completed at this time. Please try again later.
`;
      navigator.clipboard.writeText(md);
      setCopiedSummary(true);
      setTimeout(() => setCopiedSummary(false), 2500);
      return;
    }

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
  const isUnable = result.verdict === 'UNABLE_TO_VERIFY' || result.verdict === 'FAILED';

  const filteredIssues = result.issues.filter(issue => {
    if (categoryFilter !== 'all' && issue.category !== categoryFilter) return false;
    if (severityFilter !== 'all' && issue.severity !== severityFilter) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#0B0D10] text-[#F2F1ED] py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-10">
      {/* Top Action Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#232A35] pb-4">
        {/* Real Verification Station Indicator */}
        <div className="flex items-center gap-2">
          <Link
            to="/repos"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#14171D] hover:bg-[#1C222B] text-xs font-mono text-[#8E96A0] hover:text-[#37E2C4] border border-[#2A3038] transition-colors cursor-pointer"
          >
            <span>← INTAKE DOCK</span>
          </Link>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#14171D] border border-[#2A3038] text-xs font-mono text-[#F2F1ED]">
            <span className="text-[#8E96A0]">VERIFIED JOB:</span>
            <span className="text-[#F5A623] font-bold">#{jobId || result.job_id}</span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-3">
          {!isUnable && (
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
          )}

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
        errorMessage={result.error_message}
      />

      {/* If UNABLE TO VERIFY: Dedicated Clean Notice Banner with Retry Button */}
      {isUnable && (
        <div className="p-6 sm:p-8 rounded-xl border border-[#F5A623]/40 bg-[#14171D] shadow-2xl space-y-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-[#F5A623]/10 border border-[#F5A623]/30 text-[#F5A623]">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div className="space-y-2 flex-1">
              <h2 className="font-mono text-lg font-bold text-[#F2F1ED]">
                AI VERIFICATION TEMPORARILY UNAVAILABLE
              </h2>
              <p className="text-sm text-[#8E96A0] leading-relaxed">
                {result.error_message || "The verification engine was unable to analyze this code change due to temporary API rate limits or quota constraints. Please try again later."}
              </p>
              <div className="p-3 rounded-lg bg-[#0B0D10] border border-[#232A35] text-xs font-mono text-[#8E96A0] space-y-1">
                <div className="flex items-center gap-2 text-[#37E2C4] font-bold">
                  <Key className="w-3.5 h-3.5" />
                  <span>MULTI-KEY FAILOVER ACTIVE</span>
                </div>
                <p>
                  You can configure up to 5 Gemini API keys in <code className="text-[#F2F1ED]">backend/.env</code> (<code className="text-[#F5A623]">GEMINI_API_KEY_1</code> ... <code className="text-[#F5A623]">GEMINI_API_KEY_5</code>). If one key hits quota limits, the engine will automatically failover to the next healthy key in real time.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-[#232A35]">
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded bg-[#F5A623] hover:bg-[#F5A623]/90 text-[#0B0D10] font-mono font-bold text-xs shadow-[0_0_20px_rgba(245,166,35,0.3)] transition-all cursor-pointer disabled:opacity-50"
            >
              {isRetrying ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>RETRYING VERIFICATION...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>RETRY VERIFICATION NOW</span>
                </>
              )}
            </button>
            <Link
              to="/repos"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded bg-[#0B0D10] hover:bg-[#1C222B] text-[#8E96A0] hover:text-[#F2F1ED] font-mono text-xs border border-[#2A3038] transition-colors"
            >
              <span>Back to Repositories</span>
            </Link>
          </div>
        </div>
      )}

      {/* Normal Verification Sections */}
      {!isUnable && (
        <>
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
        </>
      )}
    </div>
  );
};
