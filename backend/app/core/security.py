import hashlib
import hmac
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings


def sanitize_repository_name(name: str) -> str:
    """Validate and sanitize repository identifier formatted as 'owner/repo'."""
    if not name or "/" not in name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid repository format. Expected 'owner/repo'."
        )
    parts = name.strip().split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid repository format. Expected 'owner/repo'."
        )
    # Check for disallowed characters
    disallowed = ["..", "\\", ":", "*", "?", '"', "<", ">", "|", "$", "`"]
    for char in disallowed:
        if char in parts[0] or char in parts[1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Repository name contains invalid characters: '{char}'."
            )
    return f"{parts[0]}/{parts[1]}"


def validate_safe_path(base_dir: str, target_path: str) -> Path:
    """Ensure that target_path is strictly within base_dir to prevent path traversal."""
    resolved_base = Path(base_dir).resolve()
    resolved_target = Path(target_path).resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        raise ValueError(f"Path traversal detected: {target_path} is outside {base_dir}")
    return resolved_target


def verify_github_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """Verify GitHub webhook HMAC SHA256 signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        # If no secret configured, reject or handle securely
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    
    expected_signature = "sha256=" + hmac.new(
        key=settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)


def mask_secret(secret: str | None) -> str:
    """Safely mask tokens and keys for logging purposes."""
    if not secret:
        return "<none>"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"
