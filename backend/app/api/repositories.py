from typing import Any

from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models.repository import Repository
from app.services.github_service import github_service, GitHubService

router = APIRouter(prefix="/api/repositories", tags=["Repositories"])


def get_service(x_github_token: str | None = Header(None, alias="X-GitHub-Token")) -> GitHubService:
    if x_github_token and x_github_token.strip():
        return GitHubService(token=x_github_token.strip())
    return github_service


@router.get("", response_model=list[dict[str, Any]])
async def list_repositories(service: GitHubService = Depends(get_service)):
    """
    List repositories accessible via GitHub authentication.
    Returns normalized repository metadata.
    """
    return await service.list_repositories()


@router.get("/{owner}/{repo}", response_model=dict[str, Any])
async def get_repository(
    owner: str, 
    repo: str, 
    db: Session = Depends(get_db),
    service: GitHubService = Depends(get_service)
):
    """
    Get detailed repository information.
    Syncs repository record into local database if not already tracked.
    """
    repo_data = await service.get_repository(owner, repo)
    full_name = f"{owner}/{repo}"
    
    # Track/sync in local database
    db_repo = db.query(Repository).filter(Repository.full_name == full_name).first()
    if not db_repo:
        db_repo = Repository(
            github_id=repo_data.get("github_id"),
            owner=owner,
            name=repo,
            full_name=full_name,
            private=repo_data.get("private", False)
        )
        db.add(db_repo)
        db.commit()
        db.refresh(db_repo)

    repo_data["id"] = db_repo.id
    return repo_data


from pydantic import BaseModel, Field


class CreatePullRequestInput(BaseModel):
    title: str = Field(..., description="Pull Request title")
    head: str = Field(..., description="Source branch name containing changes")
    base: str = Field(default="main", description="Target branch into which changes will be merged")
    body: str | None = Field(default=None, description="PR description / markdown body")


@router.get("/{owner}/{repo}/branches", response_model=list[dict[str, Any]])
async def list_repository_branches(
    owner: str,
    repo: str,
    service: GitHubService = Depends(get_service)
):
    """
    List all branches for a given repository.
    """
    return await service.list_branches(owner, repo)


@router.get("/{owner}/{repo}/pull-requests", response_model=list[dict[str, Any]])
async def list_repository_pull_requests(
    owner: str,
    repo: str,
    state: str = Query("all", description="PR state: open, closed, or all"),
    service: GitHubService = Depends(get_service)
):
    """
    List all pull requests for a given repository.
    """
    return await service.list_pull_requests(owner, repo, state=state)


@router.post("/{owner}/{repo}/pull-requests", response_model=dict[str, Any])
async def create_repository_pull_request(
    owner: str,
    repo: str,
    req: CreatePullRequestInput,
    service: GitHubService = Depends(get_service)
):
    """
    Create a new Pull Request directly on GitHub.
    """
    return await service.create_pull_request(
        owner=owner,
        repo=repo,
        title=req.title,
        head=req.head,
        base=req.base,
        body=req.body
    )
