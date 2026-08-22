import json

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.core.security import verify_github_signature
from app.database.connection import get_db
from app.schemas.verification import VerificationCreateRequest
from app.services.verification_service import verification_service

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(None),
    x_hub_signature_256: str | None = Header(None),
    db: Session = Depends(get_db)
):
    """
    Handle incoming GitHub webhook events with signature verification.
    Triggers automated verification on pull request creation or code update.
    """
    body_bytes = await request.body()

    # Validate HMAC signature if secret is configured
    if settings.GITHUB_WEBHOOK_SECRET:
        if not verify_github_signature(body_bytes, x_hub_signature_256):
            logger.warning("Rejected GitHub webhook with invalid signature.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub webhook signature."
            )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {e}"
        )

    event_type = x_github_event or "pull_request"
    logger.info(f"Received GitHub webhook event: {event_type}")

    if event_type == "pull_request":
        action = payload.get("action")
        # Trigger verification when PR is opened or new commits pushed (synchronize)
        if action in ["opened", "reopened", "synchronize"]:
            repo_full_name = payload.get("repository", {}).get("full_name")
            pr_number = payload.get("pull_request", {}).get("number")
            
            if repo_full_name and pr_number:
                logger.info(f"Automated webhook verification triggered for {repo_full_name} PR #{pr_number}")
                req = VerificationCreateRequest(repository=repo_full_name, pull_request=pr_number)
                res = await verification_service.create_verification(req, db, background_tasks)
                return {
                    "message": f"Verification queued for PR #{pr_number}",
                    "verification_id": res.verification_id,
                    "action": action
                }

    return {"message": "Event ignored", "event": event_type}
