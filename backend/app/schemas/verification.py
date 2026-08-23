from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.finding import FindingResponse
from app.schemas.test_result import TestResultResponse


class VerificationCreateRequest(BaseModel):
    repository: str  # e.g. "owner/repo"
    pull_request: int


class VerificationCreateResponse(BaseModel):
    verification_id: str
    status: str = "queued"


class VerificationStatusResponse(BaseModel):
    verification_id: str
    status: str
    current_step_label: str = "Allocating Isolated Verification Sandbox"
    progress_pct: int = 15
    logs: list[str] = []
    verdict: str | None = None
    score: float | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class VerificationDetailResponse(BaseModel):
    id: str
    repository_id: str
    repository_full_name: str | None = None
    pull_request_number: int
    commit_sha: str
    status: str
    verdict: str | None = None
    score: float | None = None
    error: str | None = None
    summary: str | None = None
    evidence: dict[str, Any] | None = None
    findings: list[FindingResponse] = []
    test_results: list[TestResultResponse] = []
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
