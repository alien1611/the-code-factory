from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChangedFile(BaseModel):
    filename: str
    status: str
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str | None = None
    raw_url: str | None = None
    contents_url: str | None = None


class PullRequestBase(BaseModel):
    number: int
    title: str
    description: str | None = None
    author: str
    state: str = "open"
    base_sha: str
    head_sha: str


class PullRequestResponse(PullRequestBase):
    id: str
    repository_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PullRequestDetailResponse(PullRequestBase):
    repository: str
    pull_request: int
    files: list[ChangedFile] = []
    diff: str | None = None


class PullRequestListResponse(BaseModel):
    repository: str
    pull_requests: list[PullRequestResponse]
