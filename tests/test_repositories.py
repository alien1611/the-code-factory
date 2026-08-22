from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


def test_list_repositories(client: TestClient):
    mock_data = [
        {
            "github_id": 1,
            "name": "project-a",
            "owner": "testorg",
            "full_name": "testorg/project-a",
            "private": False,
            "html_url": "https://github.com/testorg/project-a",
            "clone_url": "https://github.com/testorg/project-a.git",
            "default_branch": "main",
            "description": "Project A"
        }
    ]

    with patch("app.services.github_service.GitHubService.list_repositories", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_data
        response = client.get("/api/repositories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "project-a"


def test_get_repository_syncs_db(client: TestClient):
    mock_repo = {
        "github_id": 2,
        "name": "project-b",
        "owner": "testorg",
        "full_name": "testorg/project-b",
        "private": False,
        "html_url": "https://github.com/testorg/project-b",
        "clone_url": "https://github.com/testorg/project-b.git",
        "default_branch": "main",
        "description": "Project B"
    }

    with patch("app.services.github_service.GitHubService.get_repository", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_repo
        response = client.get("/api/repositories/testorg/project-b")
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "testorg/project-b"
        assert "id" in data
