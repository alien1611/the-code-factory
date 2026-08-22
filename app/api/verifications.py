from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.verification import (
    VerificationCreateRequest,
    VerificationCreateResponse,
    VerificationDetailResponse,
    VerificationStatusResponse,
)
from app.services.verification_service import verification_service

router = APIRouter(prefix="/api/verifications", tags=["Verifications"])


@router.post("", response_model=VerificationCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_verification(
    req: VerificationCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Queue an asynchronous verification job for a given Pull Request.
    Immediately returns verification ID and 'queued' status.
    """
    return await verification_service.create_verification(
        req=req,
        db=db,
        background_tasks=background_tasks
    )


@router.get("/{verification_id}", response_model=VerificationDetailResponse)
def get_verification_detail(verification_id: str, db: Session = Depends(get_db)):
    """
    Retrieve full verification results, including verdict, score, narrative summary, findings, and test results.
    """
    return verification_service.get_verification_detail(verification_id, db)


@router.get("/{verification_id}/status", response_model=VerificationStatusResponse)
def get_verification_status(verification_id: str, db: Session = Depends(get_db)):
    """
    Lightweight status endpoint for frontend polling and progress tracking.
    """
    return verification_service.get_verification_status(verification_id, db)
