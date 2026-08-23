"""
models.py - Common Data Models for AI Code Verification SaaS

Defines the normalized data structures used across the repository parser,
static-analysis engines (Ruff, Semgrep), dependency vulnerability scanners,
and domain-specific rule checkers (e.g. RFID compliance).

All models are implemented as Python dataclasses with built-in validation,
type safety, and serialization helpers for JSON and PostgreSQL storage.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import json
from pathlib import Path
from typing import Any, Optional, Self
import unittest


# ==============================================================================
# 1. ENUMS & CONSTANTS
# ==============================================================================

class FindingCategory(StrEnum):
    """
    Standardized categories for verification findings.
    Inherits from StrEnum (Python 3.11+) for direct string comparison and JSON compatibility.
    """
    LINT = "lint"
    STATIC_ANALYSIS = "static-analysis"
    SECURITY = "security"
    DEPENDENCY = "dependency"
    LOGIC = "logic"
    STYLE = "style"
    DOMAIN = "domain"
    OTHER = "other"


class FindingSeverity(StrEnum):
    """
    Standardized severity levels for findings.
    Follows industry-standard vulnerability scoring hierarchy.
    """
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==============================================================================
# 2. CODE PARSER METADATA MODELS
# ==============================================================================

@dataclass
class FunctionMetadata:
    """
    Metadata representation of a top-level function.

    Attributes:
        name: Name of the function.
        start_line: 1-indexed starting line in source code.
        end_line: 1-indexed ending line in source code.
        parameters: Ordered list of parameter signatures/names.
    """
    name: str
    start_line: int
    end_line: int
    parameters: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {self.start_line}")
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line ({self.end_line}) cannot be less than start_line ({self.start_line})"
            )

    def to_dict(self) -> dict[str, Any]:
        """Converts to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Constructs an instance from a dictionary."""
        return cls(
            name=data["name"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            parameters=list(data.get("parameters", [])),
        )


@dataclass
class MethodMetadata:
    """
    Metadata representation of a method inside a class, struct, or interface.

    Attributes:
        name: Name of the method.
        start_line: 1-indexed starting line in source code.
        end_line: 1-indexed ending line in source code.
        parameters: Ordered list of parameter signatures/names.
    """
    name: str
    start_line: int
    end_line: int
    parameters: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {self.start_line}")
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line ({self.end_line}) cannot be less than start_line ({self.start_line})"
            )

    def to_dict(self) -> dict[str, Any]:
        """Converts to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Constructs an instance from a dictionary."""
        return cls(
            name=data["name"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            parameters=list(data.get("parameters", [])),
        )


@dataclass
class ClassMetadata:
    """
    Metadata representation of a class, struct, or interface.

    Attributes:
        name: Name of the class/struct/interface.
        start_line: 1-indexed starting line in source code.
        end_line: 1-indexed ending line in source code.
        methods: List of method metadata instances defined within the class.
    """
    name: str
    start_line: int
    end_line: int
    methods: list[MethodMetadata] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {self.start_line}")
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line ({self.end_line}) cannot be less than start_line ({self.start_line})"
            )

    def to_dict(self) -> dict[str, Any]:
        """Converts to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Constructs an instance from a dictionary."""
        return cls(
            name=data["name"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            methods=[
                m if isinstance(m, MethodMetadata) else MethodMetadata.from_dict(m)
                for m in data.get("methods", [])
            ],
        )


@dataclass
class FileMetadata:
    """
    Normalized metadata extracted from a single source code file.

    Attributes:
        path: Relative or absolute POSIX path of the file.
        language: Programming language name (e.g. 'Python', 'JavaScript', 'C++', 'Java').
        imports: List of raw import/include statements.
        functions: Top-level functions declared in the file.
        classes: Classes declared in the file (along with nested methods).
        parse_errors: Any syntax or parser errors encountered during AST construction.
    """
    path: str
    language: str
    imports: list[str] = field(default_factory=list)
    functions: list[FunctionMetadata] = field(default_factory=list)
    classes: list[ClassMetadata] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Converts to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Constructs an instance from a dictionary."""
        return cls(
            path=data["path"],
            language=data["language"],
            imports=list(data.get("imports", [])),
            functions=[
                f if isinstance(f, FunctionMetadata) else FunctionMetadata.from_dict(f)
                for f in data.get("functions", [])
            ],
            classes=[
                c if isinstance(c, ClassMetadata) else ClassMetadata.from_dict(c)
                for c in data.get("classes", [])
            ],
            parse_errors=list(data.get("parse_errors", [])),
        )


# ==============================================================================
# 3. VERIFICATION & STATIC ANALYSIS FINDINGS
# ==============================================================================

@dataclass
class Finding:
    """
    Core normalized model representing an issue, defect, or rule violation
    discovered by any analysis tool (Ruff, Semgrep, Dependency Check, Domain Rules).

    Attributes:
        tool: Originating analysis tool (e.g. 'ruff', 'semgrep', 'tree-sitter', 'rfid-validator').
        category: Finding classification ('lint', 'security', 'dependency', 'logic', 'style', 'domain', 'other').
        severity: Impact level ('info', 'low', 'medium', 'high', 'critical').
        file: Target file path, or None for project-level findings.
        start_line: 1-indexed starting line number of the finding, if applicable.
        end_line: 1-indexed ending line number of the finding, if applicable.
        rule_id: Tool-specific or internal rule identifier (e.g. 'SEC-001', 'F401', 'RFID-ERR-02').
        message: Human-readable explanation of the finding.
        evidence: Code excerpt, matched pattern, or contextual snippet.
        confidence: Confidence score from 0.0 (uncertain) to 1.0 (certain), if provided.
        metadata: Arbitrary tool-specific metadata (CWE, OWASP, fix suggestions, references).
    """
    tool: str
    category: str
    severity: str
    file: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    rule_id: Optional[str] = None
    message: str = ""
    evidence: Optional[str] = None
    confidence: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize and validate finding category
        if isinstance(self.category, FindingCategory):
            self.category = self.category.value
        elif isinstance(self.category, str):
            normalized_cat = self.category.strip().lower()
            valid_categories = {c.value for c in FindingCategory}
            if normalized_cat not in valid_categories:
                raise ValueError(
                    f"Invalid finding category: '{self.category}'. "
                    f"Allowed categories: {sorted(valid_categories)}"
                )
            self.category = normalized_cat
        else:
            raise TypeError(
                f"category must be a str or FindingCategory, got {type(self.category).__name__}"
            )

        # Normalize and validate finding severity
        if isinstance(self.severity, FindingSeverity):
            self.severity = self.severity.value
        elif isinstance(self.severity, str):
            normalized_sev = self.severity.strip().lower()
            valid_severities = {s.value for s in FindingSeverity}
            if normalized_sev not in valid_severities:
                raise ValueError(
                    f"Invalid finding severity: '{self.severity}'. "
                    f"Allowed severities: {sorted(valid_severities)}"
                )
            self.severity = normalized_sev
        else:
            raise TypeError(
                f"severity must be a str or FindingSeverity, got {type(self.severity).__name__}"
            )

        # Validate confidence score if present
        if self.confidence is not None:
            if not (0.0 <= self.confidence <= 1.0):
                raise ValueError(
                    f"confidence score must be between 0.0 and 1.0, got {self.confidence}"
                )

        # Validate line range consistency if present
        if self.start_line is not None and self.start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {self.start_line}")
        if self.start_line is not None and self.end_line is not None:
            if self.end_line < self.start_line:
                raise ValueError(
                    f"end_line ({self.end_line}) cannot be less than start_line ({self.start_line})"
                )

    def to_dict(self) -> dict[str, Any]:
        """Converts to a clean JSON-serializable dictionary for PostgreSQL storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Constructs a Finding instance from a dictionary."""
        return cls(
            tool=data["tool"],
            category=data["category"],
            severity=data["severity"],
            file=data.get("file"),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
            rule_id=data.get("rule_id"),
            message=data.get("message", ""),
            evidence=data.get("evidence"),
            confidence=data.get("confidence"),
            metadata=dict(data.get("metadata", {})),
        )


# ==============================================================================
# 4. AGGREGATED ANALYSIS RESULT
# ==============================================================================

@dataclass
class AnalysisResult:
    """
    Unified analysis result bundling parsed repository metadata and all findings.
    Serves as the primary payload exchanged between SaaS pipeline stages.

    Attributes:
        files: List of FileMetadata objects extracted by the repository parser.
        findings: Consolidated list of Finding objects from all verification layers.
    """
    files: list[FileMetadata] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Converts the entire analysis result to a nested JSON-serializable dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serializes the analysis result directly to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Constructs an AnalysisResult from a dictionary / deserialized JSON."""
        return cls(
            files=[
                f if isinstance(f, FileMetadata) else FileMetadata.from_dict(f)
                for f in data.get("files", [])
            ],
            findings=[
                f if isinstance(f, Finding) else Finding.from_dict(f)
                for f in data.get("findings", [])
            ],
        )

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Constructs an AnalysisResult directly from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    # Helper filter methods for verification and reporting workflows
    def get_findings_by_severity(self, severity: str | FindingSeverity) -> list[Finding]:
        """Filters findings by severity level."""
        sev_str = severity.value if isinstance(severity, FindingSeverity) else severity.strip().lower()
        return [f for f in self.findings if f.severity == sev_str]

    def get_findings_by_category(self, category: str | FindingCategory) -> list[Finding]:
        """Filters findings by category."""
        cat_str = category.value if isinstance(category, FindingCategory) else category.strip().lower()
        return [f for f in self.findings if f.category == cat_str]

    def get_findings_by_file(self, file_path: str) -> list[Finding]:
        """Filters findings belonging to a specific file path."""
        return [f for f in self.findings if f.file == file_path]


# ==============================================================================
# 5. SHARED PATH & EVIDENCE UTILITIES (HIGH COHESION)
# ==============================================================================

def relativize_path(target_str: str, base_path: Optional[str | Path]) -> str:
    """
    Normalizes and relativizes file paths across Windows and POSIX platforms.
    """
    if not base_path or not target_str:
        return target_str

    t_norm = str(target_str).replace("\\", "/").strip()
    b_norm = str(base_path).replace("\\", "/").rstrip("/")

    if t_norm.startswith(b_norm + "/"):
        return t_norm[len(b_norm) + 1:]

    try:
        b_res = str(Path(base_path).resolve()).replace("\\", "/").rstrip("/")
        if t_norm.startswith(b_res + "/"):
            return t_norm[len(b_res) + 1:]
    except Exception:
        pass

    try:
        t_path = Path(target_str)
        b_path = Path(base_path)
        return str(t_path.relative_to(b_path)).replace("\\", "/")
    except Exception:
        return target_str


def extract_source_evidence(
    file_path_str: Optional[str | Path],
    start_line: Optional[int],
    end_line: Optional[int] = None,
) -> Optional[str]:
    """
    Extracts the exact source code snippet corresponding to the reported line range.
    Provides verifiable evidence for LLM / RAG downstream analysis.
    """
    if not file_path_str or not start_line:
        return None

    path = Path(file_path_str)
    if not path.is_file():
        return None

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        total_lines = len(lines)

        if 1 <= start_line <= total_lines:
            last_line = end_line if (end_line and start_line <= end_line <= total_lines) else start_line
            snippet_lines = lines[start_line - 1 : last_line]
            return "\n".join(snippet_lines).strip()
    except Exception:
        return None

    return None


# ==============================================================================
# 6. UNIT TESTS & CLI RUNNER
# ==============================================================================

class TestModels(unittest.TestCase):
    """Unit tests for domain models, dataclass serialization, and path utilities."""

    def test_finding_creation_and_normalization(self) -> None:
        f = Finding(
            tool="ruff",
            category="lint",
            severity="high",
            message="Test lint finding",
            file="src/app.py",
            start_line=10,
            end_line=12,
            rule_id="F401",
        )
        self.assertEqual(f.tool, "ruff")
        self.assertEqual(f.category, FindingCategory.LINT.value)
        self.assertEqual(f.severity, FindingSeverity.HIGH.value)
        self.assertEqual(f.to_dict()["file"], "src/app.py")

    def test_invalid_category_validation(self) -> None:
        with self.assertRaises(ValueError):
            Finding(
                tool="custom",
                category="invalid_category_xyz",
                severity="low",
                message="Invalid category test",
            )

    def test_analysis_result_serialization(self) -> None:
        finding = Finding(tool="semgrep", category="security", severity="critical", message="SQLi")
        res = AnalysisResult(findings=[finding])
        json_str = res.to_json()
        loaded = AnalysisResult.from_json(json_str)
        self.assertEqual(len(loaded.findings), 1)
        self.assertEqual(loaded.findings[0].severity, "critical")

    def test_relativize_path_utility(self) -> None:
        self.assertEqual(relativize_path("/repo/src/file.py", "/repo"), "src/file.py")
        self.assertEqual(relativize_path("C:\\repo\\src\\file.py", "C:/repo"), "src/file.py")


if __name__ == "__main__":
    import argparse
    cli = argparse.ArgumentParser(description="Core Data Models for AI Code Verification")
    cli.add_argument("--test", action="store_true", help="Run models unit tests")
    args = cli.parse_args()

    if args.test:
        print("[+] Running models unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestModels)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    else:
        cli.print_help()

