from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.database.models.repository import Repository
from app.database.models.verification import Verification
from app.database.models.finding import Finding
from app.database.models.test_result import TestResult


def test_create_verification_job(client: TestClient):
    mock_repo = {
        "github_id": 100,
        "name": "core-engine",
        "owner": "safeorg",
        "full_name": "safeorg/core-engine",
        "private": False
    }
    mock_pr = {
        "number": 10,
        "title": "Add auth filter",
        "description": "Adds middleware",
        "author": "bob",
        "state": "open",
        "base_sha": "base_sha_123",
        "head_sha": "head_sha_456"
    }

    with patch("app.services.github_service.GitHubService.get_repository", new_callable=AsyncMock) as mock_get_repo, \
         patch("app.services.github_service.GitHubService.get_pull_request", new_callable=AsyncMock) as mock_get_pr, \
         patch("app.services.verification_orchestrator.VerificationOrchestrator.execute_pipeline", new_callable=AsyncMock):

        mock_get_repo.return_value = mock_repo
        mock_get_pr.return_value = mock_pr

        response = client.post(
            "/api/verifications",
            json={"repository": "safeorg/core-engine", "pull_request": 10}
        )
        assert response.status_code == 202
        data = response.json()
        assert "verification_id" in data
        assert data["status"] == "queued"


def test_create_verification_invalid_repo_format(client: TestClient):
    response = client.post(
        "/api/verifications",
        json={"repository": "invalid_format_without_slash", "pull_request": 10}
    )
    assert response.status_code == 400


def test_get_verification_status_and_detail(client: TestClient, db_session: Session):
    # Setup test repository & verification in DB
    repo = Repository(
        owner="safeorg",
        name="test-repo",
        full_name="safeorg/test-repo",
        private=False
    )
    db_session.add(repo)
    db_session.commit()

    verif = Verification(
        repository_id=repo.id,
        pull_request_number=5,
        commit_sha="abcdef123456",
        status="COMPLETED",
        verdict="VERIFIED",
        score=95.0,
        summary="All tests passed successfully."
    )
    db_session.add(verif)
    db_session.commit()

    # Add finding and test result
    finding = Finding(
        verification_id=verif.id,
        type="static_analysis",
        severity="low",
        file="main.py",
        line=12,
        message="Unused variable"
    )
    test_res = TestResult(
        verification_id=verif.id,
        test_name="tests.test_auth.test_login",
        status="passed",
        duration=0.15
    )
    db_session.add(finding)
    db_session.add(test_res)
    db_session.commit()

    # 1. Test status endpoint
    status_res = client.get(f"/api/verifications/{verif.id}/status")
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["status"] in ("COMPLETED", "complete")
    assert st_data["verdict"] == "VERIFIED"
    assert st_data["score"] == 95.0

    # 2. Test detail endpoint
    detail_res = client.get(f"/api/verifications/{verif.id}")
    assert detail_res.status_code == 200
    dt_data = detail_res.json()
    assert dt_data["verdict"] == "VERIFIED"
    assert dt_data["summary"] == "All tests passed successfully."
    assert len(dt_data["findings"]) == 1
    assert dt_data["findings"][0]["file"] == "main.py"
    assert len(dt_data["test_results"]) == 1
    assert dt_data["test_results"][0]["status"] == "passed"


def test_get_verification_not_found(client: TestClient):
    response = client.get("/api/verifications/nonexistent-id/status")
    assert response.status_code == 404
