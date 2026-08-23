"""
cpp_analyzer.py - Clang-Tidy C++ / Arduino Static Analysis Runner & Finding Normalizer

Executes clang-tidy against C++ source files (.cpp, .cc, .cxx, .h, .hpp, .ino)
and normalizes diagnostics into the common Finding model defined in models.py.

Handles:
- Missing compilation databases (compile_commands.json) with automated fallback flags.
- Arduino-style C++ (.ino) projects.
- Missing clang-tidy installation gracefully without crashing.
- Per-file error isolation (failure in one file does not halt repository scanning).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Optional
import unittest

from models import Finding, FindingCategory, FindingSeverity, relativize_path


logger = logging.getLogger("cpp_analyzer")


# ==============================================================================
# 1. CONSTANTS & SEVERITY MAPPING
# ==============================================================================

CPP_EXTENSIONS = {".cpp", ".cxx", ".cc", ".c", ".hpp", ".h", ".hh", ".hxx", ".ino"}

# Severity normalization
CLANG_TIDY_SEVERITY_MAP: dict[str, str] = {
    "error": FindingSeverity.HIGH.value,
    "fatal error": FindingSeverity.CRITICAL.value,
    "warning": FindingSeverity.MEDIUM.value,
    "note": FindingSeverity.INFO.value,
    "remark": FindingSeverity.INFO.value,
}

# Rule prefixes classified as Security vs general Static Analysis
SECURITY_CHECK_PREFIXES = (
    "cert-",
    "bugprone-",
    "clang-analyzer-security",
    "clang-analyzer-cplusplus",
    "clang-analyzer-core.nulldereference",
    "clang-analyzer-core.uninitialized",
    "clang-analyzer-unix",
    "cppcoreguidelines-avoid-goto",
    "cppcoreguidelines-pro-bounds",
    "cppcoreguidelines-pro-type-cstyle-cast",
    "misc-use-after-move",
)


def _infer_category_from_check(check_name: Optional[str]) -> str:
    """Infers finding category (security vs static-analysis) from clang-tidy check name."""
    if not check_name:
        return "static-analysis"
    check_lower = check_name.lower()
    if any(check_lower.startswith(prefix) or prefix in check_lower for prefix in SECURITY_CHECK_PREFIXES):
        return FindingCategory.SECURITY.value
    return "static-analysis"


# ==============================================================================
# 2. STRUCTURED DIAGNOSTIC PARSER
# ==============================================================================

# Regex matching standard Clang / Clang-Tidy diagnostic lines:
# <file>:<line>:<col>: <severity>: <message> [<check-name>]
DIAGNOSTIC_LINE_PATTERN = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s+(?P<severity>error|fatal error|warning|note|remark):\s+(?P<message>.+?)(?:\s+\[(?P<check>[a-zA-Z0-9_\-\.\,\:]+)\])?$",
    re.IGNORECASE,
)


def parse_clang_tidy_output(
    raw_output: str,
    repo_base_path: Optional[Path] = None,
) -> list[Finding]:
    """
    Parses clang-tidy standard output into structured Finding models.
    Captures file, coordinates, severity, rule ID, message, and evidence.
    """
    if not raw_output or not raw_output.strip():
        return []

    findings: list[Finding] = []
    lines = raw_output.splitlines()

    for line in lines:
        match = DIAGNOSTIC_LINE_PATTERN.match(line.strip())
        if not match:
            continue

        raw_file = match.group("file").strip()
        start_line = int(match.group("line"))
        col = int(match.group("col"))
        raw_sev = match.group("severity").lower()
        message = match.group("message").strip()
        check_name = match.group("check") or "clang-diagnostic"

        # Ignore standalone compilation summary notes if they don't point to code issues
        if raw_sev == "note" and not check_name.startswith("clang-analyzer") and not check_name.startswith("readability"):
            # If it's a supplementary note without a check name, skip or attach as metadata
            continue

        normalized_file = relativize_path(raw_file, repo_base_path)
        normalized_severity = CLANG_TIDY_SEVERITY_MAP.get(raw_sev, FindingSeverity.MEDIUM.value)
        category = _infer_category_from_check(check_name)

        # Attempt to read exact source evidence line if file is accessible
        evidence: Optional[str] = None
        target_file_p = Path(raw_file)
        if not target_file_p.is_file() and repo_base_path:
            target_file_p = repo_base_path / normalized_file

        if target_file_p.is_file():
            try:
                src_lines = target_file_p.read_text(encoding="utf-8", errors="replace").splitlines()
                if 1 <= start_line <= len(src_lines):
                    evidence = src_lines[start_line - 1].strip()
            except Exception:
                pass

        metadata: dict[str, Any] = {
            "column": col,
            "raw_severity": raw_sev,
            "check_name": check_name,
        }

        finding = Finding(
            tool="clang-tidy",
            category=category,
            severity=normalized_severity,
            file=normalized_file,
            start_line=start_line,
            end_line=start_line,
            rule_id=check_name,
            message=message,
            evidence=evidence,
            confidence=1.0,
            metadata=metadata,
        )

        findings.append(finding)

    return findings


# ==============================================================================
# 3. CLANG-TIDY SUBPROCESS EXECUTION
# ==============================================================================

def _find_compilation_database(target_dir: Path) -> Optional[Path]:
    """Looks for compile_commands.json in target directory or build subdirectories."""
    candidates = [
        target_dir / "compile_commands.json",
        target_dir / "build" / "compile_commands.json",
        target_dir / "build" / "Debug" / "compile_commands.json",
        target_dir / "build" / "Release" / "compile_commands.json",
    ]
    for c in candidates:
        if c.is_file():
            return c.parent
    return None


def run_clang_tidy_on_file(
    file_path: Path,
    repo_base: Optional[Path] = None,
    compilation_db_dir: Optional[Path] = None,
    checks: str = "*,-fuchsia-*,-llvm-header-guard",
) -> list[Finding]:
    """
    Runs clang-tidy on a single C++ or Arduino source file with fallback flags.
    """
    clang_tidy_bin = shutil.which("clang-tidy") or shutil.which("clang-tidy.exe")
    if not clang_tidy_bin:
        logger.info("clang-tidy executable not found on PATH.")
        return []

    cmd = [
        clang_tidy_bin,
        str(file_path),
        f"--checks={checks}",
        "--quiet",
    ]

    if compilation_db_dir:
        cmd.append(f"-p={compilation_db_dir}")
    else:
        # Fallback compiler flags when compile_commands.json is absent
        # Supports standard modern C++ and Arduino-style conventions
        cmd.extend([
            "--",
            "-std=c++17",
            "-I.",
            "-Iinclude",
            "-DARDUINO=10800",
            "-D__AVR__",
            "-D__AVR_ATmega328P__",
            "-w",  # Suppress compiler header warnings so clang-tidy checks stand out
        ])
        if file_path.suffix.lower() == ".ino":
            cmd.extend(["-x", "c++"])

    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(repo_base or file_path.parent),
            timeout=60,
        )
        return parse_clang_tidy_output(process.stdout, repo_base_path=repo_base)
    except subprocess.TimeoutExpired:
        logger.warning(f"clang-tidy timed out on file: {file_path}")
    except Exception as exc:
        logger.warning(f"Error running clang-tidy on {file_path}: {exc}")

    return []


def run_clang_tidy(
    repo_path: str | Path,
    checks: str = "*,-fuchsia-*,-llvm-header-guard",
) -> list[Finding]:
    """
    Runs clang-tidy across all C++ and Arduino source files in a repository.

    Requirements:
    1. Returns normalized list[Finding].
    2. Sets tool = "clang-tidy", category = "static-analysis".
    3. Handles missing compilation database gracefully.
    4. Handles missing clang-tidy executable gracefully without crashing.
    5. Isolates per-file failures so one broken file does not halt analysis.
    """
    target = Path(repo_path).resolve()
    if not target.exists():
        logger.warning(f"Target repository path does not exist: {target}")
        return []

    clang_tidy_bin = shutil.which("clang-tidy") or shutil.which("clang-tidy.exe")
    if not clang_tidy_bin:
        logger.info("clang-tidy executable not found on PATH.")
        return []

    comp_db = _find_compilation_database(target if target.is_dir() else target.parent)

    all_findings: list[Finding] = []

    if target.is_file():
        if target.suffix.lower() in CPP_EXTENSIONS:
            return run_clang_tidy_on_file(
                target,
                repo_base=target.parent,
                compilation_db_dir=comp_db,
                checks=checks,
            )
        return []

    # Iterate over all C++ and Arduino files in repository
    for root, _, files in os.walk(target):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in CPP_EXTENSIONS:
                try:
                    file_findings = run_clang_tidy_on_file(
                        p,
                        repo_base=target,
                        compilation_db_dir=comp_db,
                        checks=checks,
                    )
                    all_findings.extend(file_findings)
                except Exception as file_err:
                    # Isolated error handling: continue scanning other files
                    logger.warning(f"Skipping {p} due to unexpected error: {file_err}")
                    continue

    return all_findings


# ==============================================================================
# 4. REFERENCE C++ TEST SAMPLES & UNIT TESTS
# ==============================================================================

SAMPLE_VULNERABLE_CPP = """
#include <iostream>
#include <cstring>

void processBuffer(const char* input) {
    char dest[16];
    // Insecure buffer copy without boundary check
    strcpy(dest, input);
    std::cout << "Buffer: " << dest << std::endl;
}

int calculateTotal(int count) {
    int total; // Uninitialized variable
    for (int i = 0; i < count; i++) {
        total += i;
    }
    return total;
}
"""

SAMPLE_ARDUINO_CPP = """
#include <Arduino.h>

void setup() {
    Serial.begin(9600);
}

void loop() {
    char* ptr = nullptr;
    if (analogRead(A0) > 500) {
        *ptr = 'X'; // Null pointer dereference
    }
    delay(100);
}
"""


class TestCppAnalyzer(unittest.TestCase):
    """Unit test suite for clang-tidy diagnostic parsing and normalization."""

    def setUp(self) -> None:
        self.sample_clang_tidy_raw = """
/home/user/repo/src/buffer.cpp:8:5: warning: 'strcpy' is deprecated: This function is dangerous [clang-diagnostic-deprecated-declarations]
    strcpy(dest, input);
    ^
/home/user/repo/src/buffer.cpp:13:5: warning: variable 'total' is uninitialized when used here [clang-analyzer-core.uninitialized.UndefReturn]
    total += i;
    ^
/home/user/repo/src/buffer.cpp:18:10: error: use of undeclared identifier 'missingVar' [clang-diagnostic-error]
    return missingVar;
           ^
/home/user/repo/src/lock.ino:9:9: warning: Dereference of null pointer [clang-analyzer-core.NullDereference]
        *ptr = 'X';
        ^
"""

    def test_parse_clang_tidy_output(self) -> None:
        """Verifies parsing of standard clang-tidy output into normalized Finding objects."""
        findings = parse_clang_tidy_output(
            self.sample_clang_tidy_raw,
            repo_base_path=Path("/home/user/repo"),
        )

        self.assertEqual(len(findings), 4)

        # Finding 1: strcpy deprecation
        f1 = findings[0]
        self.assertEqual(f1.tool, "clang-tidy")
        self.assertEqual(f1.file, "src/buffer.cpp")
        self.assertEqual(f1.start_line, 8)
        self.assertEqual(f1.severity, FindingSeverity.MEDIUM.value)
        self.assertEqual(f1.rule_id, "clang-diagnostic-deprecated-declarations")
        self.assertEqual(f1.category, "static-analysis")

        # Finding 2: uninitialized variable (Security / bugprone category)
        f2 = findings[1]
        self.assertEqual(f2.start_line, 13)
        self.assertEqual(f2.severity, FindingSeverity.MEDIUM.value)
        self.assertEqual(f2.rule_id, "clang-analyzer-core.uninitialized.UndefReturn")
        self.assertEqual(f2.category, FindingCategory.SECURITY.value)

        # Finding 3: error severity mapping
        f3 = findings[2]
        self.assertEqual(f3.severity, FindingSeverity.HIGH.value)
        self.assertEqual(f3.rule_id, "clang-diagnostic-error")

        # Finding 4: Arduino .ino file parsing
        f4 = findings[3]
        self.assertEqual(f4.file, "src/lock.ino")
        self.assertEqual(f4.start_line, 9)
        self.assertEqual(f4.rule_id, "clang-analyzer-core.NullDereference")
        self.assertEqual(f4.category, FindingCategory.SECURITY.value)

    def test_empty_output_handling(self) -> None:
        """Verifies that empty output produces zero findings without errors."""
        self.assertEqual(parse_clang_tidy_output(""), [])
        self.assertEqual(parse_clang_tidy_output("   \n\n  "), [])

    def test_nonexistent_repository_path(self) -> None:
        """Verifies that non-existent target returns empty list gracefully."""
        self.assertEqual(run_clang_tidy("non_existent_dir_12345"), [])


# ==============================================================================
# 5. CLI RUNNER
# ==============================================================================

if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Run clang-tidy against C++/Arduino code and normalize findings into Finding objects."
    )
    cli.add_argument(
        "repository",
        nargs="?",
        default=".",
        help="Path to C++/Arduino repository or source file (default: .)",
    )
    cli.add_argument(
        "--checks",
        default="*,-fuchsia-*,-llvm-header-guard",
        help="Clang-tidy check filter (default: *,-fuchsia-*,-llvm-header-guard)",
    )
    cli.add_argument(
        "--json",
        action="store_true",
        help="Output findings as JSON",
    )
    cli.add_argument(
        "--test",
        action="store_true",
        help="Run unit test suite",
    )

    args = cli.parse_args()

    if args.test:
        print("[+] Running C++ Analyzer (clang-tidy) unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestCppAnalyzer)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    target_path = Path(args.repository).resolve()
    print(f"[+] Running clang-tidy analysis against: '{target_path}'")

    results = run_clang_tidy(target_path, checks=args.checks)

    if args.json:
        print(json.dumps([f.to_dict() for f in results], indent=2))
    else:
        print(f"\n[+] Total clang-tidy findings: {len(results)}")
        for f in results:
            print(f"  [{f.severity.upper()}] {f.rule_id} at {f.file}:{f.start_line} - {f.message}")
