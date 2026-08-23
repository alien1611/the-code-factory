from typing import Any
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.github_service import github_service, GitHubService
from app.services.quota_service import quota_service

router = APIRouter(prefix="/api/quota", tags=["Quota"])


@router.get("", response_model=dict[str, Any])
async def get_user_quota(
    username: str = "alien1611",
    x_github_token: str | None = Header(None, alias="X-GitHub-Token"),
    db: Session = Depends(get_db)
):
    """
    Get the monthly credit limit, usage, and remaining tokens for a GitHub account.
    """
    active_user = username
    if x_github_token and x_github_token.strip():
        try:
            gh = GitHubService(token=x_github_token.strip())
            user_data = await gh.get_authenticated_user()
            if user_data.get("authenticated") and user_data.get("username"):
                active_user = user_data["username"]
        except Exception:
            pass

    return quota_service.get_quota_summary(username=active_user, db=db)
