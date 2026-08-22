// TODO: confirm against real backend response
// API Client isolating backend communication behind provisional contracts

import { 
  Repo, 
  PullRequest, 
  VerifyRequest, 
  VerifyJobCreated, 
  VerifyJobStatus, 
  VerifyResult,
  PipelineStep
} from './types';
import { 
  MOCK_REPOS, 
  MOCK_PRS, 
  MOCK_VERIFIED_RESULT, 
  MOCK_VIOLATION_RESULT,
  PIPELINE_STEPS_META 
} from './mockData';

// In-memory job state tracking for realistic simulated polling
interface SimulatedJob {
  job_id: string;
  repo_full_name: string;
  pr_number: number;
  scenario: 'verified' | 'violation';
  started_at: number;
  current_step_index: number;
  total_steps: number;
  accumulated_logs: string[];
}

const activeJobs = new Map<string, SimulatedJob>();

// Helper to delay simulation
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * GET /api/repos -> repos available after GitHub connect
 */
export async function getRepos(): Promise<Repo[]> {
  await delay(150);
  return MOCK_REPOS;
}

/**
 * GET /api/repos/{repo_id}/pulls -> open PRs for a repo
 */
export async function getPullRequests(repoId: string): Promise<PullRequest[]> {
  await delay(150);
  return MOCK_PRS[repoId] || [];
}

/**
 * POST /api/verify -> starts a verification job
 */
export async function createVerifyJob(request: VerifyRequest, forcedScenario?: 'verified' | 'violation'): Promise<VerifyJobCreated> {
  await delay(200);
  const jobId = `job-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
  
  // Determine if this PR is a violation or verified based on metadata or explicit choice
  let scenario: 'verified' | 'violation' = forcedScenario || 'verified';
  
  if (!forcedScenario) {
    // Check if PR number corresponds to known violation PRs (like #89 or #148)
    if (request.pr_number === 89 || request.pr_number === 148 || request.repo_full_name.includes('auth-core')) {
      scenario = 'violation';
    } else {
      scenario = 'verified';
    }
  }

  activeJobs.set(jobId, {
    job_id: jobId,
    repo_full_name: request.repo_full_name,
    pr_number: request.pr_number,
    scenario,
    started_at: Date.now(),
    current_step_index: 0,
    total_steps: PIPELINE_STEPS_META.length,
    accumulated_logs: [...PIPELINE_STEPS_META[0].logs]
  });

  return {
    job_id: jobId,
    status: 'queued'
  };
}

/**
 * GET /api/verify/{job_id} -> poll while it runs
 */
export async function getVerifyJobStatus(jobId: string): Promise<VerifyJobStatus> {
  await delay(100);
  
  const job = activeJobs.get(jobId);
  
  // If not found in active map, return completed or fallback
  if (!job) {
    return {
      job_id: jobId,
      status: 'complete',
      current_step_label: 'Verification Complete',
      progress_pct: 100,
      logs: ['Job completed']
    };
  }

  const elapsedMs = Date.now() - job.started_at;
  
  // Calculate current step based on elapsed time across steps
  let cumulativeTime = 0;
  let stepIndex = 0;
  
  for (let i = 0; i < PIPELINE_STEPS_META.length; i++) {
    cumulativeTime += PIPELINE_STEPS_META[i].durationMs;
    if (elapsedMs < cumulativeTime) {
      stepIndex = i;
      break;
    }
    if (i === PIPELINE_STEPS_META.length - 1) {
      stepIndex = PIPELINE_STEPS_META.length - 1;
    }
  }

  job.current_step_index = stepIndex;
  
  // Gather all logs up to current step
  const allLogs: string[] = [];
  for (let i = 0; i <= stepIndex; i++) {
    allLogs.push(...PIPELINE_STEPS_META[i].logs);
  }
  job.accumulated_logs = allLogs;

  const currentMeta = PIPELINE_STEPS_META[stepIndex];
  const isComplete = stepIndex === PIPELINE_STEPS_META.length - 1;
  const progressPct = isComplete 
    ? 100 
    : Math.min(95, Math.round((elapsedMs / (cumulativeTime + 1000)) * 100));

  return {
    job_id: jobId,
    status: currentMeta.key,
    current_step_label: currentMeta.label,
    progress_pct: progressPct,
    logs: allLogs,
    active_subtask: currentMeta.stationName
  };
}

/**
 * GET /api/verify/{job_id}/result -> once status === "complete"
 */
export async function getVerifyResult(jobId: string, forcedScenario?: 'verified' | 'violation'): Promise<VerifyResult> {
  await delay(150);
  
  const job = activeJobs.get(jobId);
  const scenario = forcedScenario || (job ? job.scenario : 'violation');

  if (scenario === 'verified') {
    return {
      ...MOCK_VERIFIED_RESULT,
      job_id: jobId,
      repo_full_name: job?.repo_full_name || MOCK_VERIFIED_RESULT.repo_full_name,
      pr_number: job?.pr_number || MOCK_VERIFIED_RESULT.pr_number,
    };
  } else {
    return {
      ...MOCK_VIOLATION_RESULT,
      job_id: jobId,
      repo_full_name: job?.repo_full_name || MOCK_VIOLATION_RESULT.repo_full_name,
      pr_number: job?.pr_number || MOCK_VIOLATION_RESULT.pr_number,
    };
  }
}
