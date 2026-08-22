import { Repo, PullRequest, VerifyResult, PipelineStep } from './types';

export const MOCK_REPOS: Repo[] = [
  {
    id: 'repo-1',
    full_name: 'acme-corp/auth-core',
    description: 'Zero-trust authentication & authorization middleware with JWT and session revocation',
    stars: 342,
    forks: 48,
    language: 'TypeScript',
    default_branch: 'main',
  },
  {
    id: 'repo-2',
    full_name: 'octocat/payment-gateway-service',
    description: 'High-throughput payment orchestration engine with idempotency & ledger reconciliation',
    stars: 1289,
    forks: 194,
    language: 'Go / TypeScript',
    default_branch: 'main',
  },
  {
    id: 'repo-3',
    full_name: 'hyperlink/data-pipeline',
    description: 'Distributed streaming ETL engine for high-cardinality telemetry ingestion',
    stars: 840,
    forks: 92,
    language: 'Rust',
    default_branch: 'master',
  },
  {
    id: 'repo-4',
    full_name: 'nebula-cloud/k8s-operator',
    description: 'Autonomous Kubernetes custom resource controller for zero-downtime canary rollouts',
    stars: 512,
    forks: 67,
    language: 'Go',
    default_branch: 'main',
  }
];

export const MOCK_PRS: Record<string, PullRequest[]> = {
  'repo-1': [
    {
      number: 89,
      title: 'Implement token refresh endpoint & role-based scoping (Contains Flaws)',
      author: 'alex-dev',
      author_avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=64&h=64&fit=crop&crop=faces',
      updated_at: '12 mins ago',
      created_at: '2 hours ago',
      branch: 'feat/token-refresh-scopes',
      target_branch: 'main',
      additions: 384,
      deletions: 42,
      commits_count: 4,
      scenario_type: 'violation',
    },
    {
      number: 94,
      title: 'Upgrade Argon2id hashing params and enforce RFC 6749 grant validation',
      author: 'sarah-sec',
      author_avatar: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=64&h=64&fit=crop&crop=faces',
      updated_at: '1 hour ago',
      created_at: '5 hours ago',
      branch: 'sec/argon2-upgrade',
      target_branch: 'main',
      additions: 120,
      deletions: 35,
      commits_count: 2,
      scenario_type: 'verified',
    }
  ],
  'repo-2': [
    {
      number: 142,
      title: 'Add idempotent Stripe webhook handler with HMAC-SHA256 signature check & exponential retry',
      author: 'david-fintech',
      author_avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=64&h=64&fit=crop&crop=faces',
      updated_at: '5 mins ago',
      created_at: '3 hours ago',
      branch: 'feat/idempotent-stripe-webhooks',
      target_branch: 'main',
      additions: 512,
      deletions: 18,
      commits_count: 6,
      scenario_type: 'verified',
    },
    {
      number: 148,
      title: 'Optimize batch ledger settlement query with materialized cache',
      author: 'elena-data',
      author_avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=64&h=64&fit=crop&crop=faces',
      updated_at: '45 mins ago',
      created_at: '1 day ago',
      branch: 'perf/ledger-batch-cache',
      target_branch: 'main',
      additions: 195,
      deletions: 88,
      commits_count: 3,
      scenario_type: 'violation',
    }
  ],
  'repo-3': [
    {
      number: 62,
      title: 'Stream windowing partitioner with watermarked backpressure',
      author: 'marcus-stream',
      author_avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=64&h=64&fit=crop&crop=faces',
      updated_at: '2 hours ago',
      created_at: '1 day ago',
      branch: 'feat/backpressure-watermarks',
      target_branch: 'master',
      additions: 430,
      deletions: 110,
      commits_count: 5,
      scenario_type: 'verified',
    }
  ],
  'repo-4': [
    {
      number: 31,
      title: 'Canary traffic split controller with Prometheus SLO feedback loop',
      author: 'priya-ops',
      author_avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=64&h=64&fit=crop&crop=faces',
      updated_at: '3 hours ago',
      created_at: '2 days ago',
      branch: 'feat/slo-canary-feedback',
      target_branch: 'main',
      additions: 290,
      deletions: 45,
      commits_count: 3,
      scenario_type: 'verified',
    }
  ]
};

export const PIPELINE_STEPS_META: {
  key: PipelineStep;
  label: string;
  stationName: string;
  durationMs: number;
  logs: string[];
}[] = [
  {
    key: 'queued',
    label: 'Job Queued in Verification Pipeline',
    stationName: 'DISPATCH DOCK',
    durationMs: 800,
    logs: [
      '[DISPATCH] Job #vfy-8902 received from GitHub webhook',
      '[DISPATCH] Fetching PR diff, commit history and AST tree...',
      '[DISPATCH] Allocating isolated container sandbox environment #sbx-992'
    ]
  },
  {
    key: 'analyzing',
    label: 'Analyzing Repository AST & Code Semantics',
    stationName: 'STATION 01 // ANALYZE',
    durationMs: 1400,
    logs: [
      '[ANALYZE] Parsing modified AST nodes (4 files changed, +384 / -42)',
      '[ANALYZE] Building dependency call-graph and control-flow matrix',
      '[ANALYZE] Running static AST lint and type boundary verification',
      '[ANALYZE] Completed syntax tree validation (0 syntax errors)'
    ]
  },
  {
    key: 'extracting_requirements',
    label: 'Extracting PR Intent & Architectural Invariants',
    stationName: 'STATION 02 // EXTRACT',
    durationMs: 1600,
    logs: [
      '[EXTRACT] Parsing PR description, linked Jira issues, and commit messages',
      '[EXTRACT] Synthesizing behavioral contract: 4 core invariants detected',
      '[EXTRACT] Requirement 1: Token renewal must enforce expiration boundaries',
      '[EXTRACT] Requirement 2: Scopes must strictly subset the parent grant',
      '[EXTRACT] Requirement 3: Revoked refresh tokens must cascade invalidate child sessions',
      '[EXTRACT] Requirement 4: Concurrent token requests must maintain atomic lock'
    ]
  },
  {
    key: 'generating_tests',
    label: 'Synthesizing Adversarial Test Cases & Edge Conditions',
    stationName: 'STATION 03 // SYNTHESIZE',
    durationMs: 1800,
    logs: [
      '[SYNTHESIZE] Generating property-based test harness for state transitions',
      '[SYNTHESIZE] Injecting 15 adversarial fuzz vectors (race conditions, null-byte payloads, expired epochs)',
      '[SYNTHESIZE] Generating mock storage ledger with 10k synthetic concurrent sessions',
      '[SYNTHESIZE] Test suite generated: 17 total test cases compiled into runner'
    ]
  },
  {
    key: 'running_tests',
    label: 'Executing Sandboxed Dynamic Test Suite',
    stationName: 'STATION 04 // RUN TESTS',
    durationMs: 1600,
    logs: [
      '[RUNNER] Executing unit test suite: 12 tests passed (42ms)',
      '[RUNNER] Executing concurrent race-condition simulation (threads=50)',
      '[RUNNER] Executing fuzzing vectors against token serialization',
      '[RUNNER] Collecting coverage profile & memory allocation traces'
    ]
  },
  {
    key: 'ai_verification',
    label: 'Running AI Adversarial Verification Engine',
    stationName: 'STATION 05 // AI VERIFICATION',
    durationMs: 2000,
    logs: [
      '[AI_VERIFY] Proving formal semantic equivalence against PR requirements',
      '[AI_VERIFY] Inspecting security boundary: checking timing attacks on hash compare',
      '[AI_VERIFY] Checking token replay protection and distributed lock leases',
      '[AI_VERIFY] Evidence synthesis completed with AST node proof mapping'
    ]
  },
  {
    key: 'complete',
    label: 'Verification Finished // Stamp Sealed',
    stationName: 'STATION 06 // SEALED',
    durationMs: 500,
    logs: [
      '[VERDICT] Verification report generated successfully',
      '[VERDICT] Packaging artifacts, evidence attachments, and suggested patches'
    ]
  }
];

export const MOCK_VERIFIED_RESULT: VerifyResult = {
  job_id: 'job-vfy-142-pass',
  verdict: 'VERIFIED',
  repo_full_name: 'octocat/payment-gateway-service',
  pr_number: 142,
  pr_title: 'Add idempotent Stripe webhook handler with HMAC-SHA256 signature check & exponential retry',
  author: 'david-fintech',
  branch: 'feat/idempotent-stripe-webhooks',
  commit_hash: '9a7e3b1c',
  timestamp: 'Just now',
  duration_sec: 4.8,
  summary: {
    tests: { status: 'PASS', passed: 18, total: 18 },
    security: { status: 'PASS', issue_count: 0 },
    ai_check: { status: 'PASS' },
    requirements: { status: 'PASS' },
  },
  requirements_checked: [
    { id: 'REQ-01', description: 'Stripe signature header is verified using constant-time HMAC-SHA256 compare', status: 'PASS' },
    { id: 'REQ-02', description: 'Webhook events are de-duplicated via Redis idempotency key with 24h TTL', status: 'PASS' },
    { id: 'REQ-03', description: 'Failed webhook transactions trigger jittered exponential backoff retries', status: 'PASS' },
    { id: 'REQ-04', description: 'Idempotency lock prevents concurrent race-condition double-charges', status: 'PASS' },
    { id: 'REQ-05', description: 'All monetary values are parsed as integer cents to avoid floating-point loss', status: 'PASS' },
  ],
  tests: [
    {
      name: 'test_stripe_webhook_signature_valid',
      file: 'services/webhook_handler_test.go',
      status: 'pass',
      duration_ms: 12,
      category: 'unit',
      message: 'Verified constant-time crypto comparison under 1,000 randomized signatures'
    },
    {
      name: 'test_stripe_webhook_signature_tampered_payload_rejected',
      file: 'services/webhook_handler_test.go',
      status: 'pass',
      duration_ms: 15,
      category: 'security',
      message: 'Tampered byte in JSON body immediately rejected with 400 Bad Signature'
    },
    {
      name: 'test_idempotency_concurrent_duplicate_events_isolated',
      file: 'services/idempotency_test.go',
      status: 'pass',
      duration_ms: 85,
      category: 'adversarial',
      message: '100 concurrent parallel deliveries of identical event ID resulted in exactly 1 ledger charge'
    },
    {
      name: 'test_retry_exponential_backoff_with_full_jitter',
      file: 'services/retry_policy_test.go',
      status: 'pass',
      duration_ms: 45,
      category: 'property',
      message: 'Retry intervals verified within [t * 2^attempt ± random_jitter]'
    },
    {
      name: 'test_integer_cents_currency_precision',
      file: 'domain/currency_test.go',
      status: 'pass',
      duration_ms: 8,
      category: 'unit',
      message: 'No floating-point IEEE-754 precision drift detected across 100k random transactions'
    },
    {
      name: 'test_redis_outage_fallback_to_postgres_advisory_lock',
      file: 'storage/lock_manager_test.go',
      status: 'pass',
      duration_ms: 62,
      category: 'integration',
      message: 'Graceful degradation to database row lock when Redis cluster unreachable'
    }
  ],
  issues: []
};

export const MOCK_VIOLATION_RESULT: VerifyResult = {
  job_id: 'job-vfy-89-fail',
  verdict: 'REQUIREMENT_VIOLATION',
  repo_full_name: 'acme-corp/auth-core',
  pr_number: 89,
  pr_title: 'Implement token refresh endpoint & role-based scoping (Contains Flaws)',
  author: 'alex-dev',
  branch: 'feat/token-refresh-scopes',
  commit_hash: '3d8f14a9',
  timestamp: 'Just now',
  duration_sec: 6.2,
  summary: {
    tests: { status: 'FAIL', passed: 14, total: 17 },
    security: { status: 'FAIL', issue_count: 3 },
    ai_check: { status: 'FAIL' },
    requirements: { status: 'FAIL' },
  },
  requirements_checked: [
    { id: 'REQ-01', description: 'Refresh endpoint generates valid cryptographically random token pair', status: 'PASS' },
    { id: 'REQ-02', description: 'Access token claims match configured role permissions', status: 'PASS' },
    { id: 'REQ-03', description: 'Revoked refresh tokens must cascade and invalidate all active child sessions', status: 'FAIL' },
    { id: 'REQ-04', description: 'Concurrent refresh requests on the same token must be atomic and reject replays', status: 'FAIL' },
    { id: 'REQ-05', description: "Requested scopes must strictly subset the user's authorized grants", status: 'FAIL' },
  ],
  tests: [
    {
      name: 'test_token_pair_generation',
      file: 'src/tokens/generator.spec.ts',
      status: 'pass',
      duration_ms: 18,
      category: 'unit',
      message: 'Generated tokens contain high-entropy 256-bit CSPRNG payload'
    },
    {
      name: 'test_jwt_claims_schema_conformance',
      file: 'src/tokens/jwt.spec.ts',
      status: 'pass',
      duration_ms: 22,
      category: 'unit',
      message: 'JWT exp, iat, sub, iss fields conform to RFC 7519'
    },
    {
      name: 'test_session_cascade_invalidation_on_revoke',
      file: 'src/services/sessionManager.spec.ts',
      status: 'fail',
      duration_ms: 94,
      category: 'adversarial',
      message: 'AssertionError: Expected 0 active sessions after refresh token revocation, but found 3 remaining active sessions in cache'
    },
    {
      name: 'test_concurrent_refresh_replay_protection',
      file: 'src/routes/refresh.spec.ts',
      status: 'fail',
      duration_ms: 120,
      category: 'adversarial',
      message: 'RaceConditionError: Parallel refresh invocation allowed double-spending of single-use refresh token'
    },
    {
      name: 'test_scope_escalation_guard',
      file: 'src/middleware/scopeGuard.spec.ts',
      status: 'fail',
      duration_ms: 41,
      category: 'security',
      message: 'PrivilegeEscalationError: User with [read:profile] requested [write:admin] and received access token'
    }
  ],
  issues: [
    {
      id: 'ISSUE-01',
      category: 'requirement_violation',
      severity: 'critical',
      title: 'Session Revocation Does Not Cascade to Child Sessions',
      file: 'src/services/sessionManager.ts',
      line: 142,
      code_snippet: '// src/services/sessionManager.ts:140-146\nexport async function revokeRefreshToken(tokenId: string): Promise<void> {\n  // Bug: Only deletes the single refresh row, leaves active JWT sessions alive in Redis!\n  await db.refreshToken.update({\n    where: { id: tokenId },\n    data: { revokedAt: new Date() }\n  });\n  // MISSING: await redis.del(`session:family:${tokenId}`);\n}',
      evidence: 'PR requirement REQ-03 explicitly dictates: "Revoking a refresh token must invalidate all active child access tokens immediately." Test test_session_cascade_invalidation_on_revoke verified 3 active JWTs remained valid for 15 minutes after parent revocation.',
      why_it_matters: 'If a user logs out or reports a compromised device, attackers retain full API access using already-issued child tokens until they naturally expire.',
      suggested_fix: 'export async function revokeRefreshToken(tokenId: string): Promise<void> {\n  const token = await db.refreshToken.update({\n    where: { id: tokenId },\n    data: { revokedAt: new Date() },\n    include: { sessionFamily: true }\n  });\n  \n  // Blacklist session family in high-speed distributed cache\n  await redis.setex(`blacklist:family:${token.familyId}`, 3600, \'revoked\');\n  await eventBus.publish(\'auth.session.revoked\', { familyId: token.familyId });\n}'
    },
    {
      id: 'ISSUE-02',
      category: 'security',
      severity: 'high',
      title: 'Race Condition Allows Concurrent Refresh Token Reuse (Replay Attack)',
      file: 'src/routes/refresh.ts',
      line: 78,
      code_snippet: '// src/routes/refresh.ts:76-84\nconst currentToken = await db.refreshToken.findUnique({ where: { token: req.body.refreshToken } });\nif (!currentToken || currentToken.revokedAt) {\n  return res.status(401).json({ error: "Invalid token" });\n}\n\n// Window of vulnerability between read and update:\nconst newTokens = await issueNewTokenPair(currentToken.userId);\nawait db.refreshToken.update({ where: { id: currentToken.id }, data: { revokedAt: new Date() } });',
      evidence: 'AI adversarial fuzzing simulated two simultaneous refresh POST requests spaced 4ms apart. Both threads read revokedAt === null and succeeded, generating two valid unlinked token lineages from a single refresh token.',
      why_it_matters: 'Breaks OAuth 2.0 RFC 6819 Section 5.2.2.3 single-use refresh token invariant. Attackers intercepting a token can race legitimate clients and establish undetected persistent access.',
      suggested_fix: '// Use atomic find-and-update or database row-level locking with optimistic locking\nconst updated = await db.refreshToken.updateMany({\n  where: { \n    token: req.body.refreshToken, \n    revokedAt: null \n  },\n  data: { revokedAt: new Date() }\n});\n\nif (updated.count === 0) {\n  // Token was already consumed! Trigger automated compromise alarm:\n  await triggerTokenReuseAlert(req.body.refreshToken);\n  return res.status(401).json({ error: "Token reuse detected" });\n}'
    },
    {
      id: 'ISSUE-03',
      category: 'ai_finding',
      severity: 'high',
      title: 'Unchecked Scope Parameter Allows Arbitrary Privilege Escalation',
      file: 'src/middleware/scopeGuard.ts',
      line: 55,
      code_snippet: '// src/middleware/scopeGuard.ts:52-58\nexport function resolveRequestedScopes(userScopes: string[], requestedScopes?: string[]): string[] {\n  if (!requestedScopes || requestedScopes.length === 0) {\n    return userScopes;\n  }\n  // Flaw: returns requestedScopes directly without intersecting with userScopes!\n  return requestedScopes;\n}',
      evidence: 'Static AST & AI logic prover showed resolveRequestedScopes accepts arbitrary client-supplied scope strings without computing set intersection against user.assigned_roles.',
      why_it_matters: 'Any standard user account can escalate their permissions to ["admin:*", "billing:write", "system:root"] simply by including ?scope=admin:* in the refresh request query body.',
      suggested_fix: 'export function resolveRequestedScopes(userScopes: string[], requestedScopes?: string[]): string[] {\n  const allowedSet = new Set(userScopes);\n  if (!requestedScopes || requestedScopes.length === 0) {\n    return userScopes;\n  }\n  const filtered = requestedScopes.filter(scope => allowedSet.has(scope));\n  if (filtered.length !== requestedScopes.length) {\n    throw new ForbiddenError("Requested scopes exceed user permissions");\n  }\n  return filtered;\n}'
    },
    {
      id: 'ISSUE-04',
      category: 'static_analysis',
      severity: 'medium',
      title: 'Insecure Direct Object Reference (IDOR) on User Profile Attachment',
      file: 'src/controllers/userController.ts',
      line: 112,
      code_snippet: '// src/controllers/userController.ts:110-115\nexport async function getProfileAuditLog(req: Request, res: Response) {\n  const { targetUserId } = req.params;\n  // Missing tenant/owner verification check:\n  const logs = await db.auditLog.findMany({ where: { userId: targetUserId } });\n  return res.json(logs);\n}',
      evidence: 'Call-graph analysis revealed targetUserId is unverified against req.auth.userId or tenant boundary before performing query.',
      why_it_matters: 'Enables any authenticated user to view audit history and IP connection records of any other user in the database.',
      suggested_fix: 'if (targetUserId !== req.auth.userId && !req.auth.roles.includes(\'security:admin\')) {\n  return res.status(403).json({ error: "Access denied to target audit logs" });\n}'
    }
  ]
};
