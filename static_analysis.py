"""
static_analysis.py - Static Analysis Execution Layer for AI Code Verification SaaS

Executes static analysis linters and security scanners (Ruff, Semgrep)
and normalizes tool-specific diagnostics into unified Finding models defined in models.py.

Designed for reliability: uses structured JSON communication with child processes,
gracefully catches runtime failures, and extracts exact source code snippets for evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Optional
import unittest

from models import Finding, FindingCategory, FindingSeverity, extract_source_evidence


# ==============================================================================
# 1. HELPER UTILITIES: SEVERITY MAPPING
# ==============================================================================

def map_ruff_severity(rule_code: Optional[str], ruff_severity: Optional[str]) -> str:
    """
    Maps Ruff diagnostics and rule prefixes into normalized FindingSeverity levels.

    Hierarchy mapping:
    - Syntax errors ('invalid-syntax', E999, F999) -> CRITICAL
    - Security / Bandit rules (S...) -> HIGH
    - Pyflakes variable / undefined errors (F821, F822) -> MEDIUM
    - Standard lint warnings / errors (E..., F..., W...) -> LOW
    - Style, formatting, and docstrings (I..., D...) -> INFO
    """
    if not rule_code:
        return FindingSeverity.LOW.value

    code_upper = rule_code.upper()

    # Syntax and compilation blockers
    if code_upper in ("INVALID-SYNTAX", "E999", "F999"):
        return FindingSeverity.CRITICAL.value

    # Bandit security rules (S101, S105, S608 SQLi, etc.)
    if code_upper.startswith("S"):
        return FindingSeverity.HIGH.value

    # Undefined names, imports, runtime syntax issues
    if code_upper.startswith("F8") or code_upper.startswith("E9"):
        return FindingSeverity.MEDIUM.value

    # Respect Ruff's explicit severity if provided
    if ruff_severity:
        sev_lower = ruff_severity.lower()
        if sev_lower == "error":
            return FindingSeverity.LOW.value
        elif sev_lower == "warning":
            return FindingSeverity.LOW.value
        elif sev_lower == "info":
            return FindingSeverity.INFO.value

    # Style and docstrings
    if code_upper.startswith("D") or code_upper.startswith("I"):
        return FindingSeverity.INFO.value

    return FindingSeverity.LOW.value


# ==============================================================================
# 2. RUFF STATIC ANALYSIS RUNNER
# ==============================================================================

def _get_ruff_command(target_path: Path) -> list[str]:
    """
    Determines the appropriate command to invoke Ruff on the current platform.
    Prefers standalone 'ruff' CLI executable, falls back to 'python -m ruff'.
    """
    ruff_bin = shutil.which("ruff")
    if ruff_bin:
        return [ruff_bin, "check", str(target_path), "--output-format=json"]
    return [sys.executable, "-m", "ruff", "check", str(target_path), "--output-format=json"]


def run_ruff(repo_path: str | Path) -> list[Finding]:
    """
    Runs the Ruff linter on a Python codebase and returns normalized Findings.

    Features:
    - Communicates via structured JSON (--output-format=json).
    - Avoids regex parsing for total reliability.
    - Captures file, start_line, end_line, rule_id, message, and source evidence.
    - Handles missing Ruff, invalid paths, and subprocess errors without crashing.
    """
    target = Path(repo_path).resolve()
    findings: list[Finding] = []

    # Handle non-existent repository path gracefully
    if not target.exists():
        return [
            Finding(
                tool="ruff",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.HIGH.value,
                message=f"Repository path does not exist: {target}",
            )
        ]

    cmd = _get_ruff_command(target)

    try:
        # Note: Ruff returns exit code 1 when lint errors are detected (standard behavior).
        # Hence check=False so subprocess does not raise CalledProcessError.
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except FileNotFoundError:
        return [
            Finding(
                tool="ruff",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.INFO.value,
                message="Ruff is not installed or not available on PATH.",
            )
        ]
    except subprocess.TimeoutExpired:
        return [
            Finding(
                tool="ruff",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.HIGH.value,
                message=f"Ruff execution timed out after 120s on path: {target}",
            )
        ]
    except Exception as e:
        return [
            Finding(
                tool="ruff",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.HIGH.value,
                message=f"Unexpected error running Ruff: {str(e)}",
            )
        ]

    stdout_raw = process.stdout.strip()
    if not stdout_raw:
        # Exit code 0 or empty output indicates no issues detected
        return []

    try:
        raw_issues = json.loads(stdout_raw)
    except json.JSONDecodeError as err:
        return [
            Finding(
                tool="ruff",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.HIGH.value,
                message=f"Failed to parse Ruff JSON output: {str(err)}",
                evidence=stdout_raw[:200],
            )
        ]

    if not isinstance(raw_issues, list):
        return []

    # Transform each Ruff issue into a normalized Finding
    for issue in raw_issues:
        if not isinstance(issue, dict):
            continue

        file_str = issue.get("filename")
        rule_code = issue.get("code")
        message_str = issue.get("message", "")
        raw_severity = issue.get("severity")

        # Extract 1-indexed coordinates from Ruff's location objects
        loc = issue.get("location") or {}
        end_loc = issue.get("end_location") or {}
        start_line = loc.get("row")
        end_line = end_loc.get("row") or start_line

        # Map category: Security for Bandit rules, Lint for standard rules
        category = (
            FindingCategory.SECURITY.value
            if (rule_code and rule_code.upper().startswith("S"))
            else FindingCategory.LINT.value
        )

        # Map severity
        severity = map_ruff_severity(rule_code, raw_severity)

        # Extract exact source code line snippet for evidence
        evidence = extract_source_evidence(file_str, start_line, end_line)

        # Retain rule documentation URL and fix metadata if available
        metadata: dict[str, Any] = {}
        if issue.get("url"):
            metadata["url"] = issue["url"]
        if issue.get("name"):
            metadata["rule_name"] = issue["name"]
        if issue.get("fix"):
            metadata["fix"] = issue["fix"]

        finding = Finding(
            tool="ruff",
            category=category,
            severity=severity,
            file=file_str,
            start_line=start_line,
            end_line=end_line,
            rule_id=rule_code,
            message=message_str,
            evidence=evidence,
            confidence=1.0,  # Deterministic AST rule engine
            metadata=metadata,
        )
        findings.append(finding)

    return findings


# ==============================================================================
# 3. UNIFIED STATIC ANALYSIS ENTRYPOINT
# ==============================================================================

def is_ruff_available() -> bool:
    """
    Returns True if Ruff CLI or python -m ruff is installed and available.
    """
    if shutil.which("ruff"):
        return True
    try:
        res = subprocess.run([sys.executable, "-m", "ruff", "--version"], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


def get_ruff_version() -> Optional[str]:
    """
    Retrieves the installed Ruff version string, or None if unavailable.
    """
    ruff_bin = shutil.which("ruff")
    cmd = [ruff_bin, "--version"] if ruff_bin else [sys.executable, "-m", "ruff", "--version"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def run_static_analysis(repo_path: str | Path) -> list[Finding]:
    """
    Executes static analysis across supported languages:
    - Python: Ruff linter & security checks
    - JavaScript / TypeScript: ESLint linter & rules
    - C++ / Arduino: clang-tidy static analysis & security checks
    """
    all_findings: list[Finding] = []

    # 1. Run Python static analysis (Ruff)
    all_findings.extend(run_ruff(repo_path))

    # 2. Run JavaScript static analysis (ESLint)
    try:
        from javascript_analyzer import run_eslint
        all_findings.extend(run_eslint(repo_path))
    except ImportError:
        pass
    except Exception:
        pass

    # 3. Run TypeScript static analysis (TypeScript ESLint)
    try:
        from typescript_analyzer import run_typescript_eslint
        all_findings.extend(run_typescript_eslint(repo_path))
    except ImportError:
        pass
    except Exception:
        pass

    # 4. Run C++ / Arduino static analysis (clang-tidy)
    try:
        from cpp_analyzer import run_clang_tidy
        all_findings.extend(run_clang_tidy(repo_path))
    except ImportError:
        pass
    except Exception:
        pass

    return all_findings



# ==============================================================================
# 4. UNIT TESTS & CLI RUNNER
# ==============================================================================

class TestStaticAnalysis(unittest.TestCase):
    """Unit tests for Ruff severity mapping, availability check, and execution."""

    def test_map_ruff_severity(self) -> None:
        self.assertEqual(map_ruff_severity("E999", None), FindingSeverity.CRITICAL.value)
        self.assertEqual(map_ruff_severity("S101", None), FindingSeverity.HIGH.value)
        self.assertEqual(map_ruff_severity("F821", None), FindingSeverity.MEDIUM.value)
        self.assertEqual(map_ruff_severity("D100", None), FindingSeverity.INFO.value)

    def test_ruff_availability(self) -> None:
        # Check that is_ruff_available returns a boolean
        avail = is_ruff_available()
        self.assertIsInstance(avail, bool)

    def test_run_ruff_nonexistent_path(self) -> None:
        findings = run_ruff("non_existent_path_xyz_123")
        self.assertEqual(len(findings), 1)
        self.assertIn("does not exist", findings[0].message)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Run static analysis tools and output normalized findings as JSON."
    )
    cli.add_argument(
        "--test",
        action="store_true",
        help="Run static analysis unit tests",
    )
    cli.add_argument(
        "--check",
        action="store_true",
        help="Check if Ruff is installed and print the version.",
    )
    cli.add_argument(
        "repository_path",
        nargs="?",
        default="./test_repository",
        help="Path to repository or directory to analyze (default: ./test_repository)",
    )

    args = cli.parse_args()

    if args.test:
        print("[+] Running Static Analysis unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestStaticAnalysis)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    if args.check:
        version = get_ruff_version()
        if version:
            print(f"[PASS] Ruff is installed and ready: {version}")
            sys.exit(0)
        else:
            print("[-] Ruff is not installed or not available on PATH.")
            sys.exit(1)

    target_repo = Path(args.repository_path)

    print(f"[+] Running static analysis against: '{target_repo}'")
    results = run_static_analysis(target_repo)

    # Format findings as readable JSON
    json_output = json.dumps([f.to_dict() for f in results], indent=2)
    print(json_output)

    # Print summary statistics
    print("\n" + "=" * 50)
    print("STATIC ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Total Findings : {len(results)}")
    by_severity: dict[str, int] = {}
    for item in results:
        by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
    for sev, count in sorted(by_severity.items()):
        print(f" - {sev.upper():<10}: {count}")
    print("=" * 50)

