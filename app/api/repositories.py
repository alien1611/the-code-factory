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
