"""
semgrep_analyzer.py - Semgrep Semantic & Security Analysis Layer for AI Code Verification SaaS

Executes Semgrep against code repositories across multiple languages, requests structured
JSON output, and normalizes findings into the common Finding model defined in models.py.

Designed to run resiliently: gracefully handles missing installations, subprocess timeouts,
syntax failures, and malformed JSON without disrupting the overall verification pipeline.
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
# 1. NORMALIZATION HELPERS: SEVERITY, CATEGORY, & CONFIDENCE
# ==============================================================================

def map_semgrep_severity(raw_severity: Optional[str]) -> str:
    """
    Maps Semgrep's severity levels to normalized FindingSeverity enum values.

    Semgrep levels:
    - CRITICAL / BLOCKER -> 'critical'
    - ERROR / HIGH       -> 'high'
    - WARNING / MEDIUM   -> 'medium'
    - LOW                -> 'low'
    - INFO / EXPERIMENT  -> 'info'
    """
    if not raw_severity:
        return FindingSeverity.MEDIUM.value

    sev_upper = raw_severity.strip().upper()
    if sev_upper in ("CRITICAL", "BLOCKER"):
        return FindingSeverity.CRITICAL.value
    elif sev_upper in ("ERROR", "HIGH"):
        return FindingSeverity.HIGH.value
    elif sev_upper in ("WARNING", "MEDIUM"):
        return FindingSeverity.MEDIUM.value
    elif sev_upper in ("LOW",):
        return FindingSeverity.LOW.value
    elif sev_upper in ("INFO", "EXPERIMENT", "AUDIT"):
        return FindingSeverity.INFO.value

    return FindingSeverity.MEDIUM.value


def map_semgrep_category(metadata_category: Optional[str], rule_id: str) -> str:
    """
    Infers the finding category from Semgrep rule metadata and rule identifier naming.

    Rules:
    - Metadata 'security' or rule ID containing security/crypto/owasp/cwe -> 'security'
    - Metadata 'correctness', 'logic', 'bug' -> 'logic'
    - Metadata 'maintainability', 'best-practice', 'lint' -> 'lint'
    - Metadata 'style', 'formatting' -> 'style'
    - Metadata 'dependency', 'dependencies' -> 'dependency'
    - Metadata 'domain', 'rfid' -> 'domain'
    - Defaults to 'security' for security-related rules, otherwise 'other'.
    """
    cat_lower = metadata_category.strip().lower() if metadata_category else ""
    rule_lower = rule_id.lower()

    if cat_lower in ("domain", "rfid") or "rfid" in rule_lower:
        return FindingCategory.DOMAIN.value

    # Explicit or inferred security findings
    if cat_lower == "security" or any(
        kw in rule_lower
        for kw in (
            "security", "vuln", "cwe", "owasp", "injection", "crypto",
            "xss", "rce", "sqli", "deserialization", "jwt", "ssrf", "auth"
        )
    ):
        return FindingCategory.SECURITY.value

    if cat_lower in ("lint", "maintainability", "best-practice"):
        return FindingCategory.LINT.value
    elif cat_lower in ("correctness", "logic", "bug"):
        return FindingCategory.LOGIC.value
    elif cat_lower in ("style", "formatting"):
        return FindingCategory.STYLE.value
    elif cat_lower in ("dependency", "dependencies", "supply-chain"):
        return FindingCategory.DEPENDENCY.value
        return FindingCategory.DEPENDENCY.value
    elif cat_lower in ("domain", "rfid"):
        return FindingCategory.DOMAIN.value

    return FindingCategory.OTHER.value


def map_semgrep_confidence(raw_confidence: Any) -> Optional[float]:
    """
    Normalizes Semgrep's confidence score into a float between 0.0 and 1.0.

    Semgrep often outputs string confidence tags:
    - 'HIGH' / 'CERTAIN'   -> 0.9
    - 'MEDIUM' / 'LIKELY'  -> 0.6
    - 'LOW' / 'POSSIBLE'   -> 0.3
    """
    if raw_confidence is None:
        return None

    if isinstance(raw_confidence, (int, float)):
        return max(0.0, min(1.0, float(raw_confidence)))

    if isinstance(raw_confidence, str):
        c_upper = raw_confidence.strip().upper()
        if c_upper in ("HIGH", "CERTAIN"):
            return 0.9
        elif c_upper in ("MEDIUM", "LIKELY"):
            return 0.6
        elif c_upper in ("LOW", "POSSIBLE"):
            return 0.3

    return None


# ==============================================================================
# 2. SEMGREP PROCESS EXECUTION & PARSING
# ==============================================================================

def _get_semgrep_command(target_path: Path, config: str = "auto") -> list[str]:
    """
    Constructs the Semgrep CLI execution command.
    Uses 'semgrep scan --config <config> --json' to ensure clean JSON output.
    """
    semgrep_bin = shutil.which("semgrep")
    if semgrep_bin:
        return [
            semgrep_bin,
            "scan",
            "--config",
            config,
            "--json",
            "--quiet",
            str(target_path),
        ]
    return [
        sys.executable,
        "-m",
        "semgrep",
        "scan",
        "--config",
        config,
        "--json",
        "--quiet",
        str(target_path),
    ]


def run_semgrep(
    repo_path: str | Path,
    config: str = "auto",
    timeout_seconds: int = 180,
) -> list[Finding]:
    """
    Executes Semgrep static analysis on a codebase and returns normalized Findings.

    Parameters:
        repo_path: Path to the target directory or source file.
        config: Semgrep rule configuration (default: 'auto' for Semgrep registry default rules).
        timeout_seconds: Process timeout in seconds (default: 180).

    Features:
    - Uses subprocess and pure JSON deserialization (no regex parsing).
    - Injects CWE, OWASP, fix suggestions, and rule references into Finding.metadata.
    - Captures exact file lines and source evidence snippets.
    - Completely safe: never raises unhandled exceptions or halts the verification pipeline.
    """
    target = Path(repo_path).resolve()
    findings: list[Finding] = []

    if not target.exists():
        return [
            Finding(
                tool="semgrep",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.HIGH.value,
                message=f"Target repository path does not exist: {target}",
            )
        ]

    cmd = _get_semgrep_command(target, config=config)

    try:
        # Semgrep returns exit code 0 (no issues), 1 (issues found), or 2+ (error).
        # We do not raise an exception on non-zero exit codes.
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return [
            Finding(
                tool="semgrep",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.INFO.value,
                message="Semgrep CLI is not installed or not available on system PATH.",
            )
        ]
    except subprocess.TimeoutExpired:
        return [
            Finding(
                tool="semgrep",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.HIGH.value,
                message=f"Semgrep analysis timed out after {timeout_seconds}s on path: {target}",
            )
        ]
    except Exception as e:
        return [
            Finding(
                tool="semgrep",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.HIGH.value,
                message=f"Unexpected error executing Semgrep: {str(e)}",
            )
        ]

    stdout_raw = process.stdout.strip()
    if not stdout_raw:
        # Clean repository or no findings
        return []

    try:
        raw_data = json.loads(stdout_raw)
    except json.JSONDecodeError as err:
        return [
            Finding(
                tool="semgrep",
                category=FindingCategory.OTHER.value,
                severity=FindingSeverity.HIGH.value,
                message=f"Failed to parse Semgrep JSON output: {str(err)}",
                evidence=stdout_raw[:250],
            )
        ]

    if not isinstance(raw_data, dict):
        return []

    results_list = raw_data.get("results", [])
    if not isinstance(results_list, list):
        return []

    # Transform each Semgrep result into a normalized Finding
    for item in results_list:
        if not isinstance(item, dict):
            continue

        rule_id = item.get("check_id") or "unknown-rule"
        file_path = item.get("path")

        # Extract line coordinates (1-indexed)
        start_coord = item.get("start") or {}
        end_coord = item.get("end") or {}
        start_line = start_coord.get("line")
        end_line = end_coord.get("line") or start_line

        # Extract extra diagnostics
        extra = item.get("extra") or {}
        message_str = extra.get("message", "").strip()
        metadata_dict = extra.get("metadata") or {}

        # Severity, category, and confidence
        raw_severity = extra.get("severity")
        raw_category = metadata_dict.get("category")
        raw_confidence = metadata_dict.get("confidence")

        severity = map_semgrep_severity(raw_severity)
        category = map_semgrep_category(raw_category, rule_id)
        confidence = map_semgrep_confidence(raw_confidence)

        # Code snippet evidence (Semgrep provides 'lines' string)
        evidence_snippet = extra.get("lines")
        if not evidence_snippet and file_path and start_line:
            evidence_snippet = extract_source_evidence(file_path, start_line, end_line)

        # Build clean metadata payload
        finding_meta: dict[str, Any] = {}
        if "cwe" in metadata_dict:
            finding_meta["cwe"] = metadata_dict["cwe"]
        if "owasp" in metadata_dict:
            finding_meta["owasp"] = metadata_dict["owasp"]
        if "references" in metadata_dict:
            finding_meta["references"] = metadata_dict["references"]
        if "fix" in extra:
            finding_meta["fix"] = extra["fix"]
        if "impact" in metadata_dict:
            finding_meta["impact"] = metadata_dict["impact"]
        if "likelihood" in metadata_dict:
            finding_meta["likelihood"] = metadata_dict["likelihood"]

        finding = Finding(
            tool="semgrep",
            category=category,
            severity=severity,
            file=file_path,
            start_line=start_line,
            end_line=end_line,
            rule_id=rule_id,
            message=message_str,
            evidence=evidence_snippet,
            confidence=confidence,
            metadata=finding_meta,
        )
        findings.append(finding)

    return findings


# ==============================================================================
# 3. UNIT TESTS & CLI DEMONSTRATION RUNNER
# ==============================================================================

class TestSemgrepAnalyzer(unittest.TestCase):
    """Unit tests for Semgrep severity/category mapping and execution handling."""

    def test_map_semgrep_severity(self) -> None:
        self.assertEqual(map_semgrep_severity("ERROR"), FindingSeverity.HIGH.value)
        self.assertEqual(map_semgrep_severity("WARNING"), FindingSeverity.MEDIUM.value)
        self.assertEqual(map_semgrep_severity("INFO"), FindingSeverity.INFO.value)

    def test_map_semgrep_category(self) -> None:
        self.assertEqual(map_semgrep_category("security", "custom-rule"), FindingCategory.SECURITY.value)
        self.assertEqual(map_semgrep_category(None, "rules.rfid.RFID-001"), FindingCategory.DOMAIN.value)

    def test_nonexistent_repository_path(self) -> None:
        findings = run_semgrep("non_existent_folder_xyz_999")
        self.assertEqual(len(findings), 1)
        self.assertIn("does not exist", findings[0].message)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Run Semgrep semantic code analysis and print normalized findings as JSON."
    )
    cli.add_argument(
        "--test",
        action="store_true",
        help="Run semgrep analyzer unit tests",
    )
    cli.add_argument(
        "repository_path",
        nargs="?",
        default="./test_repository",
        help="Path to repository or directory to scan (default: ./test_repository)",
    )
    cli.add_argument(
        "--config",
        default="auto",
        help="Semgrep ruleset configuration (default: auto)",
    )

    args = cli.parse_args()

    if args.test:
        print("[+] Running Semgrep Analyzer unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestSemgrepAnalyzer)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    target_repo = Path(args.repository_path)

    print(f"[+] Running Semgrep analysis against: '{target_repo}' (config: {args.config})")
    semgrep_results = run_semgrep(target_repo, config=args.config)

    # Format findings as readable JSON
    json_output = json.dumps([f.to_dict() for f in semgrep_results], indent=2)
    print(json_output)

    # Print summary statistics
    print("\n" + "=" * 50)
    print("SEMGREP ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Total Findings : {len(semgrep_results)}")
    by_severity: dict[str, int] = {}
    for item in semgrep_results:
        by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
    for sev, count in sorted(by_severity.items()):
        print(f" - {sev.upper():<10}: {count}")
    print("=" * 50)

