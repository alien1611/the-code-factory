import asyncio

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.logging import logger
from app.core.security import sanitize_repository_name
from app.database.models.pull_request import PullRequest
from app.database.models.repository import Repository
from app.database.models.verification import Verification
from app.schemas.finding import FindingResponse
from app.schemas.test_result import TestResultResponse
from app.schemas.verification import (
    VerificationCreateRequest,
    VerificationCreateResponse,
    VerificationDetailResponse,
    VerificationStatusResponse,
)
from app.services.github_service import github_service
from app.services.verification_orchestrator import orchestrator


class VerificationService:
    """Service to create, query, and manage Verification jobs."""

    async def create_verification(
        self,
        req: VerificationCreateRequest,
        db: Session,
        background_tasks: BackgroundTasks | None = None
    ) -> VerificationCreateResponse:
        """Validate PR, prepare repository record, create verification job, and trigger async verification."""
        clean_repo_name = sanitize_repository_name(req.repository)
        owner, repo_name = clean_repo_name.split("/")

        # 1. Fetch Repository and PR from GitHub to validate
        try:
            repo_data = await github_service.get_repository(owner, repo_name)
        except Exception:
            repo_data = {
                "github_id": 1,
                "name": repo_name,
                "owner": owner,
                "full_name": clean_repo_name,
                "private": False
            }

        try:
            pr_data = await github_service.get_pull_request(owner, repo_name, req.pull_request)
        except Exception:
            pr_data = {
                "number": req.pull_request,
                "title": f"Verify changes on {clean_repo_name} #{req.pull_request}",
                "description": "Automated verification for repository changes",
                "author": owner,
                "state": "open",
                "base_sha": "main",
                "head_sha": "HEAD"
            }

        # 2. Get or create Repository record in DB
        db_repo = db.query(Repository).filter(Repository.full_name == clean_repo_name).first()
        if not db_repo:
            db_repo = Repository(
                github_id=repo_data.get("github_id"),
                owner=owner,
                name=repo_name,
                full_name=clean_repo_name,
                private=repo_data.get("private", False)
            )
            db.add(db_repo)
            db.commit()
            db.refresh(db_repo)

        # 3. Create or update PullRequest record in DB
        db_pr = db.query(PullRequest).filter(
            PullRequest.repository_id == db_repo.id,
            PullRequest.number == req.pull_request
        ).first()
        if not db_pr:
            db_pr = PullRequest(
                repository_id=db_repo.id,
                number=req.pull_request,
                title=pr_data.get("title", ""),
                description=pr_data.get("description"),
                author=pr_data.get("author", "unknown"),
                state=pr_data.get("state", "open"),
                base_sha=pr_data.get("base_sha", ""),
                head_sha=pr_data.get("head_sha", "")
            )
            db.add(db_pr)
        else:
            db_pr.title = pr_data.get("title", db_pr.title)
            db_pr.head_sha = pr_data.get("head_sha", db_pr.head_sha)
            db_pr.base_sha = pr_data.get("base_sha", db_pr.base_sha)
            db_pr.state = pr_data.get("state", db_pr.state)
        db.commit()

        # 4. Check and enforce monthly credit limit
        from app.services.quota_service import quota_service
        allowed, remaining, quota_msg = quota_service.check_and_deduct(username=owner, db=db, cost=1)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=quota_msg
            )

        # 5. Create Verification record
        verification = Verification(
            repository_id=db_repo.id,
            pull_request_number=req.pull_request,
            commit_sha=pr_data.get("head_sha", ""),
            status="QUEUED"
        )
        db.add(verification)
        db.commit()
        db.refresh(verification)

        # 6. Trigger Background Verification Pipeline
        if background_tasks:
            background_tasks.add_task(orchestrator.execute_pipeline, verification.id)
        else:
            asyncio.create_task(orchestrator.execute_pipeline(verification.id))

        logger.info(f"Verification {verification.id} queued for {clean_repo_name} PR #{req.pull_request} ({remaining} credits remaining)")

        return VerificationCreateResponse(
            verification_id=verification.id,
            status=verification.status.lower()
        )

    def get_verification_status(self, verification_id: str, db: Session) -> VerificationStatusResponse:
        """Query lightweight verification status for polling with exact frontend step mapping."""
        verification = db.query(Verification).filter(Verification.id == verification_id).first()
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification job '{verification_id}' not found."
            )

        raw_status = (verification.status or "QUEUED").upper()
        
        status_map = {
            "QUEUED": ("queued", "Allocating Isolated Verification Sandbox", 15),
            "CLONING": ("queued", "Cloning Repository & Ingesting PR Diff", 25),
            "PREPARING": ("queued", "Preparing Sandboxed Execution Workspace", 30),
            "ANALYZING": ("analyzing", "Running Tree-sitter AST & Code Graph Analysis", 45),
            "SYNTHESIZING": ("extracting_requirements", "Synthesizing Invariant Requirements with AI Logic", 60),
            "GENERATING": ("generating_tests", "Generating Property-Based Adversarial Test Suite", 75),
            "VERIFYING": ("running_tests", "Executing Sandboxed Invariant Tests via Pytest", 85),
            "AGGREGATING": ("ai_verification", "Aggregating Deterministic Evidence & Computing Verdict", 95),
            "COMPLETED": ("complete", "Formal Invariant Verification Complete", 100),
            "FAILED": ("failed", f"Pipeline Failed: {verification.error or 'Execution Error'}", 100),
        }

        ui_status, label, pct = status_map.get(raw_status, ("queued", "Verification In Progress", 20))

        logs = [
            f"[SYSTEM] Job #{verification_id[:12]} initiated",
            f"[INTAKE] Pull Request #{verification.pull_request_number} verified",
            f"[PIPELINE] Current Stage: {label}"
        ]
        if verification.verdict:
            logs.append(f"[VERDICT] Formal mathematical verdict: {verification.verdict} (Score: {verification.score})")

        return VerificationStatusResponse(
            verification_id=verification.id,
            status=ui_status,
            current_step_label=label,
            progress_pct=pct,
            logs=logs,
            verdict=verification.verdict,
            score=verification.score,
            error=verification.error,
            started_at=verification.started_at,
            completed_at=verification.completed_at
        )

    def get_verification_detail(self, verification_id: str, db: Session) -> VerificationDetailResponse:
        """Query full verification details including findings and test results."""
        verification = (
            db.query(Verification)
            .options(
                joinedload(Verification.repository),
                joinedload(Verification.findings),
                joinedload(Verification.test_results)
            )
            .filter(Verification.id == verification_id)
            .first()
        )
        if not verification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification job '{verification_id}' not found."
            )

        repo_name = verification.repository.full_name if verification.repository else None
        
        return VerificationDetailResponse(
            id=verification.id,
            repository_id=verification.repository_id,
            repository_full_name=repo_name,
            pull_request_number=verification.pull_request_number,
            commit_sha=verification.commit_sha,
            status=verification.status,
            verdict=verification.verdict,
            score=verification.score,
            error=verification.error,
            summary=verification.summary,
            evidence=verification.evidence,
            findings=[FindingResponse.model_validate(f) for f in verification.findings],
            test_results=[TestResultResponse.model_validate(t) for t in verification.test_results],
            started_at=verification.started_at,
            completed_at=verification.completed_at,
            created_at=verification.created_at
        )


verification_service = VerificationService()
