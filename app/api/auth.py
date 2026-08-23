from typing import Any
from pydantic import BaseModel, Field
import httpx
from fastapi import APIRouter, HTTPException, Header, status

from app.core.logging import logger
from app.services.github_service import github_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class ConnectTokenRequest(BaseModel):
    token: str = Field(..., description="GitHub Personal Access Token (classic or fine-grained)")


class UserProfileResponse(BaseModel):
    authenticated: bool
    username: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None
    public_repos: int = 0
    total_private_repos: int = 0


@router.post("/connect", response_model=UserProfileResponse)
async def connect_github_token(req: ConnectTokenRequest):
    """
    Validate a user's GitHub Personal Access Token directly with GitHub API.
    If valid, activates authenticated mode on the backend and returns the real GitHub profile.
    """
    clean_token = req.token.strip()
    if not clean_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token cannot be empty."
        )

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {clean_token}",
        "User-Agent": "Evidence-Driven-Verification-Engine"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get("https://api.github.com/user", headers=headers)
        except Exception as e:
            logger.error(f"Failed to connect to GitHub API: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach GitHub API. Check network connectivity."
            )

        if res.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub Personal Access Token. Please verify token permissions."
            )
        elif res.is_error:
            raise HTTPException(
                status_code=res.status_code,
                detail=f"GitHub validation error: {res.text}"
            )

        data = res.json()
        # Set active token in backend service
        github_service.token = clean_token
        github_service.headers["Authorization"] = f"token {clean_token}"

        logger.info(f"Successfully authenticated GitHub user: {data.get('login')}")

        return UserProfileResponse(
            authenticated=True,
            username=data.get("login"),
            name=data.get("name") or data.get("login"),
            avatar_url=data.get("avatar_url"),
            html_url=data.get("html_url"),
            public_repos=data.get("public_repos", 0),
            total_private_repos=data.get("total_private_repos", 0)
        )


@router.get("/user", response_model=UserProfileResponse)
async def get_current_user():
    """
    Get currently authenticated GitHub user profile.
    """
    if not github_service.token:
        return UserProfileResponse(authenticated=False)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get("https://api.github.com/user", headers=github_service.headers)
            if res.status_code == 200:
                data = res.json()
                return UserProfileResponse(
                    authenticated=True,
                    username=data.get("login"),
                    name=data.get("name") or data.get("login"),
                    avatar_url=data.get("avatar_url"),
                    html_url=data.get("html_url"),
                    public_repos=data.get("public_repos", 0),
                    total_private_repos=data.get("total_private_repos", 0)
                )
        except Exception as e:
            logger.warning(f"Error fetching authenticated user: {e}")

    return UserProfileResponse(authenticated=False)


@router.post("/disconnect")
def disconnect_github():
    """
    Clear the currently configured GitHub token and switch to unauthenticated public mode.
    """
    github_service.token = None
    if "Authorization" in github_service.headers:
        del github_service.headers["Authorization"]
    return {"authenticated": False, "message": "Disconnected from GitHub"}
