"""
pipeline.py - Unified Verification Pipeline & Loose Coupling Facade

Implements Strategy and Facade patterns to decouple individual verification tools
(Ruff, Semgrep, Dependency Checker, RFID Verifier) from consumer modules.

Enables high cohesion (each engine has a single responsibility) and low coupling
(consumers interact exclusively through the VerificationEngine interface and Pipeline facade).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Optional
import unittest

from models import AnalysisResult, FileMetadata, Finding, FindingCategory, FindingSeverity
from parser import analyze_repository
from static_analysis import run_ruff
from semgrep_analyzer import run_semgrep
from dependency_checker import check_dependencies, run_pip_audit
from rfid_verifier import verify_rfid_authentication, verify_rfid_repository


# ==============================================================================
# 1. VERIFICATION ENGINE INTERFACE (STRATEGY PATTERN)
# ==============================================================================

class VerificationEngine(ABC):
    """
    Abstract interface for all static analysis, security, dependency,
    and domain-specific verification engines.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns unique identifier for this verification engine."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Returns human-readable name for UI/Dashboard reporting."""
        pass

    @abstractmethod
    def is_applicable(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bool:
        """Determines whether this engine can analyze the given target."""
        pass

    @abstractmethod
    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        """Executes verification and returns normalized Finding objects."""
        pass


# ==============================================================================
# 2. CONCRETE ENGINE IMPLEMENTATIONS
# ==============================================================================

class RuffVerificationEngine(VerificationEngine):
    """Linter and syntax verification engine for Python code using Ruff."""

    @property
    def name(self) -> str:
        return "ruff"

    @property
    def display_name(self) -> str:
        return "Ruff Linter"

    def is_applicable(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bool:
        p = Path(target_path)
        if language and language.lower() in ("python", "py"):
            return True
        return p.suffix.lower() == ".py" or p.is_dir()

    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        p = Path(target_path)
        if p.exists():
            return run_ruff(str(p))

        if source_code:
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tmp:
                tmp.write(source_code)
                tmp_path = Path(tmp.name)
            try:
                findings = run_ruff(str(tmp_path))
                for f in findings:
                    f.file = str(target_path)
                return findings
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

        return []


class SemgrepVerificationEngine(VerificationEngine):
    """Semantic AST pattern and rule matching engine using Semgrep."""

    def __init__(self, default_config: Optional[str] = None) -> None:
        self.default_config = default_config

    @property
    def name(self) -> str:
        return "semgrep"

    @property
    def display_name(self) -> str:
        return "Semgrep AST Rules"

    def is_applicable(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bool:
        return True

    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        p = Path(target_path)
        if p.exists():
            return run_semgrep(str(p), config=self.default_config)
        return []


class DependencyVerificationEngine(VerificationEngine):
    """Third-party manifest CVE auditor (pip-audit & npm audit)."""

    @property
    def name(self) -> str:
        return "dependency_scanner"

    @property
    def display_name(self) -> str:
        return "Dependency Vulnerability Scanner"

    def is_applicable(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bool:
        p = Path(target_path)
        manifest_names = {"requirements.txt", "pyproject.toml", "package.json", "package-lock.json"}
        if p.name.lower() in manifest_names:
            return True
        if p.is_dir():
            return True
        if source_code and ("==" in source_code or "\"dependencies\"" in source_code):
            return True
        return False

    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        p = Path(target_path)
        if p.is_file() and p.name.lower() == "requirements.txt":
            return run_pip_audit(p)
        elif p.is_dir():
            return check_dependencies(str(p))

        if source_code and (language or "").lower() in ("python", "requirements"):
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tmp:
                tmp.write(source_code)
                tmp_path = Path(tmp.name)
            try:
                findings = run_pip_audit(tmp_path)
                for f in findings:
                    f.file = str(target_path)
                return findings
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

        return []


class RfidDomainVerificationEngine(VerificationEngine):
    """Domain-specific static verification engine for RFID authentication invariants."""

    @property
    def name(self) -> str:
        return "rfid_domain_rule"

    @property
    def display_name(self) -> str:
        return "Domain Rules (RFID / IoT)"

    def is_applicable(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bool:
        p = Path(target_path)
        c_exts = {".ino", ".cpp", ".c", ".h", ".hpp", ".cc"}
        if p.suffix.lower() in c_exts:
            return True
        if (language or "").lower() in ("cpp", "c", "arduino"):
            return True
        if source_code and ("MFRC522" in source_code or "PICC_" in source_code or "RFID" in source_code):
            return True
        return False

    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        if source_code:
            meta = metadata or FileMetadata(path=str(target_path), language="C++")
            return verify_rfid_authentication(source_code, meta)

        p = Path(target_path)
        if p.is_file():
            try:
                code = p.read_text(encoding="utf-8", errors="replace")
                meta = metadata or FileMetadata(path=str(p), language="C++")
                return verify_rfid_authentication(code, meta)
            except Exception:
                return []
        elif p.is_dir():
            return verify_rfid_repository(p)

        return []


class EslintVerificationEngine(VerificationEngine):
    """Linter and security verification engine for JavaScript/TypeScript using ESLint."""

    @property
    def name(self) -> str:
        return "eslint"

    @property
    def display_name(self) -> str:
        return "ESLint Linter"

    def is_applicable(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bool:
        p = Path(target_path)
        js_exts = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
        if language and language.lower() in ("javascript", "js", "typescript", "ts"):
            return True
        return p.suffix.lower() in js_exts or p.is_dir()

    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        try:
            from javascript_analyzer import run_eslint
            return run_eslint(target_path)
        except Exception:
            return []


class CppClangTidyVerificationEngine(VerificationEngine):
    """Static analysis and security engine for C++ and Arduino code using clang-tidy."""

    @property
    def name(self) -> str:
        return "clang-tidy"

    @property
    def display_name(self) -> str:
        return "Clang-Tidy (C++/Arduino)"

    def is_applicable(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bool:
        p = Path(target_path)
        cpp_exts = {".cpp", ".cxx", ".cc", ".c", ".hpp", ".h", ".hh", ".hxx", ".ino"}
        if language and language.lower() in ("c++", "cpp", "c", "arduino"):
            return True
        return p.suffix.lower() in cpp_exts or p.is_dir()

    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        try:
            from cpp_analyzer import run_clang_tidy
            return run_clang_tidy(target_path)
        except Exception:
            return []


class TypeScriptEslintVerificationEngine(VerificationEngine):
    """Linter and type-safety verification engine for TypeScript using TypeScript ESLint."""

    @property
    def name(self) -> str:
        return "eslint-typescript"

    @property
    def display_name(self) -> str:
        return "TypeScript ESLint"

    def is_applicable(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bool:
        p = Path(target_path)
        ts_exts = {".ts", ".tsx", ".mts", ".cts", ".d.ts"}
        if language and language.lower() in ("typescript", "ts", "tsx"):
            return True
        return p.suffix.lower() in ts_exts or p.is_dir()

    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        try:
            from typescript_analyzer import run_typescript_eslint
            return run_typescript_eslint(target_path)
        except Exception:
            return []


# ==============================================================================
# 3. PIPELINE FACADE (ORCHESTRATOR)
# ==============================================================================

@dataclass
class VerificationPipeline:
    """
    Unified verification pipeline orchestrator.
    Manages registered verification engines and aggregates results cleanly.
    """
    engines: list[VerificationEngine] = field(default_factory=list)

    @classmethod
    def create_default(cls) -> "VerificationPipeline":
        """Factory creating pipeline pre-configured with all standard engines."""
        pipeline = cls()
        pipeline.register_engine(RuffVerificationEngine())
        pipeline.register_engine(EslintVerificationEngine())
        pipeline.register_engine(TypeScriptEslintVerificationEngine())
        pipeline.register_engine(CppClangTidyVerificationEngine())
        pipeline.register_engine(SemgrepVerificationEngine())
        pipeline.register_engine(DependencyVerificationEngine())
        pipeline.register_engine(RfidDomainVerificationEngine())
        return pipeline

    def register_engine(self, engine: VerificationEngine) -> None:
        """Registers a new verification engine strategy into the pipeline."""
        self.engines.append(engine)

    def verify_target(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        """
        Runs all applicable registered engines against a single target file or code snippet.
        """
        all_findings: list[Finding] = []
        for engine in self.engines:
            if engine.is_applicable(target_path, source_code=source_code, language=language):
                findings = engine.verify(
                    target_path,
                    source_code=source_code,
                    language=language,
                    metadata=metadata,
                )
                all_findings.extend(findings)
        return all_findings

    def verify_repository(
        self,
        repo_path: str | Path,
    ) -> AnalysisResult:
        """
        Performs full AST parsing and comprehensive multi-engine verification on a repository.
        """
        p = Path(repo_path).resolve()
        start_time = time.perf_counter()

        # 1. AST Parsing
        parsed_files = analyze_repository(p)

        # 2. Run all engines
        all_findings: list[Finding] = []
        for engine in self.engines:
            if engine.is_applicable(p):
                findings = engine.verify(p)
                all_findings.extend(findings)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return AnalysisResult(
            repository_path=str(p),
            total_files_scanned=len(parsed_files),
            files=parsed_files,
            findings=all_findings,
            execution_time_ms=round(elapsed_ms, 2),
        )


# ==============================================================================
# 4. UNIT TESTS
# ==============================================================================

class TestVerificationPipeline(unittest.TestCase):
    """Unit tests for the VerificationPipeline and engine strategies."""

    def setUp(self) -> None:
        self.pipeline = VerificationPipeline.create_default()

    def test_pipeline_registration(self) -> None:
        """Verifies default engine registration."""
        engine_names = [e.name for e in self.pipeline.engines]
        self.assertIn("ruff", engine_names)
        self.assertIn("semgrep", engine_names)
        self.assertIn("dependency_scanner", engine_names)
        self.assertIn("rfid_domain_rule", engine_names)

    def test_rfid_engine_dispatch(self) -> None:
        """Verifies RFID domain engine execution via pipeline."""
        insecure_rfid = """
        #include <MFRC522.h>
        void loop() {
            if (mfrc522.PICC_IsNewCardPresent()) {
                unlockDoor();
            }
        }
        """
        findings = self.pipeline.verify_target("door.ino", source_code=insecure_rfid, language="C++")
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RFID-001-UNAUTHORIZED-UNLOCK")

    def test_safe_code_dispatch(self) -> None:
        """Verifies that safe code produces zero findings."""
        safe_python = "def add(a: int, b: int) -> int:\n    return a + b\n"
        findings = self.pipeline.verify_target("math_utils.py", source_code=safe_python, language="Python")
        self.assertEqual(len(findings), 0)


# ==============================================================================
# 5. CLI RUNNER
# ==============================================================================

if __name__ == "__main__":
    import argparse
    cli = argparse.ArgumentParser(description="Unified Verification Pipeline CLI")
    cli.add_argument("--test", action="store_true", help="Run pipeline unit tests")
    cli.add_argument("target", nargs="?", default=".", help="Path to repository or file to verify")

    args = cli.parse_args()

    if args.test:
        print("[+] Running VerificationPipeline unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestVerificationPipeline)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    else:
        pipeline = VerificationPipeline.create_default()
        print(f"[+] Scanning target: '{args.target}'")
        target_path = Path(args.target)
        if target_path.is_dir():
            result = pipeline.verify_repository(target_path)
            print(result.to_json())
        else:
            findings = pipeline.verify_target(target_path)
            print(json.dumps([f.to_dict() for f in findings], indent=2))
