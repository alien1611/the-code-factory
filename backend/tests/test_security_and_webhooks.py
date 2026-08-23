import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from app.core.security import validate_safe_path, sanitize_repository_name, verify_github_signature
from app.core.config import settings


def test_sanitize_repository_name_valid():
    assert sanitize_repository_name("owner/repo") == "owner/repo"
    assert sanitize_repository_name("  google-deepmind/evidence-engine  ") == "google-deepmind/evidence-engine"


def test_sanitize_repository_name_path_traversal():
    with pytest.raises(Exception):
        sanitize_repository_name("../malicious/repo")
    with pytest.raises(Exception):
        sanitize_repository_name("owner/../../evil")
    with pytest.raises(Exception):
        sanitize_repository_name("just-repo-name")


def test_validate_safe_path(tmp_path):
    safe_sub = tmp_path / "subdir"
    safe_sub.mkdir()
    assert validate_safe_path(str(tmp_path), str(safe_sub)) == safe_sub.resolve()

    evil_path = tmp_path.parent / "escape"
    with pytest.raises(ValueError):
        validate_safe_path(str(tmp_path), str(evil_path))


def test_webhook_signature_verification(client: TestClient, monkeypatch):
    secret = "super_secret_webhook_key_123"
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", secret)

    payload = {
        "action": "opened",
        "repository": {"full_name": "google/sample-repo"},
        "pull_request": {"number": 88}
    }
    raw_payload = json.dumps(payload).encode("utf-8")

    # Generate valid signature
    valid_sig = "sha256=" + hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    assert verify_github_signature(raw_payload, valid_sig) is True
    assert verify_github_signature(raw_payload, "sha256=invalid_signature") is False

    # Test webhook endpoint with invalid signature
    res = client.post(
        "/api/webhooks/github",
        content=raw_payload,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid_sig",
            "Content-Type": "application/json"
        }
    )
    assert res.status_code == 401
