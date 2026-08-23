import pytest
from pathlib import Path
from app.services.docker_service import DockerService
from app.services.evidence_service import EvidenceService


def test_artifact_parsing_pytest_xml(tmp_path: Path):
    docker_srv = DockerService()
    
    # Create sample pytest xml
    pytest_xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" errors="0" failures="1" skipped="0" tests="3" time="0.5">
    <testcase classname="tests.test_app" name="test_one" time="0.1" />
    <testcase classname="tests.test_app" name="test_two" time="0.2">
        <failure message="AssertionError: 1 != 2">Traceback here...</failure>
    </testcase>
    <testcase classname="tests.test_app" name="test_three" time="0.1" />
</testsuite>
"""
    xml_file = tmp_path / ".evidence_pytest.xml"
    xml_file.write_text(pytest_xml_content, encoding="utf-8")

    artifacts = docker_srv._read_workspace_artifacts(tmp_path)
    assert artifacts["pytest"]["summary"]["total"] == 3
    assert artifacts["pytest"]["summary"]["passed"] == 2
    assert artifacts["pytest"]["summary"]["failed"] == 1
    assert len(artifacts["pytest"]["tests"]) == 3
    assert artifacts["pytest"]["tests"][1]["status"] == "failed"


def test_evidence_service_verdict_rejection_on_failure():
    ev_service = EvidenceService()
    mock_artifacts = {
        "pytest": {
            "summary": {"total": 5, "passed": 4, "failed": 1, "errors": 0, "skipped": 0},
            "tests": [{"name": "test_feature", "status": "failed", "duration": 0.2, "output": "Failed assertion"}]
        },
        "ruff": [],
        "bandit": {"results": []}
    }

    normalized, findings, tests = ev_service.aggregate_evidence(
        docker_artifacts=mock_artifacts,
        custom_findings=[],
        metadata={"repository": "test/repo"}
    )

    verdict, score = ev_service.compute_verdict(normalized, findings)
    assert verdict == "REJECTED"
    assert normalized["regression"]["detected"] is True


def test_evidence_service_verdict_verified_on_clean_pass():
    ev_service = EvidenceService()
    mock_artifacts = {
        "pytest": {
            "summary": {"total": 10, "passed": 10, "failed": 0, "errors": 0, "skipped": 0},
            "tests": [{"name": f"test_{i}", "status": "passed", "duration": 0.05, "output": ""} for i in range(10)]
        },
        "ruff": [],
        "bandit": {"results": []}
    }

    normalized, findings, tests = ev_service.aggregate_evidence(
        docker_artifacts=mock_artifacts,
        custom_findings=[],
        metadata={"repository": "test/repo"}
    )

    verdict, score = ev_service.compute_verdict(normalized, findings)
    assert verdict == "VERIFIED"
    assert score == 100.0
