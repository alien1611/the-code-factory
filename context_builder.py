"""
context_builder.py - Repository Context Assembly Layer for AI Code Verification SaaS

Transforms AST metadata, source code slices, PR change mappings, and static-analysis
findings into granular, structured, and normalized context objects ready for downstream
indexing, vector embedding, and targeted LLM verification.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any, Optional
import unittest

from models import ClassMetadata, FileMetadata, Finding, FunctionMetadata, MethodMetadata
from change_mapper import map_changes_to_code


# ==============================================================================
# 1. STRUCTURED CONTEXT DATA MODELS
# ==============================================================================

@dataclass
class FunctionContext:
    """
    Granular context unit representing a function or method.
    Designed to be directly ingested by vector databases or RAG pipelines.

    Attributes:
        file: Repository-relative file path.
        language: Programming language name.
        function: Name of the function or method.
        class_name: Enclosing class/struct/interface name, or None for standalone functions.
        lines: 1-indexed start and end line coordinates {"start": int, "end": int}.
        source: Exact source code string of the function.
        parameters: Declared parameter names and type signatures.
        imports: List of module-level import statements.
        findings: Relevant static-analysis findings occurring within this function.
        is_changed: True if any PR changed lines fall inside this function.
        metadata: Indexing attributes (character count, estimated tokens, scope type).
    """
    file: str
    language: str
    function: str
    class_name: Optional[str] = None
    lines: dict[str, int] = field(default_factory=dict)
    source: str = ""
    parameters: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    is_changed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converts to a clean, stable JSON-serializable dictionary."""
        return {
            "file": self.file,
            "language": self.language,
            "function": self.function,
            "class": self.class_name,
            "lines": self.lines,
            "source": self.source,
            "parameters": self.parameters,
            "imports": self.imports,
            "findings": self.findings,
            "is_changed": self.is_changed,
            "metadata": self.metadata,
        }


@dataclass
class FileContext:
    """
    Comprehensive context representation of an entire parsed source file.

    Attributes:
        file: Repository-relative file path.
        language: Programming language.
        total_lines: Total line count of the source file.
        imports: Declared imports in the file.
        functions: Granular FunctionContext objects for all functions/methods.
        classes: Declared class definitions.
        findings: All static-analysis findings mapped to this file.
        is_changed: True if this file was modified in the PR.
        parse_errors: Any AST parsing errors encountered.
        test_files: Associated test files discovered in the codebase.
    """
    file: str
    language: str
    total_lines: int = 0
    imports: list[str] = field(default_factory=list)
    functions: list[FunctionContext] = field(default_factory=list)
    classes: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    is_changed: bool = False
    parse_errors: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Converts to a JSON-serializable dictionary."""
        return {
            "file": self.file,
            "language": self.language,
            "total_lines": self.total_lines,
            "imports": self.imports,
            "functions": [f.to_dict() for f in self.functions],
            "classes": self.classes,
            "findings": self.findings,
            "is_changed": self.is_changed,
            "parse_errors": self.parse_errors,
            "test_files": self.test_files,
        }


@dataclass
class RepositoryContext:
    """
    Consolidated repository verification payload.

    Attributes:
        repository_path: Root path of the analyzed repository.
        files: List of FileContext objects.
        all_chunks: Complete list of granular FunctionContext chunks for RAG indexing.
        changed_chunks: Filtered subset of changed functions for targeted PR verification.
        total_findings: Total number of static-analysis findings.
    """
    repository_path: str
    files: list[FileContext] = field(default_factory=list)
    all_chunks: list[FunctionContext] = field(default_factory=list)
    changed_chunks: list[FunctionContext] = field(default_factory=list)
    total_findings: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Converts to a JSON-serializable dictionary."""
        return {
            "repository_path": self.repository_path,
            "files": [f.to_dict() for f in self.files],
            "all_chunks": [c.to_dict() for c in self.all_chunks],
            "changed_chunks": [c.to_dict() for c in self.changed_chunks],
            "total_findings": self.total_findings,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serializes directly to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


# ==============================================================================
# 2. HELPER UTILITIES
# ==============================================================================

def _normalize_path(path_str: str) -> str:
    """Standardizes path strings to lower-case POSIX format."""
    return Path(path_str).as_posix().lower()


def _extract_source_slice(source_text: str, start_line: int, end_line: int) -> str:
    """Extracts a 1-indexed slice of code from the source string."""
    if not source_text or start_line < 1:
        return ""
    lines = source_text.splitlines()
    total = len(lines)
    if start_line > total:
        return ""
    last = min(end_line, total) if end_line >= start_line else start_line
    return "\n".join(lines[start_line - 1 : last])


def _filter_findings_for_range(
    file_path: str,
    start_line: int,
    end_line: int,
    findings: list[Finding],
) -> list[dict[str, Any]]:
    """Filters findings that overlap with a specific file line range."""
    norm_target_p = _normalize_path(file_path)
    matched: list[dict[str, Any]] = []

    for f in findings:
        if not f.file:
            continue
        norm_f_path = _normalize_path(f.file)
        if norm_f_path.endswith(norm_target_p) or norm_target_p.endswith(norm_f_path):
            f_start = f.start_line or 1
            f_end = f.end_line or f_start
            # Check for range overlap: [start_line, end_line] overlaps [f_start, f_end]
            if not (f_end < start_line or f_start > end_line):
                matched.append(f.to_dict())

    return matched


def _find_associated_tests(file_path: str, all_repo_paths: list[str]) -> list[str]:
    """Identifies test files corresponding to a source file by convention."""
    base_stem = Path(file_path).stem.lower()
    associated: list[str] = []

    # Common test naming conventions
    test_patterns = {
        f"test_{base_stem}",
        f"{base_stem}_test",
        f"{base_stem}.test",
        f"{base_stem}.spec",
    }

    for p_str in all_repo_paths:
        p = Path(p_str)
        p_stem = p.stem.lower()
        if any(p_stem.startswith(pat) or p_stem.endswith(pat) for pat in test_patterns):
            norm = Path(p_str).as_posix()
            if norm != Path(file_path).as_posix() and norm not in associated:
                associated.append(norm)

    return associated


# ==============================================================================
# 3. BUILDER IMPLEMENTATIONS
# ==============================================================================

def build_function_context(
    func_name: str,
    start_line: int,
    end_line: int,
    parameters: list[str],
    file_path: str,
    language: str,
    imports: list[str],
    source_code: str,
    class_name: Optional[str] = None,
    findings: Optional[list[Finding]] = None,
    changed_lines: Optional[list[int]] = None,
) -> FunctionContext:
    """
    Constructs a granular FunctionContext chunk for a function or method.
    """
    findings_list = findings or []
    changed_set = set(changed_lines or [])

    # Extract source slice
    code_slice = _extract_source_slice(source_code, start_line, end_line)

    # Determine if this function contains any PR modifications
    is_changed = any(start_line <= line <= end_line for line in changed_set)

    # Match static-analysis findings overlapping this function
    relevant_findings = _filter_findings_for_range(file_path, start_line, end_line, findings_list)

    # Retrieval and indexing metadata
    metadata = {
        "char_count": len(code_slice),
        "estimated_tokens": max(1, len(code_slice) // 4),
        "scope": "method" if class_name else "function",
        "has_findings": len(relevant_findings) > 0,
    }

    return FunctionContext(
        file=Path(file_path).as_posix(),
        language=language.lower(),
        function=func_name,
        class_name=class_name,
        lines={"start": start_line, "end": end_line},
        source=code_slice,
        parameters=parameters,
        imports=imports,
        findings=relevant_findings,
        is_changed=is_changed,
        metadata=metadata,
    )


def build_file_context(
    file_metadata: FileMetadata,
    source_code: str,
    findings: Optional[list[Finding]] = None,
    changed_lines_map: Optional[dict[str, list[int]]] = None,
    all_repo_files: Optional[list[str]] = None,
) -> FileContext:
    """
    Constructs a comprehensive FileContext object for a single source file.
    """
    findings_list = findings or []
    changed_map = changed_lines_map or {}
    repo_files = all_repo_files or []

    file_path = file_metadata.path
    norm_p = _normalize_path(file_path)

    # Resolve changed lines for this file
    changed_lines: list[int] = []
    for k, v in changed_map.items():
        if _normalize_path(k).endswith(norm_p) or norm_p.endswith(_normalize_path(k)):
            changed_lines = v
            break

    is_changed = len(changed_lines) > 0
    total_lines = len(source_code.splitlines()) if source_code else 0

    # Build function contexts
    functions_context: list[FunctionContext] = []

    # 1. Top-level functions
    for fn in file_metadata.functions:
        fc = build_function_context(
            func_name=fn.name,
            start_line=fn.start_line,
            end_line=fn.end_line,
            parameters=fn.parameters,
            file_path=file_path,
            language=file_metadata.language,
            imports=file_metadata.imports,
            source_code=source_code,
            class_name=None,
            findings=findings_list,
            changed_lines=changed_lines,
        )
        functions_context.append(fc)

    # 2. Classes and inner methods
    classes_summary: list[dict[str, Any]] = []
    for cls in file_metadata.classes:
        cls_dict = {
            "name": cls.name,
            "lines": {"start": cls.start_line, "end": cls.end_line},
            "methods_count": len(cls.methods),
        }
        classes_summary.append(cls_dict)

        for m in cls.methods:
            mc = build_function_context(
                func_name=m.name,
                start_line=m.start_line,
                end_line=m.end_line,
                parameters=m.parameters,
                file_path=file_path,
                language=file_metadata.language,
                imports=file_metadata.imports,
                source_code=source_code,
                class_name=cls.name,
                findings=findings_list,
                changed_lines=changed_lines,
            )
            functions_context.append(mc)

    # All findings mapped to this file
    file_findings = _filter_findings_for_range(file_path, 1, max(1, total_lines), findings_list)

    # Associated test files
    associated_tests = _find_associated_tests(file_path, repo_files)

    return FileContext(
        file=Path(file_path).as_posix(),
        language=file_metadata.language.lower(),
        total_lines=total_lines,
        imports=file_metadata.imports,
        functions=functions_context,
        classes=classes_summary,
        findings=file_findings,
        is_changed=is_changed,
        parse_errors=file_metadata.parse_errors,
        test_files=associated_tests,
    )


def build_repository_context(
    file_metadata_list: list[FileMetadata],
    source_code_map: Optional[dict[str, str]] = None,
    findings: Optional[list[Finding]] = None,
    changed_lines: Optional[dict[str, list[int]]] = None,
    repository_path: str = "./",
) -> RepositoryContext:
    """
    Assembles unified context across all repository files.

    Parameters:
        file_metadata_list: FileMetadata list produced by parser.py.
        source_code_map: Optional pre-loaded dict of {file_path: source_text}.
                         If omitted, reads files directly from disk.
        findings: Consolidated list of static-analysis / security findings.
        changed_lines: Mapping from file to list of PR changed line numbers.
        repository_path: Root directory path of the repository.

    Returns:
        Structured RepositoryContext ready for vector DB indexing and verification.
    """
    sources = source_code_map or {}
    findings_list = findings or []
    changed_map = changed_lines or {}

    repo_files = [m.path for m in file_metadata_list]
    files_context: list[FileContext] = []
    all_chunks: list[FunctionContext] = []
    changed_chunks: list[FunctionContext] = []

    for meta in file_metadata_list:
        source_text = sources.get(meta.path)
        if source_text is None:
            p = Path(meta.path)
            if p.is_file():
                try:
                    source_text = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    source_text = ""
            else:
                source_text = ""

        fc = build_file_context(
            file_metadata=meta,
            source_code=source_text,
            findings=findings_list,
            changed_lines_map=changed_map,
            all_repo_files=repo_files,
        )

        files_context.append(fc)
        all_chunks.extend(fc.functions)

        for chunk in fc.functions:
            if chunk.is_changed:
                changed_chunks.append(chunk)

    return RepositoryContext(
        repository_path=Path(repository_path).as_posix(),
        files=files_context,
        all_chunks=all_chunks,
        changed_chunks=changed_chunks,
        total_findings=len(findings_list),
    )


# ==============================================================================
# 4. UNIT TESTS
# ==============================================================================

class TestContextBuilder(unittest.TestCase):
    """Unit test suite verifying context assembly and retrieval metadata."""

    def setUp(self) -> None:
        self.sample_code = (
            "import math\n"
            "from typing import Optional\n\n"
            "def calculate_tax(amount: float, rate: float = 0.2) -> float:\n"
            "    return amount * rate\n\n"
            "class PaymentProcessor:\n"
            "    def __init__(self, key: str):\n"
            "        self.key = key\n\n"
            "    def process_payment(self, account_id: str, amount: float) -> bool:\n"
            "        if amount <= 0:\n"
            "            return False\n"
            "        return True\n"
        )

        self.fn_tax = FunctionMetadata(name="calculate_tax", start_line=4, end_line=5, parameters=["amount", "rate"])
        self.m_init = MethodMetadata(name="__init__", start_line=8, end_line=9, parameters=["self", "key"])
        self.m_process = MethodMetadata(name="process_payment", start_line=11, end_line=14, parameters=["self", "account_id", "amount"])
        self.cls_proc = ClassMetadata(name="PaymentProcessor", start_line=7, end_line=14, methods=[self.m_init, self.m_process])

        self.file_meta = FileMetadata(
            path="src/payment.py",
            language="Python",
            imports=["import math", "from typing import Optional"],
            functions=[self.fn_tax],
            classes=[self.cls_proc],
            parse_errors=[],
        )

        self.finding_sec = Finding(
            tool="semgrep",
            category="security",
            severity="high",
            file="src/payment.py",
            start_line=12,
            end_line=13,
            rule_id="SEC-01",
            message="Unchecked amount validation",
        )

    def test_build_function_context_standalone(self) -> None:
        """Verifies standalone function context creation."""
        fc = build_function_context(
            func_name="calculate_tax",
            start_line=4,
            end_line=5,
            parameters=["amount", "rate"],
            file_path="src/payment.py",
            language="Python",
            imports=["import math"],
            source_code=self.sample_code,
            class_name=None,
            findings=[self.finding_sec],
            changed_lines=[4],
        )

        d = fc.to_dict()
        self.assertEqual(d["file"], "src/payment.py")
        self.assertEqual(d["function"], "calculate_tax")
        self.assertIsNone(d["class"])
        self.assertEqual(d["lines"], {"start": 4, "end": 5})
        self.assertTrue(d["is_changed"])
        self.assertIn("return amount * rate", d["source"])
        self.assertEqual(len(d["findings"]), 0)  # Finding is on line 12, outside calculate_tax

    def test_build_function_context_method_with_finding(self) -> None:
        """Verifies class method context correctly links findings and parent class."""
        mc = build_function_context(
            func_name="process_payment",
            start_line=11,
            end_line=14,
            parameters=["self", "account_id", "amount"],
            file_path="src/payment.py",
            language="Python",
            imports=["import math"],
            source_code=self.sample_code,
            class_name="PaymentProcessor",
            findings=[self.finding_sec],
            changed_lines=[12],
        )

        d = mc.to_dict()
        self.assertEqual(d["class"], "PaymentProcessor")
        self.assertEqual(d["function"], "process_payment")
        self.assertTrue(d["is_changed"])
        self.assertEqual(len(d["findings"]), 1)
        self.assertEqual(d["findings"][0]["rule_id"], "SEC-01")

    def test_build_file_context(self) -> None:
        """Verifies file context aggregates all functions and classes."""
        fc = build_file_context(
            file_metadata=self.file_meta,
            source_code=self.sample_code,
            findings=[self.finding_sec],
            changed_lines_map={"src/payment.py": [12]},
            all_repo_files=["src/payment.py", "tests/test_payment.py"],
        )

        d = fc.to_dict()
        self.assertEqual(d["file"], "src/payment.py")
        self.assertTrue(d["is_changed"])
        self.assertEqual(len(d["functions"]), 3)  # 1 top-level func + 2 class methods
        self.assertEqual(len(d["classes"]), 1)
        self.assertEqual(d["test_files"], ["tests/test_payment.py"])

    def test_build_repository_context(self) -> None:
        """Verifies repository-level context assembly and chunk partitioning."""
        repo_ctx = build_repository_context(
            file_metadata_list=[self.file_meta],
            source_code_map={"src/payment.py": self.sample_code},
            findings=[self.finding_sec],
            changed_lines={"src/payment.py": [12]},
            repository_path="my_project",
        )

        d = repo_ctx.to_dict()
        self.assertEqual(d["repository_path"], "my_project")
        self.assertEqual(len(d["files"]), 1)
        self.assertEqual(len(d["all_chunks"]), 3)
        self.assertEqual(len(d["changed_chunks"]), 1)  # Only process_payment changed
        self.assertEqual(d["changed_chunks"][0]["function"], "process_payment")
        self.assertEqual(d["total_findings"], 1)


# ==============================================================================
# 5. CLI DEMONSTRATION RUNNER
# ==============================================================================

if __name__ == "__main__":
    parser_cli = argparse.ArgumentParser(
        description="Build structured repository context for AI code verification."
    )
    parser_cli.add_argument(
        "--test",
        action="store_true",
        help="Run unit tests",
    )
    parser_cli.add_argument(
        "repository_path",
        nargs="?",
        default="./test_repository",
        help="Path to repository to build context for (default: ./test_repository)",
    )

    args = parser_cli.parse_args()

    if args.test:
        print("[+] Executing ContextBuilder test suite...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestContextBuilder)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    target_repo = Path(args.repository_path)
    print(f"[+] Assembling structured context for repository: '{target_repo}'")

    try:
        from parser import analyze_repository
        from static_analysis import run_static_analysis

        repo_meta = analyze_repository(target_repo)
        repo_findings = run_static_analysis(target_repo)

        sample_diff = {
            "calculator.py": [4, 11],
            "service.js": [15],
        }

        ctx = build_repository_context(
            file_metadata_list=repo_meta,
            findings=repo_findings,
            changed_lines=sample_diff,
            repository_path=str(target_repo),
        )

        print("\n" + "=" * 50)
        print("SAMPLE FUNCTION CHUNK (Ready for Vector Indexing):")
        print("=" * 50)
        if ctx.all_chunks:
            print(json.dumps(ctx.all_chunks[0].to_dict(), indent=2))

        print("\n" + "=" * 50)
        print("CHANGED CHUNKS (High-priority PR verification targets):")
        print("=" * 50)
        for chunk in ctx.changed_chunks:
            print(f" - [{chunk.file}] {chunk.class_name or ''} {chunk.function}() (lines {chunk.lines['start']}-{chunk.lines['end']})")

        print("\n" + "=" * 50)
        print("REPOSITORY CONTEXT SUMMARY")
        print("=" * 50)
        print(f"Files Indexed   : {len(ctx.files)}")
        print(f"Total Chunks    : {len(ctx.all_chunks)}")
        print(f"Changed Chunks  : {len(ctx.changed_chunks)}")
        print(f"Total Findings  : {ctx.total_findings}")
        print("=" * 50)

    except Exception as e:
        print(f"Context build note: {e}")
