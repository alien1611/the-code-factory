"""
pipeline.py - Unified Verification Pipeline & Loose Coupling Facade

Implements Strategy and Facade patterns to decouple individual verification tools
(Ruff, Semgrep, Dependency Checker, RFID Verifier) from consumer modules.

Enables high cohesion (each engine has a single responsibility) and low coupling
(consumers interact exclusively through the VerificationEngine interface and Pipeline facade).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from typing import Any, Optional
import unittest

from models import (
    AnalysisResult,
    FileMetadata,
    Finding,
    FindingCategory,
    FindingSeverity,
    PRAnalysisResult,
)
from parser import analyze_file, analyze_repository, analyze_source
from change_mapper import map_changes_to_code
from context_builder import build_repository_context
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
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False, encoding="utf-8") as tmp:
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


SEMGREP_SUPPORTED_EXTENSIONS: set[str] = {
    ".py", ".pyi",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".mts", ".cts",
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx", ".ino",
    ".java", ".jav",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".rs",
    ".scala",
    ".kt", ".kts",
    ".swift",
    ".yaml", ".yml",
    ".json",
    ".sol",
    ".html", ".htm",
    ".sh", ".bash",
}

SEMGREP_SUPPORTED_LANGUAGES: set[str] = {
    "python", "py",
    "javascript", "js", "jsx",
    "typescript", "ts", "tsx",
    "c", "cpp", "c++", "arduino",
    "java",
    "go", "golang",
    "ruby", "rb",
    "php",
    "csharp", "c#", "cs",
    "rust", "rs",
    "scala",
    "kotlin",
    "swift",
    "yaml", "json", "solidity", "bash", "sh",
}


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
        p = Path(target_path)
        if language and language.lower().strip() in SEMGREP_SUPPORTED_LANGUAGES:
            return True
        if p.is_dir():
            return True
        if p.suffix.lower() in SEMGREP_SUPPORTED_EXTENSIONS:
            return True
        if source_code:
            return True
        return False

    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        if not shutil.which("semgrep"):
            return []

        p = Path(target_path)
        if p.exists():
            findings = run_semgrep(str(p), config=self.default_config)
            return [f for f in findings if f.category != FindingCategory.OTHER.value or "not installed" not in f.message]

        if source_code:
            ext = p.suffix if p.suffix else ".py"
            if language:
                lang_lower = language.lower().strip()
                if lang_lower in ("javascript", "js"):
                    ext = ".js"
                elif lang_lower in ("typescript", "ts"):
                    ext = ".ts"
                elif lang_lower in ("cpp", "c++", "c", "arduino"):
                    ext = ".cpp"
                elif lang_lower in ("java",):
                    ext = ".java"
                elif lang_lower in ("python", "py"):
                    ext = ".py"

            with tempfile.NamedTemporaryFile(mode="w+", suffix=ext, delete=False, encoding="utf-8") as tmp:
                tmp.write(source_code)
                tmp_path = Path(tmp.name)
            try:
                findings = run_semgrep(str(tmp_path), config=self.default_config)
                valid_findings: list[Finding] = []
                for f in findings:
                    if f.category == FindingCategory.OTHER.value and "not installed" in f.message:
                        continue
                    f.file = str(target_path)
                    valid_findings.append(f)
                return valid_findings
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

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
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False, encoding="utf-8") as tmp:
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
    """Linter and security verification engine for JavaScript using ESLint."""

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
        js_exts = {".js", ".jsx", ".mjs", ".cjs"}
        if language and language.lower() in ("javascript", "js"):
            return True
        return p.suffix.lower() in js_exts or p.is_dir()

    def verify(
        self,
        target_path: str | Path,
        source_code: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[FileMetadata] = None,
    ) -> list[Finding]:
        p = Path(target_path)
        if p.exists():
            try:
                from javascript_analyzer import run_eslint
                return run_eslint(target_path)
            except Exception:
                return []

        if source_code:
            ext = p.suffix if p.suffix else ".js"
            with tempfile.NamedTemporaryFile(mode="w+", suffix=ext, delete=False, encoding="utf-8") as tmp:
                tmp.write(source_code)
                tmp_path = Path(tmp.name)
            try:
                from javascript_analyzer import run_eslint
                findings = run_eslint(tmp_path)
                for f in findings:
                    f.file = str(target_path)
                return findings
            except Exception:
                return []
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

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
        p = Path(target_path)
        if p.exists():
            try:
                from cpp_analyzer import run_clang_tidy
                return run_clang_tidy(target_path)
            except Exception:
                return []

        if source_code:
            ext = p.suffix if p.suffix else ".cpp"
            with tempfile.NamedTemporaryFile(mode="w+", suffix=ext, delete=False, encoding="utf-8") as tmp:
                tmp.write(source_code)
                tmp_path = Path(tmp.name)
            try:
                from cpp_analyzer import run_clang_tidy
                findings = run_clang_tidy(tmp_path)
                for f in findings:
                    f.file = str(target_path)
                return findings
            except Exception:
                return []
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

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
        p = Path(target_path)
        if p.exists():
            try:
                from typescript_analyzer import run_typescript_eslint
                return run_typescript_eslint(target_path)
            except Exception:
                return []

        if source_code:
            ext = p.suffix if p.suffix else ".ts"
            with tempfile.NamedTemporaryFile(mode="w+", suffix=ext, delete=False, encoding="utf-8") as tmp:
                tmp.write(source_code)
                tmp_path = Path(tmp.name)
            try:
                from typescript_analyzer import run_typescript_eslint
                findings = run_typescript_eslint(tmp_path)
                for f in findings:
                    f.file = str(target_path)
                return findings
            except Exception:
                return []
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

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
# 4. BACKEND INTEGRATION HELPERS & ANALYZE_PR ENTRYPOINT
# ==============================================================================

def extract_changed_lines_from_patch(patch_str: str) -> list[int]:
    """
    Parses a unified diff patch string (standard GitHub PR patch format)
    and extracts 1-indexed line numbers of modified/added lines in the new file.
    """
    if not patch_str:
        return []

    changed_lines: list[int] = []
    current_line = 0

    hunk_header_re = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@")

    for line in patch_str.splitlines():
        hunk_match = hunk_header_re.match(line)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            continue

        if current_line == 0:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            changed_lines.append(current_line)
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            # Line deleted from old file, does not advance line number in new file
            pass
        elif line.startswith(" "):
            # Context line in new file
            current_line += 1
        elif line.startswith(r"\ "):
            # '\ No newline at end of file'
            pass

    return sorted(list(set(changed_lines)))


def normalize_pr_files(
    files_input: Any,
) -> tuple[list[dict[str, Any]], dict[str, list[int]], list[str]]:
    """
    Normalizes diverse backend file payloads into standard dictionary format:
    [
        {
            "path": "src/payment.py",
            "content": "...",
            "changed_lines": [42, 43, 44],
            "status": "modified" | "added" | "removed"
        }
    ]

    Extracts changed line numbers from 'patch' if 'changed_lines' is not explicitly provided.
    Safely handles deleted files and binary files without raising exceptions.
    """
    normalized_files: list[dict[str, Any]] = []
    changed_lines_map: dict[str, list[int]] = {}
    warnings: list[str] = []

    if not files_input:
        return normalized_files, changed_lines_map, warnings

    file_items = files_input if isinstance(files_input, list) else [files_input]

    for item in file_items:
        if not isinstance(item, dict):
            continue

        file_path = (
            item.get("path")
            or item.get("filename")
            or item.get("file")
            or item.get("name")
            or ""
        )
        if not file_path:
            continue

        file_path = Path(file_path).as_posix()
        status = (item.get("status") or "modified").lower()

        # Handle deleted files safely
        if status in ("removed", "deleted"):
            warnings.append(f"File was deleted in PR: {file_path}")
            continue

        # Extract content (string or decoded base64 if provided)
        raw_content = item.get("content")
        if raw_content is None:
            raw_content = item.get("source_code") or item.get("source") or ""

        if isinstance(raw_content, bytes):
            try:
                content = raw_content.decode("utf-8")
            except UnicodeDecodeError:
                warnings.append(f"Skipping binary/non-UTF8 file: {file_path}")
                continue
        else:
            content = str(raw_content)

        # Extract changed lines
        c_lines = item.get("changed_lines") or []
        if not c_lines and item.get("patch"):
            c_lines = extract_changed_lines_from_patch(item["patch"])

        if c_lines:
            changed_lines_map[file_path] = c_lines

        normalized_files.append({
            "path": file_path,
            "content": content,
            "changed_lines": c_lines,
            "status": status,
            "additions": item.get("additions", 0),
            "deletions": item.get("deletions", 0),
            "changes": item.get("changes", len(c_lines)),
            "sha": item.get("sha"),
        })

    return normalized_files, changed_lines_map, warnings


def analyze_pr(
    files: Optional[list[dict[str, Any]]] = None,
    changed_lines: Optional[dict[str, list[int]]] = None,
    pr_description: Optional[str] = None,
    repo_path: Optional[str | Path] = None,
    repository_meta: Optional[dict[str, Any]] = None,
    pipeline: Optional[VerificationPipeline] = None,
) -> PRAnalysisResult:
    """
    Main integration entry point for FastAPI backend and PR verification.

    Supports both backend execution modes:
    - Mode A (Full Repository): Analyzes a cloned repository workspace on disk.
    - Mode B (In-Memory Files): Analyzes in-memory file payloads without requiring a git clone.

    Returns:
        Structured, JSON-serializable PRAnalysisResult model.
    """
    pipe = pipeline or VerificationPipeline.create_default()
    repo_meta_dict = dict(repository_meta or {})
    errors: list[str] = []
    parsed_files: list[FileMetadata] = []
    source_code_map: dict[str, str] = {}
    effective_changed_lines: dict[str, list[int]] = dict(changed_lines or {})
    all_findings: list[Finding] = []

    # =========================================================================
    # MODE A: FULL REPOSITORY WORKSPACE
    # =========================================================================
    if repo_path:
        p = Path(repo_path).resolve()
        if not p.exists():
            errors.append(f"Specified repo_path does not exist: {repo_path}")
            return PRAnalysisResult(
                status="error",
                repository=repo_meta_dict,
                analysis={"files_analyzed": 0, "functions_found": 0, "classes_found": 0},
                errors=errors,
            )

        # 1. Parse repository files
        parsed_files = analyze_repository(p)

        # Populate source_code_map
        for meta in parsed_files:
            file_disk_path = Path(meta.path)
            if file_disk_path.exists():
                try:
                    source_code_map[meta.path] = file_disk_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

        # 2. Extract changed lines from files payload if provided
        if files:
            norm_files, extracted_lines, norm_warnings = normalize_pr_files(files)
            errors.extend(norm_warnings)
            for f_path, c_lines in extracted_lines.items():
                if f_path not in effective_changed_lines:
                    effective_changed_lines[f_path] = c_lines

        # 3. Run verification pipeline on repository
        repo_result = pipe.verify_repository(p)
        all_findings = repo_result.findings

    # =========================================================================
    # MODE B: IN-MEMORY FILES PAYLOAD
    # =========================================================================
    elif files is not None:
        norm_files, extracted_lines, norm_warnings = normalize_pr_files(files)
        errors.extend(norm_warnings)

        for f_path, c_lines in extracted_lines.items():
            if f_path not in effective_changed_lines:
                effective_changed_lines[f_path] = c_lines

        # 1. In-memory Tree-sitter parsing
        for item in norm_files:
            f_path = item["path"]
            f_content = item["content"]
            source_code_map[f_path] = f_content

            meta = analyze_source(f_content, f_path)
            parsed_files.append(meta)

            # 2. Run applicable static verification engines in-memory
            target_findings = pipe.verify_target(
                target_path=f_path,
                source_code=f_content,
                language=meta.language,
                metadata=meta,
            )
            all_findings.extend(target_findings)
    else:
        errors.append("Neither repo_path nor files was provided to analyze_pr.")
        return PRAnalysisResult(
            status="error",
            repository=repo_meta_dict,
            analysis={"files_analyzed": 0, "functions_found": 0, "classes_found": 0},
            errors=errors,
        )

    # =========================================================================
    # 4. CHANGED CODE MAPPING (change_mapper.py)
    # =========================================================================
    changed_code_map: dict[str, dict[str, Any]] = {}
    if effective_changed_lines and parsed_files:
        try:
            changed_code_map = map_changes_to_code(parsed_files, effective_changed_lines)
        except Exception as e:
            errors.append(f"Change mapping failed: {str(e)}")

    # =========================================================================
    # 5. RAG CONTEXT ASSEMBLY (context_builder.py)
    # =========================================================================
    contexts_payload: list[dict[str, Any]] = []
    if parsed_files:
        try:
            repo_display_path = str(repo_path) if repo_path else repo_meta_dict.get("name", "in-memory-workspace")
            repo_context = build_repository_context(
                file_metadata_list=parsed_files,
                source_code_map=source_code_map,
                findings=all_findings,
                changed_lines=effective_changed_lines,
                repository_path=repo_display_path,
                pr_description=pr_description,
            )
            contexts_payload = [chunk.to_dict() for chunk in repo_context.all_chunks]
        except Exception as e:
            errors.append(f"Context builder failed: {str(e)}")

    # =========================================================================
    # 6. ASSEMBLE PRAnalysisResult
    # =========================================================================
    detected_languages = sorted(list({f.language for f in parsed_files if f.language and f.language != "Unknown"}))
    if not repo_meta_dict.get("languages") and detected_languages:
        repo_meta_dict["languages"] = detected_languages

    functions_count = sum(len(f.functions) for f in parsed_files) + sum(
        sum(len(c.methods) for c in f.classes) for f in parsed_files
    )
    classes_count = sum(len(f.classes) for f in parsed_files)

    analysis_summary = {
        "files_analyzed": len(parsed_files),
        "functions_found": functions_count,
        "classes_found": classes_count,
    }

    changed_code_list = list(changed_code_map.values()) if isinstance(changed_code_map, dict) else []
    findings_list = [f.to_dict() for f in all_findings]

    return PRAnalysisResult(
        status="completed" if not errors else "completed_with_warnings",
        repository=repo_meta_dict,
        analysis=analysis_summary,
        changed_code=changed_code_list,
        findings=findings_list,
        contexts=contexts_payload,
        errors=errors,
    )


# ==============================================================================
# 5. BACKEND VERIFICATION SERVICE LAYER
# ==============================================================================

class VerificationService:
    """
    High-level verification service for FastAPI backend integration.
    Encapsulates pipeline execution, input normalization, error handling,
    and returns clean JSON-serializable PRAnalysisResult payloads.
    """
    def __init__(self, pipeline: Optional[VerificationPipeline] = None) -> None:
        self.pipeline = pipeline or VerificationPipeline.create_default()

    def verify_pull_request(
        self,
        files: Optional[list[dict[str, Any]]] = None,
        changed_lines: Optional[dict[str, list[int]]] = None,
        pr_description: Optional[str] = None,
        repo_path: Optional[str | Path] = None,
        repository_meta: Optional[dict[str, Any]] = None,
    ) -> PRAnalysisResult:
        """
        Entry point for FastAPI routes.
        Thinly delegates to analyze_pr with the configured pipeline.
        """
        return analyze_pr(
            files=files,
            changed_lines=changed_lines,
            pr_description=pr_description,
            repo_path=repo_path,
            repository_meta=repository_meta,
            pipeline=self.pipeline,
        )


# ==============================================================================
# 6. UNIT & INTEGRATION TESTS
# ==============================================================================

class TestVerificationPipeline(unittest.TestCase):
    """Unit tests for the VerificationPipeline and engine strategies."""

    def setUp(self) -> None:
        self.pipeline = VerificationPipeline.create_default()
        self.service = VerificationService(self.pipeline)

    def test_pipeline_registration(self) -> None:
        """Verifies default engine registration."""
        engine_names = [e.name for e in self.pipeline.engines]
        self.assertIn("ruff", engine_names)
        self.assertIn("semgrep", engine_names)
        self.assertIn("dependency_scanner", engine_names)
        self.assertIn("rfid_domain_rule", engine_names)
        self.assertIn("eslint", engine_names)
        self.assertIn("eslint-typescript", engine_names)
        self.assertIn("clang-tidy", engine_names)

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

    def test_semgrep_is_applicable(self) -> None:
        """Verifies that Semgrep is_applicable accurately filters code files vs non-code/binaries."""
        semgrep_engine = SemgrepVerificationEngine()
        self.assertTrue(semgrep_engine.is_applicable("app.py"))
        self.assertTrue(semgrep_engine.is_applicable("server.js"))
        self.assertTrue(semgrep_engine.is_applicable("service.ts"))
        self.assertTrue(semgrep_engine.is_applicable("engine.cpp"))
        self.assertTrue(semgrep_engine.is_applicable("Main.java"))
        self.assertTrue(semgrep_engine.is_applicable(Path("test_repository")))
        self.assertTrue(semgrep_engine.is_applicable("snippet", source_code="def foo(): pass"))

        self.assertFalse(semgrep_engine.is_applicable("image.png"))
        self.assertFalse(semgrep_engine.is_applicable("video.mp4"))
        self.assertFalse(semgrep_engine.is_applicable("document.pdf"))
        self.assertFalse(semgrep_engine.is_applicable("archive.zip"))
        self.assertFalse(semgrep_engine.is_applicable("program.exe"))
        self.assertFalse(semgrep_engine.is_applicable("compiled.pyc"))

    def test_extract_changed_lines_from_patch(self) -> None:
        """Verifies parsing of GitHub unified diff patch format."""
        patch = (
            "@@ -10,3 +10,4 @@ def add(a, b):\n"
            "     return a + b\n"
            "+def multiply(a, b):\n"
            "+    return a * b\n"
        )
        lines = extract_changed_lines_from_patch(patch)
        self.assertEqual(lines, [11, 12])

    def test_normalize_pr_files(self) -> None:
        """Verifies normalization of GitHub file payloads with deleted/binary handling."""
        raw_files = [
            {
                "filename": "src/payment.py",
                "content": "class PaymentProcessor:\n    pass\n",
                "patch": "@@ -1,1 +1,2 @@\n class PaymentProcessor:\n+    pass\n",
                "status": "modified",
            },
            {
                "filename": "old_file.py",
                "status": "removed",
            },
            {
                "filename": "binary_file.png",
                "content": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01",
                "status": "added",
            },
        ]
        norm_files, changed_lines, warnings = normalize_pr_files(raw_files)
        self.assertEqual(len(norm_files), 1)
        self.assertEqual(norm_files[0]["path"], "src/payment.py")
        self.assertEqual(changed_lines["src/payment.py"], [2])
        self.assertEqual(len(warnings), 2)

    def test_analyze_pr_in_memory_mode(self) -> None:
        """Verifies analyze_pr running completely in-memory (Mode B)."""
        files_payload = [
            {
                "path": "src/calculator.py",
                "content": "def add(a: int, b: int) -> int:\n    return a + b\n\ndef sub(a: int, b: int) -> int:\n    return a - b\n",
                "changed_lines": [1, 2],
            }
        ]
        result = analyze_pr(
            files=files_payload,
            pr_description="Add addition and subtraction helpers",
            repository_meta={"name": "my-org/my-repo", "commit_sha": "abc1234"},
        )
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.analysis["files_analyzed"], 1)
        self.assertEqual(result.analysis["functions_found"], 2)
        self.assertGreaterEqual(len(result.changed_code), 1)
        self.assertGreaterEqual(len(result.contexts), 1)

    def test_analyze_pr_full_repo_mode(self) -> None:
        """Verifies analyze_pr running on a physical repository workspace (Mode A)."""
        p = Path("test_repository")
        if p.exists():
            result = analyze_pr(
                repo_path=p,
                changed_lines={"calculator.py": [4]},
                repository_meta={"name": "alien1611/the-code-factory", "commit_sha": "c0135c0"},
            )
            self.assertIn(result.status, ("completed", "completed_with_warnings"))
            self.assertGreater(result.analysis["files_analyzed"], 0)
            self.assertIsInstance(result.findings, list)

    def test_multi_language_test_repository_files(self) -> None:
        """Verifies end-to-end analysis on all test_repository source files."""
        repo_dir = Path("test_repository")
        if not repo_dir.exists():
            self.skipTest("test_repository directory not found")

        # 1. Python calculator.py
        calc_path = repo_dir / "calculator.py"
        if calc_path.exists():
            res_py = analyze_pr(files=[{"path": "calculator.py", "content": calc_path.read_text(encoding="utf-8"), "changed_lines": [4, 5]}])
            self.assertEqual(res_py.status, "completed")
            self.assertEqual(res_py.repository["languages"], ["Python"])
            self.assertGreaterEqual(res_py.analysis["functions_found"] + res_py.analysis["classes_found"], 1)

        # 2. Broken Python broken_syntax.py
        broken_path = repo_dir / "broken_syntax.py"
        if broken_path.exists():
            res_broken = analyze_pr(files=[{"path": "broken_syntax.py", "content": broken_path.read_text(encoding="utf-8")}])
            self.assertIn(res_broken.status, ("completed", "completed_with_warnings"))

        # 3. JavaScript files: auth_service.js, payment_processor.js, service.js
        for js_file in ["auth_service.js", "payment_processor.js", "service.js"]:
            p = repo_dir / js_file
            if p.exists():
                res_js = analyze_pr(files=[{"path": js_file, "content": p.read_text(encoding="utf-8"), "changed_lines": [5]}])
                self.assertEqual(res_js.status, "completed")
                self.assertEqual(res_js.repository["languages"], ["JavaScript"])

        # 4. TypeScript minimal in-memory test
        ts_code = "export interface Config { timeout: number; }\nexport function init(c: Config): boolean { return true; }"
        res_ts = analyze_pr(files=[{"path": "src/config.ts", "content": ts_code, "changed_lines": [2]}])
        self.assertEqual(res_ts.status, "completed")
        self.assertEqual(res_ts.repository["languages"], ["TypeScript"])
        self.assertEqual(res_ts.analysis["functions_found"], 1)

        # 5. C++ engine.cpp
        cpp_path = repo_dir / "engine.cpp"
        if cpp_path.exists():
            res_cpp = analyze_pr(files=[{"path": "engine.cpp", "content": cpp_path.read_text(encoding="utf-8"), "changed_lines": [5]}])
            self.assertEqual(res_cpp.status, "completed")
            self.assertEqual(res_cpp.repository["languages"], ["C++"])

        # 6. Java PaymentProcessor.java
        java_path = repo_dir / "PaymentProcessor.java"
        if java_path.exists():
            res_java = analyze_pr(files=[{"path": "PaymentProcessor.java", "content": java_path.read_text(encoding="utf-8"), "changed_lines": [10]}])
            self.assertEqual(res_java.status, "completed")
            self.assertEqual(res_java.repository["languages"], ["Java"])

    def test_verification_service_wrapper(self) -> None:
        """Verifies VerificationService helper for FastAPI routing."""
        files = [{"path": "calculator.py", "content": "def add(a, b):\n    return a + b\n", "changed_lines": [2]}]
        res = self.service.verify_pull_request(
            files=files,
            pr_description="Add calculation function",
            repository_meta={"name": "test-owner/test-repo", "commit_sha": "abc1234"},
        )
        self.assertEqual(res.status, "completed")
        self.assertEqual(res.repository["name"], "test-owner/test-repo")
        self.assertEqual(res.analysis["files_analyzed"], 1)
        self.assertGreaterEqual(len(res.contexts), 1)


# ==============================================================================
# 6. CLI RUNNER
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
