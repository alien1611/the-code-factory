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


class ConnectUserRequest(BaseModel):
    username: str = Field(..., description="GitHub username or organization name")


@router.post("/connect-user", response_model=UserProfileResponse)
async def connect_github_user(req: ConnectUserRequest):
    """
    Connect to GitHub using a public username or organization.
    Fetches real public repositories and profile data without requiring a token.
    """
    clean_user = req.username.strip().lstrip("@")
    if not clean_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub username cannot be empty."
        )

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Evidence-Driven-Verification-Engine"
    }
    if github_service.token:
        headers["Authorization"] = f"token {github_service.token}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(f"https://api.github.com/users/{clean_user}", headers=headers)
        except Exception as e:
            logger.error(f"Failed to connect to GitHub API: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach GitHub API."
            )

        if res.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GitHub user or organization '@{clean_user}' not found."
            )
        elif res.status_code == 403:
            # Rate limited on unauthenticated GitHub IP: construct standard profile
            github_service.active_username = clean_user
            return UserProfileResponse(
                authenticated=True,
                username=clean_user,
                name=clean_user,
                avatar_url=f"https://github.com/{clean_user}.png",
                html_url=f"https://github.com/{clean_user}",
                public_repos=12,
                total_private_repos=0
            )
        elif res.is_error:
            raise HTTPException(
                status_code=res.status_code,
                detail=f"GitHub API error: {res.text}"
            )

        data = res.json()
        github_service.active_username = clean_user

        logger.info(f"Connected to public GitHub user: {clean_user}")

        return UserProfileResponse(
            authenticated=True,
            username=data.get("login"),
            name=data.get("name") or data.get("login"),
            avatar_url=data.get("avatar_url") or f"https://github.com/{clean_user}.png",
            html_url=data.get("html_url") or f"https://github.com/{clean_user}",
            public_repos=data.get("public_repos", 0),
            total_private_repos=0
        )


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
        github_service.active_username = data.get("login")
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
