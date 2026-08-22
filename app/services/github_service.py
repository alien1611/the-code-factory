from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.schemas.pull_request import ChangedFile


class GitHubService:
    """Service for interacting with GitHub REST API."""

    def __init__(self, token: str | None = None):
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = settings.GITHUB_API_URL.rstrip("/")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Evidence-Driven-Verification-Engine",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _get_headers(self, custom_accept: str | None = None) -> dict[str, str]:
        headers = dict(self.headers)
        if custom_accept:
            headers["Accept"] = custom_accept
        return headers

    async def _handle_response(self, response: httpx.Response) -> Any:
        """Handle GitHub API HTTP errors and response normalization."""
        if response.status_code == 401:
            logger.error("GitHub API returned 401 Unauthorized.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired GitHub authentication token."
            )
        elif response.status_code == 403:
            msg = response.json().get("message", "Access forbidden or rate limit exceeded.")
            logger.warning(f"GitHub API returned 403 Forbidden: {msg}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"GitHub API access forbidden: {msg}"
            )
        elif response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found on GitHub."
            )
        elif response.is_error:
            logger.error(f"GitHub API error {response.status_code}: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"GitHub API error: {response.text}"
            )
        return response

    async def get_authenticated_user(self) -> dict[str, Any]:
        """Fetch the currently authenticated user profile."""
        if not self.token:
            return {"authenticated": False, "username": None, "mode": "public"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(f"{self.base_url}/user", headers=self.headers)
            await self._handle_response(res)
            data = res.json()
            return {
                "authenticated": True,
                "id": data.get("id"),
                "username": data.get("login"),
                "name": data.get("name"),
                "avatar_url": data.get("avatar_url"),
                "mode": "token"
            }

    async def list_repositories(self) -> list[dict[str, Any]]:
        """List repositories accessible to the user or public popular repos."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            if self.token:
                res = await client.get(
                    f"{self.base_url}/user/repos",
                    headers=self.headers,
                    params={"sort": "updated", "per_page": 30}
                )
            else:
                # If unauthenticated, return public repos search or empty
                res = await client.get(
                    f"{self.base_url}/repositories",
                    headers=self.headers,
                    params={"per_page": 30}
                )
            await self._handle_response(res)
            repos = res.json()
            normalized = []
            for r in repos:
                normalized.append({
                    "github_id": r.get("id"),
                    "name": r.get("name"),
                    "owner": r.get("owner", {}).get("login", ""),
                    "full_name": r.get("full_name"),
                    "private": r.get("private", False),
                    "html_url": r.get("html_url"),
                    "clone_url": r.get("clone_url"),
                    "default_branch": r.get("default_branch", "main"),
                    "description": r.get("description"),
                })
            return normalized

    async def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repository metadata."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=self.headers
            )
            await self._handle_response(res)
            r = res.json()
            return {
                "github_id": r.get("id"),
                "name": r.get("name"),
                "owner": r.get("owner", {}).get("login", owner),
                "full_name": r.get("full_name", f"{owner}/{repo}"),
                "private": r.get("private", False),
                "html_url": r.get("html_url"),
                "clone_url": r.get("clone_url"),
                "default_branch": r.get("default_branch", "main"),
                "description": r.get("description"),
            }

    async def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> list[dict[str, Any]]:
        """List pull requests for a repository."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                headers=self.headers,
                params={"state": state, "per_page": 30}
            )
            await self._handle_response(res)
            prs = res.json()
            normalized = []
            for pr in prs:
                normalized.append({
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "description": pr.get("body"),
                    "author": pr.get("user", {}).get("login", "unknown"),
                    "state": pr.get("state"),
                    "base_sha": pr.get("base", {}).get("sha", ""),
                    "head_sha": pr.get("head", {}).get("sha", ""),
                    "created_at": pr.get("created_at"),
                    "updated_at": pr.get("updated_at"),
                    "html_url": pr.get("html_url"),
                })
            return normalized

    async def get_pull_request(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        """Get details for a specific pull request."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{number}",
                headers=self.headers
            )
            await self._handle_response(res)
            pr = res.json()
            return {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "description": pr.get("body"),
                "author": pr.get("user", {}).get("login", "unknown"),
                "state": pr.get("state"),
                "base_sha": pr.get("base", {}).get("sha", ""),
                "head_sha": pr.get("head", {}).get("sha", ""),
                "created_at": pr.get("created_at"),
                "updated_at": pr.get("updated_at"),
                "html_url": pr.get("html_url"),
                "mergeable": pr.get("mergeable"),
            }

    async def get_pull_request_files(self, owner: str, repo: str, number: int) -> list[ChangedFile]:
        """Get changed files and diff patches for a pull request."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{number}/files",
                headers=self.headers,
                params={"per_page": 100}
            )
            await self._handle_response(res)
            files = res.json()
            changed_files: list[ChangedFile] = []
            for f in files:
                changed_files.append(
                    ChangedFile(
                        filename=f.get("filename", ""),
                        status=f.get("status", "modified"),
                        additions=f.get("additions", 0),
                        deletions=f.get("deletions", 0),
                        changes=f.get("changes", 0),
                        patch=f.get("patch"),  # May be None for binary or large files
                        raw_url=f.get("raw_url"),
                        contents_url=f.get("contents_url"),
                    )
                )
            return changed_files

    async def get_diff(self, owner: str, repo: str, number: int) -> str:
        """Get full raw unified diff for a pull request."""
        diff_headers = self._get_headers("application/vnd.github.v3.diff")
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{number}",
                headers=diff_headers
            )
            await self._handle_response(res)
            return res.text

    async def get_commit(self, owner: str, repo: str, sha: str) -> dict[str, Any]:
        """Get commit details."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}",
                headers=self.headers
            )
            await self._handle_response(res)
            c = res.json()
            return {
                "sha": c.get("sha"),
                "message": c.get("commit", {}).get("message"),
                "author": c.get("commit", {}).get("author", {}).get("name"),
                "date": c.get("commit", {}).get("author", {}).get("date"),
            }

    def get_repository_clone_url(self, owner: str, repo: str) -> str:
        """Construct secure git clone URL."""
        if self.token:
            return f"https://x-access-token:{self.token}@github.com/{owner}/{repo}.git"
        return f"https://github.com/{owner}/{repo}.git"


github_service = GitHubService()
