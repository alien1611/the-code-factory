// Types matching the provisional backend specification

export interface Repo {
  id: string;
  full_name: string; // "owner/repo"
  description?: string;
  stars?: number;
  forks?: number;
  language?: string;
  default_branch?: string;
}

export interface PullRequest {
  number: number;
  title: string;
  author: string;
  author_avatar?: string;
  updated_at: string;
  created_at?: string;
  branch: string;
  target_branch?: string;
  state?: string;
  additions: number;
  deletions: number;
  changed_files_count?: number;
  commits_count: number;
  description?: string;
  scenario_type?: 'verified' | 'violation';
}

export interface VerifyRequest {
  repo_full_name: string;
  pr_number: number;
}

export interface VerifyJobCreated {
  job_id: string;
  status: "queued";
}

export type PipelineStep = 
  | "queued"
  | "analyzing"
  | "extracting_requirements"
  | "generating_tests"
  | "running_tests"
  | "ai_verification"
  | "complete"
  | "failed";

export interface VerifyJobStatus {
  job_id: string;
  status: PipelineStep;
  current_step_label: string; // human-readable, for the progress screen
  progress_pct: number;       // 0-100
  logs?: string[];
  active_subtask?: string;
}

export interface TestCase {
  name: string;
  file: string;
  status: "pass" | "fail";
  message?: string;
  duration_ms?: number;
  category?: "unit" | "integration" | "property" | "adversarial" | "security";
}

export interface VerificationIssue {
  id: string;
  category: "security" | "static_analysis" | "ai_finding" | "requirement_violation";
  severity: "critical" | "high" | "medium" | "low";
  title: string;    // what failed
  file: string;
  line?: number;    // where
  evidence: string; // the proof
  why_it_matters: string;
  suggested_fix: string;
  code_snippet?: string;
  requirement_id?: string;
}

export interface VerifyResult {
  job_id: string;
  verdict: "VERIFIED" | "REQUIREMENT_VIOLATION";
  repo_full_name?: string;
  pr_number?: number;
  pr_title?: string;
  author?: string;
  branch?: string;
  commit_hash?: string;
  timestamp?: string;
  duration_sec?: number;
  summary: {
    tests: { status: "PASS" | "FAIL"; passed: number; total: number };
    security: { status: "PASS" | "FAIL"; issue_count: number };
    ai_check: { status: "PASS" | "FAIL" };
    requirements: { status: "PASS" | "FAIL" };
  };
  tests: TestCase[];
  issues: VerificationIssue[];
  requirements_checked?: {
    id: string;
    description: string;
    status: "PASS" | "FAIL";
  }[];
}
