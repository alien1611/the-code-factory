# Evidence-Driven Verification Engine - API Contract

This document outlines the API contract for the frontend team. It answers all requirements regarding endpoints, request/response formats, progress tracking, and error handling.

---

## 1. API Endpoints
The frontend will communicate with the following REST endpoints:

* **Get Repositories:** `GET /api/repositories`
* **Get PRs/Commits/Diffs:** `GET /api/pull_requests/{owner}/{repo}/{pr_number}`
* **Start Verification:** `POST /api/verifications`
* **Get Verification Status (Progress):** `GET /api/verifications/{verification_id}/status`
* **Get Final Result:** `GET /api/verifications/{verification_id}`

---

## 2. Request Format
To trigger a new verification, the frontend ONLY needs to send the repository and PR number. 
*(Note: The backend automatically fetches the commit SHA, diff, and files directly from GitHub during the `CLONING` phase, so the frontend doesn't need to provide them).*

**Endpoint:** `POST /api/verifications`
**Payload:**
```json
{
  "repository": "owner/repo",
  "pull_request": 123
}
```

---

## 3. Progress Updates
While the verification runs in the background, the frontend should use **Polling** to ping the status endpoint every few seconds.

**Endpoint:** `GET /api/verifications/{verification_id}/status`

**Response format (Just stages, no percentages):**
```json
{
  "verification_id": "uuid-123",
  "status": "ANALYZING",
  "verdict": null,
  "error": null
}
```

### Exact Status Stages Returned:
1. `QUEUED`
2. `CLONING`
3. `PREPARING`
4. `ANALYZING`
5. `VERIFYING`
6. `AGGREGATING`
7. `COMPLETED` (or `FAILED`)

---

## 4. Verification Response (Final Result)
Once the status reaches `COMPLETED`, the frontend should fetch the full result.

**Endpoint:** `GET /api/verifications/{verification_id}`

**Exact JSON Response:**
```json
{
  "id": "uuid-1234",
  "repository_full_name": "owner/repo",
  "pull_request_number": 123,
  "commit_sha": "abc123def456",
  "status": "COMPLETED",
  "verdict": "VERIFIED_WITH_RISKS",
  "score": 85.5,
  "summary": "AI generated explanation of the evidence goes here...",
  "evidence": {
    "security": {"critical": 0, "high": 1, "medium": 0, "low": 0},
    "static_analysis": {"errors": 0, "warnings": 2}
  },
  "test_results": [
    {
      "name": "test_auth_bypass",
      "status": "passed",
      "duration": 1.2,
      "output": ""
    }
  ],
  "findings": [
    {
      "file": "app/auth.py",
      "line": 42,
      "severity": "high",
      "type": "bandit_scan",
      "message": "Potential hardcoded password detected."
    }
  ],
  "started_at": "2026-08-22T10:00:00Z",
  "completed_at": "2026-08-22T10:01:15Z"
}
```

*(Note: AI verification results, static analysis, and security scans are aggregated inside the `evidence` object and mapped to specific `findings` and `test_results` arrays).*

---

## 5. Error Handling
If anything fails (GitHub timeout, invalid PR, analysis crash):
1. During the background run, the background pipeline catches the error and the status safely updates to `"FAILED"`.
2. The `/status` and detail API responses will include an `"error"` field detailing exactly what failed.

**Example Failure Response:**
```json
{
  "verification_id": "uuid-123",
  "status": "FAILED",
  "error": "Failed to clone repository: GitHub API connection timeout."
}
```
If the initial `POST` request is malformed (e.g., missing repo name), standard FastAPI `422 Unprocessable Entity` or `404 Not Found` JSON is returned immediately.
