import asyncio
import os
import shutil
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger
from app.core.security import validate_safe_path


class WorkspaceService:
    """Manages isolated temporary filesystem workspaces for verification runs."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.WORKSPACE_BASE_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_workspace(self, prefix: str = "verify_") -> Path:
        """Create a new unique temporary workspace directory."""
        unique_id = uuid.uuid4().hex[:12]
        workspace_path = self.base_dir / f"{prefix}{unique_id}"
        workspace_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created temporary workspace at {workspace_path}")
        return workspace_path

    async def clone_and_checkout(
        self,
        clone_url: str,
        commit_sha: str,
        workspace_path: Path
    ) -> bool:
        """
        Clone the repository into workspace and checkout the specific PR commit SHA.
        Runs git safely via subprocess.
        """
        # Validate workspace path security
        validate_safe_path(str(self.base_dir), str(workspace_path))
        
        logger.info(f"Cloning repository into {workspace_path} (commit: {commit_sha[:8]})...")
        
        # Git clone
        clone_cmd = ["git", "clone", "--no-checkout", clone_url, str(workspace_path)]
        proc = await asyncio.create_subprocess_exec(
            *clone_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace")
            # Mask any token in clone_url if present
            masked_err = err_msg.replace(clone_url, "<CLONE_URL>")
            logger.error(f"Git clone failed: {masked_err}")
            raise RuntimeError(f"Git clone failed: {masked_err.strip()}")

        # Git checkout exact commit SHA
        checkout_cmd = ["git", "checkout", commit_sha]
        proc = await asyncio.create_subprocess_exec(
            *checkout_cmd,
            cwd=str(workspace_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace")
            logger.error(f"Git checkout {commit_sha} failed: {err_msg}")
            raise RuntimeError(f"Git checkout failed: {err_msg.strip()}")

        logger.info(f"Checked out commit {commit_sha} in {workspace_path}")
        return True

    def cleanup_workspace(self, workspace_path: Path) -> None:
        """Safely remove the temporary workspace directory."""
        try:
            validate_safe_path(str(self.base_dir), str(workspace_path))
            if workspace_path.exists():
                # On Windows, readonly git files need special permission removal before rmtree
                def on_rm_error(func, path, exc_info):
                    try:
                        os.chmod(path, 0o777)
                        func(path)
                    except Exception as e:
                        logger.warning(f"Failed to clear permission for {path}: {e}")

                shutil.rmtree(workspace_path, onerror=on_rm_error)
                logger.info(f"Cleaned up workspace at {workspace_path}")
        except Exception as e:
            logger.error(f"Error during workspace cleanup for {workspace_path}: {e}")


workspace_service = WorkspaceService()
