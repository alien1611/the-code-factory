import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from app.services.github_service import GitHubService
from app.schemas.pull_request import ChangedFile


@pytest.mark.asyncio
async def test_get_authenticated_user_unauthenticated():
    service = GitHubService(token=None)
    user = await service.get_authenticated_user()
    assert user["authenticated"] is False
    assert user["mode"] == "public"


@pytest.mark.asyncio
async def test_get_authenticated_user_with_token():
    service = GitHubService(token="dummy_token")
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.is_error = False
    mock_res.json.return_value = {
        "id": 12345,
        "login": "testuser",
        "name": "Test User",
        "avatar_url": "https://avatar.com/user"
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_res
        user = await service.get_authenticated_user()
        assert user["authenticated"] is True
        assert user["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_repository():
    service = GitHubService(token="dummy_token")
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.is_error = False
    mock_res.json.return_value = {
        "id": 999,
        "name": "sample-repo",
        "owner": {"login": "octocat"},
        "full_name": "octocat/sample-repo",
        "private": False,
        "clone_url": "https://github.com/octocat/sample-repo.git",
        "default_branch": "main",
        "description": "Sample repo"
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_res
        repo = await service.get_repository("octocat", "sample-repo")
        assert repo["name"] == "sample-repo"
        assert repo["full_name"] == "octocat/sample-repo"


@pytest.mark.asyncio
async def test_get_pull_request_files():
    service = GitHubService(token="dummy_token")
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.is_error = False
    mock_res.json.return_value = [
        {
            "filename": "auth.py",
            "status": "modified",
            "additions": 10,
            "deletions": 2,
            "changes": 12,
            "patch": "@@ -1,3 +1,11 @@\n+new line"
        },
        {
            "filename": "binary.png",
            "status": "added",
            "additions": 0,
            "deletions": 0,
            "changes": 0,
            "patch": None
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_res
        files = await service.get_pull_request_files("octocat", "sample-repo", 1)
        assert len(files) == 2
        assert isinstance(files[0], ChangedFile)
        assert files[0].filename == "auth.py"
        assert files[0].patch is not None
        assert files[1].patch is None


@pytest.mark.asyncio
async def test_github_api_404_handling():
    service = GitHubService(token="dummy_token")
    mock_res = MagicMock()
    mock_res.status_code = 404
    mock_res.is_error = True

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_res
        with pytest.raises(HTTPException) as exc_info:
            await service.get_repository("octocat", "nonexistent")
        assert exc_info.value.status_code == 404
