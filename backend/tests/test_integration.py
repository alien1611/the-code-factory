import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.models.repository import Repository
from app.database.models.verification import Verification
from app.services.verification_orchestrator import orchestrator


@pytest.mark.asyncio
async def test_full_pipeline_orchestration(client: TestClient, db_session: Session, tmp_path):
    # Setup test repository
    repo = Repository(
        owner="google-deepmind",
        name="ai-code-verifier",
        full_name="google-deepmind/ai-code-verifier",
        private=False
    )
    db_session.add(repo)
    db_session.commit()

    verif = Verification(
        repository_id=repo.id,
        pull_request_number=101,
        commit_sha="c0ffee123456",
        status="QUEUED"
    )
    db_session.add(verif)
    db_session.commit()

    # Mock GitHub Service
    mock_pr = {
        "number": 101,
        "title": "Optimize AST parser and patch token sanitizer",
        "description": "Fixes edge case in AST node traversal.",
        "author": "engineer1",
        "state": "open",
        "base_sha": "base111",
        "head_sha": "c0ffee123456"
    }

    # Mock Docker artifacts
    mock_docker_result = {
        "exit_code": 0,
        "output": "All 12 tests passed successfully.",
        "error": None,
        "artifacts": {
            "pytest": {
                "summary": {"total": 12, "passed": 12, "failed": 0, "errors": 0, "skipped": 0},
                "tests": [{"name": f"test_ast_{i}", "status": "passed", "duration": 0.02, "output": ""} for i in range(12)]
            },
            "ruff": [],
            "bandit": {"results": []}
        }
    }

    with patch("app.services.github_service.GitHubService.get_pull_request", new_callable=AsyncMock) as mock_get_pr, \
         patch("app.services.github_service.GitHubService.get_pull_request_files", new_callable=AsyncMock) as mock_get_files, \
         patch("app.services.github_service.GitHubService.get_diff", new_callable=AsyncMock) as mock_get_diff, \
         patch("app.services.workspace_service.WorkspaceService.clone_and_checkout", new_callable=AsyncMock) as mock_clone, \
         patch("app.services.docker_service.DockerService.run_sandboxed_analysis", new_callable=AsyncMock) as mock_docker:

        mock_get_pr.return_value = mock_pr
        mock_get_files.return_value = []
        mock_get_diff.return_value = "diff --git a/ast.py b/ast.py"
        mock_clone.return_value = True
        mock_docker.return_value = mock_docker_result

        # Execute the verification orchestrator pipeline
        await orchestrator.execute_pipeline(verif.id, db=db_session)

        # Verify database record updated to COMPLETED and valid verdict
        db_session.expire_all()
        updated_verif = db_session.query(Verification).filter(Verification.id == verif.id).first()
        assert updated_verif.status == "COMPLETED"
        assert updated_verif.verdict in ["VERIFIED", "REQUIREMENT_VIOLATION", "VERIFIED_WITH_RISKS"]
        assert updated_verif.score is not None
        assert updated_verif.summary is not None
        assert updated_verif.completed_at is not None

        # Verify via API endpoint
        response = client.get(f"/api/verifications/{verif.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] in ["VERIFIED", "REQUIREMENT_VIOLATION", "VERIFIED_WITH_RISKS"]
        assert len(data["test_results"]) >= 1
