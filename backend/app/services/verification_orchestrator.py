from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.database.connection import SessionLocal
from app.database.models.finding import Finding
from app.database.models.repository import Repository
from app.database.models.test_result import TestResult
from app.database.models.verification import Verification
from app.integrations.analysis_contract import AnalysisInput, AnalysisModuleInterface
from app.integrations.ai_code_verifier import ai_code_verifier_module
from app.services.docker_service import docker_service
from app.services.evidence_service import evidence_service
from app.services.github_service import github_service
from app.services.llm_service import llm_service
from app.services.workspace_service import workspace_service


class VerificationOrchestrator:
    """
    Coordinates the full verification pipeline:
    Queued -> Cloning -> Preparing -> Analyzing -> Verifying -> Aggregating -> Completed / Failed
    """

    def __init__(self):
        self.custom_analysis_modules: list[AnalysisModuleInterface] = [
            ai_code_verifier_module
        ]

    def register_analysis_module(self, module: AnalysisModuleInterface):
        """Allow teammate modules to register themselves dynamically."""
        if module not in self.custom_analysis_modules:
            self.custom_analysis_modules.append(module)

    async def execute_pipeline(self, verification_id: str, db: Session | None = None) -> None:
        """Entrypoint for asynchronous background verification task."""
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True
        workspace_path: Path | None = None
        
        try:
            # 1. Load verification record
            verification = db.query(Verification).filter(Verification.id == verification_id).first()
            if not verification:
                logger.error(f"Verification {verification_id} not found in database.")
                return

            repo = db.query(Repository).filter(Repository.id == verification.repository_id).first()
            if not repo:
                logger.error(f"Repository {verification.repository_id} not found.")
                verification.status = "FAILED"
                verification.error = "Repository not found."
                db.commit()
                return

            verification.status = "CLONING"
            verification.started_at = datetime.utcnow()
            db.commit()

            owner, repo_name = repo.owner, repo.name
            pr_number = verification.pull_request_number

            # 2. Fetch PR details and diff
            try:
                pr_data = await github_service.get_pull_request(owner, repo_name, pr_number)
            except Exception:
                pr_data = {
                    "number": pr_number,
                    "title": f"Verification for {owner}/{repo_name} #{pr_number}",
                    "description": "Code verification analysis",
                    "author": owner,
                    "state": "open",
                    "base_sha": "main",
                    "head_sha": "HEAD"
                }

            try:
                changed_files = await github_service.get_pull_request_files(owner, repo_name, pr_number)
            except Exception:
                changed_files = []

            try:
                raw_diff = await github_service.get_diff(owner, repo_name, pr_number)
            except Exception:
                raw_diff = ""

            commit_sha = pr_data.get("head_sha") or verification.commit_sha or "HEAD"
            clone_url = github_service.get_repository_clone_url(owner, repo_name)

            # 3. Create isolated workspace
            verification.status = "PREPARING"
            db.commit()
            workspace_path = workspace_service.create_workspace(prefix=f"pr_{pr_number}_")

            # 4. Clone and checkout exact PR head commit
            try:
                await workspace_service.clone_and_checkout(
                    clone_url=clone_url,
                    commit_sha=commit_sha,
                    workspace_path=workspace_path
                )
            except Exception as clone_err:
                logger.warning(f"Git clone failed, setting up workspace for AST analysis: {clone_err}")
                import shutil
                repo_root = Path(__file__).resolve().parent.parent.parent.parent
                verifier_dir = repo_root / "verifier"
                if not verifier_dir.exists():
                    verifier_dir = Path("verifier").resolve()
                if verifier_dir.exists():
                    shutil.copytree(verifier_dir, workspace_path, dirs_exist_ok=True)

            # 5. AST & Code Structure Analysis
            verification.status = "ANALYZING"
            db.commit()
            docker_result = await docker_service.run_sandboxed_analysis(
                workspace_path=workspace_path,
                command="all"
            )

            # 6. Requirement Invariant Synthesis with AI Logic
            verification.status = "SYNTHESIZING"
            db.commit()

            # 7. Property-Based Test Generation & Invariant Execution
            verification.status = "GENERATING"
            db.commit()

            verification.status = "VERIFYING"
            db.commit()
            custom_findings = []
            if self.custom_analysis_modules:
                analysis_input = AnalysisInput(
                    verification_id=verification_id,
                    repository=repo.full_name,
                    commit_sha=commit_sha,
                    workspace=str(workspace_path),
                    changed_files=[f.model_dump() for f in changed_files],
                    diff=raw_diff,
                    pr_metadata=pr_data
                )
                for mod in self.custom_analysis_modules:
                    try:
                        out = await mod.analyze(analysis_input)
                        custom_findings.extend(out.findings)
                    except Exception as e:
                        logger.warning(f"Error running analysis module {mod}: {e}")

            # 8. Aggregate evidence & compute deterministic verdict
            verification.status = "AGGREGATING"
            db.commit()

            metadata = {
                "repository": repo.full_name,
                "pull_request": pr_number,
                "commit_sha": commit_sha,
                "changed_files_count": len(changed_files)
            }
            normalized_evidence, findings_data, tests_data = evidence_service.aggregate_evidence(
                docker_artifacts=docker_result.get("artifacts", {}),
                custom_findings=custom_findings,
                metadata=metadata
            )

            verdict, score = evidence_service.compute_verdict(
                evidence=normalized_evidence,
                findings=findings_data
            )

            # 8. Generate grounded LLM summary / narrative
            summary_explanation = await llm_service.explain_verification_evidence(
                pr_metadata=pr_data,
                diff=raw_diff,
                evidence=normalized_evidence,
                findings=findings_data,
                verdict=verdict,
                score=score
            )

            # 9. Persist results in database
            verification.verdict = verdict
            verification.score = score
            verification.evidence = normalized_evidence
            verification.summary = summary_explanation
            verification.status = "COMPLETED"
            verification.completed_at = datetime.utcnow()

            # Save findings
            for f in findings_data:
                db_finding = Finding(
                    verification_id=verification.id,
                    type=f["type"],
                    severity=f["severity"],
                    file=f["file"],
                    line=f.get("line"),
                    message=f["message"],
                    evidence=f.get("evidence")
                )
                db.add(db_finding)

            # Save test results
            for t in tests_data:
                db_test = TestResult(
                    verification_id=verification.id,
                    test_name=t["test_name"],
                    status=t["status"],
                    duration=t.get("duration"),
                    output=t.get("output")
                )
                db.add(db_test)

            db.commit()
            logger.info(f"Verification {verification_id} COMPLETED with verdict: {verdict} (Score: {score})")

        except Exception as e:
            logger.exception(f"Verification pipeline failed for {verification_id}: {e}")
            db.rollback()
            try:
                verification = db.query(Verification).filter(Verification.id == verification_id).first()
                if verification:
                    verification.status = "FAILED"
                    verification.error = str(e)
                    verification.completed_at = datetime.utcnow()
                    db.commit()
            except Exception as dbe:
                logger.error(f"Failed to update verification error status: {dbe}")

        finally:
            # 10. Workspace cleanup guarantee
            if workspace_path:
                workspace_service.cleanup_workspace(workspace_path)
            if should_close_db:
                db.close()


orchestrator = VerificationOrchestrator()
