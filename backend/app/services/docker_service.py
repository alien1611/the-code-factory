import asyncio
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import logger

try:
    import docker
    from docker.errors import ContainerError, DockerException, ImageNotFound
    DOCKER_LIB_AVAILABLE = True
except ImportError:
    DOCKER_LIB_AVAILABLE = False


class DockerService:
    """Service to execute untrusted code and analysis tools inside a restricted Docker sandbox."""

    def __init__(self):
        self.enabled = settings.DOCKER_ENABLED
        self.image_name = settings.DOCKER_SANDBOX_IMAGE
        self.timeout = settings.DOCKER_TIMEOUT_SECONDS
        self.memory_limit = settings.DOCKER_MEMORY_LIMIT
        self.cpu_limit = settings.DOCKER_CPU_LIMIT
        self._client = None

    def _get_docker_client(self):
        if not DOCKER_LIB_AVAILABLE:
            return None
        if self._client is None:
            try:
                self._client = docker.from_env()
                self._client.ping()
            except Exception as e:
                logger.warning(f"Docker client unavailable: {e}")
                self._client = None
        return self._client

    def is_docker_available(self) -> bool:
        """Check if Docker engine is running and accessible."""
        client = self._get_docker_client()
        return client is not None

    async def run_sandboxed_analysis(
        self,
        workspace_path: Path,
        command: str = "all"
    ) -> dict[str, Any]:
        """
        Execute sandboxed verification tools inside Docker container or isolated fallback.
        Returns dictionary with stdout, stderr, exit_code, and parsed artifact results.
        """
        if self.enabled and self.is_docker_available():
            return await self._run_in_docker(workspace_path, command)
        else:
            logger.info(f"Running in local isolated runner (Docker enabled: {self.enabled}, Docker available: {self.is_docker_available()})")
            return await self._run_local_isolated_tools(workspace_path, command)

    async def _run_in_docker(self, workspace_path: Path, command: str) -> dict[str, Any]:
        """Run inside an isolated Docker container with resource constraints and no network."""
        client = self._get_docker_client()
        container = None
        output = ""
        exit_code = 0
        error_msg = None

        abs_workspace = str(workspace_path.resolve())
        # Volume mount: workspace mapped to /workspace
        volumes = {
            abs_workspace: {"bind": "/workspace", "mode": "rw"}
        }

        try:
            logger.info(f"Starting Docker sandbox container from {self.image_name}...")
            # Run container synchronously in a worker thread to prevent blocking event loop
            def _exec():
                nonlocal container
                container = client.containers.create(
                    image=self.image_name,
                    command=[command],
                    volumes=volumes,
                    network_mode="none",  # No network access for untrusted code
                    mem_limit=self.memory_limit,
                    nano_cpus=int(self.cpu_limit * 1e9),
                    pids_limit=100,
                    user="1000:1000",
                    working_dir="/workspace",
                    detach=True
                )
                container.start()
                res = container.wait(timeout=self.timeout)
                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                return res.get("StatusCode", 0), logs

            exit_code, output = await asyncio.to_thread(_exec)
            logger.info(f"Docker sandbox finished with exit code {exit_code}")

        except Exception as e:
            logger.error(f"Docker sandbox execution error: {e}")
            error_msg = str(e)
            exit_code = 1
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Error removing container: {e}")

        parsed_data = self._read_workspace_artifacts(workspace_path)
        return {
            "exit_code": exit_code,
            "output": output,
            "error": error_msg,
            "artifacts": parsed_data
        }

    async def _run_local_isolated_tools(self, workspace_path: Path, command: str) -> dict[str, Any]:
        """
        Local analysis execution runner for development / non-docker environments.
        Executes ruff, bandit, pytest safely and captures structured evidence.
        """
        results_output = []
        
        # 1. Run Ruff Static Analysis
        ruff_file = workspace_path / ".evidence_ruff.json"
        try:
            proc = await asyncio.create_subprocess_exec(
                "ruff", "check", ".", "--output-format=json",
                cwd=str(workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            ruff_json = stdout.decode(errors="replace")
            if ruff_json.strip():
                ruff_file.write_text(ruff_json, encoding="utf-8")
            results_output.append(f"Ruff: exit {proc.returncode}")
        except Exception as e:
            logger.debug(f"Ruff execution skipped/failed: {e}")

        # 2. Run Bandit Security Scan
        bandit_file = workspace_path / ".evidence_bandit.json"
        try:
            proc = await asyncio.create_subprocess_exec(
                "bandit", "-r", ".", "-f", "json", "-o", str(bandit_file),
                cwd=str(workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=30.0)
            results_output.append(f"Bandit: exit {proc.returncode}")
        except Exception as e:
            logger.debug(f"Bandit execution skipped/failed: {e}")

        # 3. Run Pytest
        pytest_xml_file = workspace_path / ".evidence_pytest.xml"
        try:
            proc = await asyncio.create_subprocess_exec(
                "pytest", "-v", f"--junitxml={pytest_xml_file}",
                cwd=str(workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=45.0)
            results_output.append(f"Pytest: exit {proc.returncode}\n{stdout.decode(errors='replace')}")
        except Exception as e:
            logger.debug(f"Pytest execution skipped/failed: {e}")

        parsed_data = self._read_workspace_artifacts(workspace_path)
        return {
            "exit_code": 0,
            "output": "\n".join(results_output),
            "error": None,
            "artifacts": parsed_data
        }

    def _read_workspace_artifacts(self, workspace_path: Path) -> dict[str, Any]:
        """Read generated evidence files (.evidence_ruff.json, .evidence_bandit.json, .evidence_pytest.xml)."""
        artifacts = {
            "ruff": [],
            "bandit": {},
            "pytest": {"tests": [], "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}}
        }

        # Parse Ruff
        ruff_path = workspace_path / ".evidence_ruff.json"
        if ruff_path.exists():
            try:
                content = ruff_path.read_text(encoding="utf-8")
                artifacts["ruff"] = json.loads(content)
            except Exception as e:
                logger.warning(f"Failed to parse ruff json: {e}")

        # Parse Bandit
        bandit_path = workspace_path / ".evidence_bandit.json"
        if bandit_path.exists():
            try:
                content = bandit_path.read_text(encoding="utf-8")
                artifacts["bandit"] = json.loads(content)
            except Exception as e:
                logger.warning(f"Failed to parse bandit json: {e}")

        # Parse Pytest JUnit XML
        pytest_path = workspace_path / ".evidence_pytest.xml"
        if pytest_path.exists():
            try:
                tree = ET.parse(pytest_path)
                root = tree.getroot()
                # Handle testsuite or testsuites
                suite = root if root.tag == "testsuite" else root.find("testsuite")
                if suite is not None:
                    total = int(suite.attrib.get("tests", 0))
                    failures = int(suite.attrib.get("failures", 0))
                    errors = int(suite.attrib.get("errors", 0))
                    skipped = int(suite.attrib.get("skipped", 0))
                    passed = max(0, total - (failures + errors + skipped))

                    artifacts["pytest"]["summary"] = {
                        "total": total,
                        "passed": passed,
                        "failed": failures,
                        "errors": errors,
                        "skipped": skipped
                    }

                    for case in suite.findall("testcase"):
                        name = f"{case.attrib.get('classname', '')}.{case.attrib.get('name', '')}"
                        time_val = float(case.attrib.get("time", 0.0))
                        status_val = "passed"
                        output_msg = ""

                        fail_elem = case.find("failure")
                        err_elem = case.find("error")
                        skip_elem = case.find("skipped")

                        if fail_elem is not None:
                            status_val = "failed"
                            output_msg = fail_elem.text or fail_elem.attrib.get("message", "")
                        elif err_elem is not None:
                            status_val = "error"
                            output_msg = err_elem.text or err_elem.attrib.get("message", "")
                        elif skip_elem is not None:
                            status_val = "skipped"
                            output_msg = skip_elem.attrib.get("message", "")

                        artifacts["pytest"]["tests"].append({
                            "name": name,
                            "status": status_val,
                            "duration": time_val,
                            "output": output_msg
                        })
            except Exception as e:
                logger.warning(f"Failed to parse pytest xml: {e}")

        return artifacts


docker_service = DockerService()
