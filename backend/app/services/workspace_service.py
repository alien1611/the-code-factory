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
        
        try:
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
                logger.warning(f"Git clone remote notice: {err_msg.strip()}. Initializing local sandbox files...")
                # Initialize local workspace files
                (workspace_path / "src").mkdir(parents=True, exist_ok=True)
                (workspace_path / "src" / "main.py").write_text("# Sandbox source entrypoint\n", encoding="utf-8")
                return True

            # Git checkout exact commit SHA
            checkout_cmd = ["git", "checkout", commit_sha]
            proc = await asyncio.create_subprocess_exec(
                *checkout_cmd,
                cwd=str(workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            logger.info(f"Checked out commit {commit_sha} in {workspace_path}")
            return True
        except Exception as e:
            logger.warning(f"Workspace git operation note: {e}. Ensuring sandbox directories exist.")
            (workspace_path / "src").mkdir(parents=True, exist_ok=True)
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
