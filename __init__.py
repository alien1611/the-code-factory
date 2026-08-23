"""
AI Code Verification Engine - Root Package

Exposes a clean, unified public API for all AST parsers, static analyzers,
security verifiers, and the orchestration pipeline.
"""

from models import (
    AnalysisResult,
    ClassMetadata,
    FileMetadata,
    Finding,
    FindingCategory,
    FindingSeverity,
    FunctionMetadata,
    PRAnalysisResult,
    extract_source_evidence,
    relativize_path,
)
from parser import analyze_file, analyze_repository, analyze_source
from static_analysis import run_ruff, run_static_analysis
from semgrep_analyzer import run_semgrep
from javascript_analyzer import run_eslint
from typescript_analyzer import run_typescript_eslint
from cpp_analyzer import run_clang_tidy
from dependency_checker import check_dependencies, run_npm_audit, run_pip_audit
from rfid_verifier import verify_rfid_authentication, verify_rfid_repository
from change_mapper import map_changes_to_code
from context_builder import build_file_context, build_repository_context
from pipeline import (
    VerificationEngine,
    VerificationPipeline,
    VerificationService,
    analyze_pr,
    extract_changed_lines_from_patch,
    normalize_pr_files,
)
from behavioral_engine import (
    BehavioralExecutionResult,
    TestItemEvidence,
    run_behavioral_tests,
)
from aggregator import aggregate
from verifier import generate_verification_spec
from code_parser import parse_profile

__all__ = [
    # Models
    "AnalysisResult",
    "ClassMetadata",
    "FileMetadata",
    "Finding",
    "FindingCategory",
    "FindingSeverity",
    "FunctionMetadata",
    "PRAnalysisResult",
    "extract_source_evidence",
    "relativize_path",
    # Parsers
    "analyze_file",
    "analyze_repository",
    "analyze_source",
    "parse_profile",
    # Static Analyzers
    "run_ruff",
    "run_eslint",
    "run_typescript_eslint",
    "run_clang_tidy",
    "run_semgrep",
    "run_static_analysis",
    # Security & Dependency Checkers
    "check_dependencies",
    "run_pip_audit",
    "run_npm_audit",
    "verify_rfid_authentication",
    "verify_rfid_repository",
    # PR Diff & RAG Context
    "map_changes_to_code",
    "build_file_context",
    "build_repository_context",
    # Pipeline Facade & PR Entrypoint
    "VerificationEngine",
    "VerificationPipeline",
    "VerificationService",
    "analyze_pr",
    "extract_changed_lines_from_patch",
    "normalize_pr_files",
    # Verification, Test Generation & Behavioral Engine
    "BehavioralExecutionResult",
    "TestItemEvidence",
    "run_behavioral_tests",
    "generate_verification_spec",
    "aggregate",
]
