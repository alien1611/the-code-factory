from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.schemas.pull_request import ChangedFile


def test_get_pull_request_details(client: TestClient):
    mock_pr = {
        "number": 42,
        "title": "Fix memory leak in parser",
        "description": "Resolves issue with unclosed streams",
        "author": "dev-alice",
        "state": "open",
        "base_sha": "base123456",
        "head_sha": "headabcdef"
    }

    mock_files = [
        ChangedFile(
            filename="parser.py",
            status="modified",
            additions=5,
            deletions=2,
            changes=7,
            patch="@@ -10,2 +10,5 @@\n+with open() as f:"
        )
    ]

    mock_diff = "diff --git a/parser.py b/parser.py\n@@ -10,2 +10,5 @@"

    with patch("app.services.github_service.GitHubService.get_pull_request", new_callable=AsyncMock) as mock_get_pr, \
         patch("app.services.github_service.GitHubService.get_pull_request_files", new_callable=AsyncMock) as mock_get_files, \
         patch("app.services.github_service.GitHubService.get_diff", new_callable=AsyncMock) as mock_get_diff:

        mock_get_pr.return_value = mock_pr
        mock_get_files.return_value = mock_files
        mock_get_diff.return_value = mock_diff

        response = client.get("/api/pull-requests/testorg/project-a/42")
        assert response.status_code == 200
        data = response.json()
        assert data["repository"] == "testorg/project-a"
        assert data["pull_request"] == 42
        assert data["author"] == "dev-alice"
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "parser.py"
        assert data["diff"] is not None
