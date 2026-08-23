"""
javascript_analyzer.py - ESLint Static Analysis Runner & Finding Normalizer

Executes ESLint against JavaScript/TypeScript repositories and normalizes results
into the common Finding dataclass defined in models.py.

Supported file extensions: .js, .jsx, .mjs, .cjs, .ts, .tsx
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Optional
import unittest

from models import Finding, FindingCategory, FindingSeverity, relativize_path


logger = logging.getLogger("javascript_analyzer")


# ==============================================================================
# 1. ESLINT SEVERITY & CATEGORY MAPPINGS
# ==============================================================================

# ESLint severity definitions:
# 0 = off / info
# 1 = warning -> low
# 2 = error -> high
ESLINT_SEVERITY_MAP: dict[int, str] = {
    0: FindingSeverity.INFO.value,
    1: FindingSeverity.LOW.value,
    2: FindingSeverity.HIGH.value,
}

# Common ESLint security plugin rule prefixes
SECURITY_RULE_PREFIXES = (
    "security/",
    "no-eval",
    "no-implied-eval",
    "no-new-func",
    "detect-",
    "xss",
    "csrf",
    "sql-injection",
)


def _infer_category_from_rule(rule_id: Optional[str]) -> str:
    """Infers finding category (security vs lint) from rule name."""
    if not rule_id:
        return FindingCategory.LINT.value
    rule_lower = rule_id.lower()
    if any(prefix in rule_lower for prefix in SECURITY_RULE_PREFIXES):
        return FindingCategory.SECURITY.value
    return FindingCategory.LINT.value


# ==============================================================================
# 2. JSON NORMALIZATION ENGINE
# ==============================================================================

def parse_eslint_json(
    raw_json: str,
    repo_base_path: Optional[Path] = None,
) -> list[Finding]:
    """
    Parses ESLint's JSON output format and converts every message into a Finding object.
    Does NOT use regular expressions to parse tool output.
    """
    if not raw_json or not raw_json.strip():
        return []

    try:
        report_data = json.loads(raw_json)
    except json.JSONDecodeError as err:
        logger.warning(f"Failed to parse ESLint JSON output: {err}")
        return []

    if not isinstance(report_data, list):
        logger.warning("Unexpected ESLint JSON root structure; expected a list.")
        return []

    findings: list[Finding] = []

    for file_entry in report_data:
        if not isinstance(file_entry, dict):
            continue

        raw_file_path = file_entry.get("filePath", "")
        file_source = file_entry.get("source", "")
        source_lines = file_source.splitlines() if file_source else []

        normalized_file = relativize_path(raw_file_path, repo_base_path)

        messages = file_entry.get("messages", [])
        if not isinstance(messages, list):
            continue

        for msg in messages:
            if not isinstance(msg, dict):
                continue

            rule_id = msg.get("ruleId") or "eslint-syntax-error"
            message_text = msg.get("message", "ESLint diagnostic issue")
            raw_severity = msg.get("severity", 2)
            normalized_severity = ESLINT_SEVERITY_MAP.get(raw_severity, FindingSeverity.MEDIUM.value)

            start_line = msg.get("line")
            end_line = msg.get("endLine") or start_line
            start_col = msg.get("column")
            end_col = msg.get("endColumn")

            # Extract evidence line if available
            evidence: Optional[str] = None
            if source_lines and start_line and 1 <= start_line <= len(source_lines):
                evidence = source_lines[start_line - 1].strip()
            elif "source" in msg:
                evidence = str(msg["source"]).strip()

            category = _infer_category_from_rule(rule_id)

            metadata: dict[str, Any] = {
                "column": start_col,
                "end_column": end_col,
                "node_type": msg.get("nodeType"),
                "message_id": msg.get("messageId"),
                "fatal": msg.get("fatal", False),
            }

            if "fix" in msg:
                metadata["fixable"] = True
                metadata["fix"] = msg["fix"]

            finding = Finding(
                tool="eslint",
                category=category,
                severity=normalized_severity,
                file=normalized_file,
                start_line=start_line,
                end_line=end_line,
                rule_id=rule_id,
                message=message_text,
                evidence=evidence,
                confidence=1.0,
                metadata=metadata,
            )

            findings.append(finding)

    return findings


# ==============================================================================
# 3. SUBPROCESS EXECUTION
# ==============================================================================

def run_eslint(
    repo_path: str | Path,
    config: Optional[str | Path] = None,
    extensions: Optional[list[str]] = None,
) -> list[Finding]:
    """
    Executes ESLint against a JavaScript repository/file and returns normalized findings.
    
    Handles:
    - ESLint not installed
    - Invalid repository paths
    - Non-zero process exit codes (ESLint returns 1 when lint errors are found)
    - Malformed JSON
    """
    target = Path(repo_path).resolve()

    if not target.exists():
        logger.warning(f"Target path does not exist: {target}")
        return []

    # Locate ESLint executable
    eslint_bin = shutil.which("eslint") or shutil.which("eslint.cmd")
    npx_bin = shutil.which("npx") or shutil.which("npx.cmd")

    cmd: list[str] = []
    if eslint_bin:
        cmd.append(eslint_bin)
    elif npx_bin:
        cmd.extend([npx_bin, "--no-install", "eslint"])
    else:
        logger.info("Neither 'eslint' nor 'npx' was found on PATH. Skipping ESLint execution.")
        return []

    cmd.append(str(target))
    cmd.extend(["--format", "json"])

    if config:
        cfg_path = Path(config).resolve()
        if cfg_path.exists():
            cmd.extend(["--config", str(cfg_path)])

    if target.is_dir():
        ext_list = extensions or [".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"]
        cmd.extend(["--ext", ",".join(ext_list)])

    try:
        # ESLint returns exit code 1 when lint errors are found, code 0 when clean.
        # Exit code 2 usually represents configuration or fatal syntax errors.
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(target if target.is_dir() else target.parent),
            timeout=120,
        )

        stdout = process.stdout.strip()
        stderr = process.stderr.strip()

        if stdout:
            base_dir = target if target.is_dir() else target.parent
            return parse_eslint_json(stdout, repo_base_path=base_dir)

        if process.returncode not in (0, 1) and stderr:
            logger.warning(f"ESLint execution error (code {process.returncode}): {stderr}")

    except subprocess.TimeoutExpired:
        logger.warning(f"ESLint timed out while scanning {target}")
    except FileNotFoundError:
        logger.info("ESLint executable not found.")
    except Exception as exc:
        logger.warning(f"Unexpected error running ESLint: {exc}")

    return []


# ==============================================================================
# 4. UNIT TESTS
# ==============================================================================

class TestJavaScriptAnalyzer(unittest.TestCase):
    """Unit test suite for ESLint output parsing and normalization."""

    def setUp(self) -> None:
        self.sample_eslint_json = json.dumps([
            {
                "filePath": "/home/user/project/src/auth.js",
                "messages": [
                    {
                        "ruleId": "no-unused-vars",
                        "severity": 2,
                        "message": "'authToken' is assigned a value but never used.",
                        "line": 12,
                        "column": 9,
                        "nodeType": "Identifier",
                        "messageId": "unusedVar",
                        "endLine": 12,
                        "endColumn": 18,
                    },
                    {
                        "ruleId": "no-eval",
                        "severity": 2,
                        "message": "eval can be harmful.",
                        "line": 45,
                        "column": 5,
                        "nodeType": "CallExpression",
                        "endLine": 45,
                        "endColumn": 25,
                    },
                    {
                        "ruleId": "prefer-const",
                        "severity": 1,
                        "message": "'port' is never reassigned. Use 'const' instead.",
                        "line": 5,
                        "column": 5,
                        "nodeType": "Identifier",
                        "endLine": 5,
                        "endColumn": 9,
                        "fix": {"range": [40, 43], "text": "const"},
                    },
                ],
                "errorCount": 2,
                "warningCount": 1,
                "source": "let port = 8080;\n\nfunction login() {\n    const authToken = 'xyz';\n    eval('console.log(1)');\n}",
            }
        ])

    def test_parse_eslint_json_structure(self) -> None:
        """Verifies parsing of ESLint messages into Finding models."""
        findings = parse_eslint_json(self.sample_eslint_json, repo_base_path=Path("/home/user/project"))

        self.assertEqual(len(findings), 3)

        # Finding 1: no-unused-vars (Severity 2 -> High, Lint)
        f1 = findings[0]
        self.assertEqual(f1.tool, "eslint")
        self.assertEqual(f1.rule_id, "no-unused-vars")
        self.assertEqual(f1.severity, FindingSeverity.HIGH.value)
        self.assertEqual(f1.category, FindingCategory.LINT.value)
        self.assertEqual(f1.start_line, 12)
        self.assertEqual(f1.end_line, 12)
        self.assertEqual(f1.file, "src/auth.js")

        # Finding 2: no-eval (Security category inference)
        f2 = findings[1]
        self.assertEqual(f2.rule_id, "no-eval")
        self.assertEqual(f2.category, FindingCategory.SECURITY.value)
        self.assertEqual(f2.severity, FindingSeverity.HIGH.value)

        # Finding 3: prefer-const (Severity 1 -> Low, Fixable metadata)
        f3 = findings[2]
        self.assertEqual(f3.rule_id, "prefer-const")
        self.assertEqual(f3.severity, FindingSeverity.LOW.value)
        self.assertTrue(f3.metadata.get("fixable"))

    def test_malformed_json_handling(self) -> None:
        """Verifies that corrupted or empty JSON returns an empty list without crashing."""
        self.assertEqual(parse_eslint_json(""), [])
        self.assertEqual(parse_eslint_json("{ invalid json"), [])
        self.assertEqual(parse_eslint_json('{"errorCount": 0}'), [])

    def test_nonexistent_repository_path(self) -> None:
        """Verifies that invalid repository paths return empty list gracefully."""
        findings = run_eslint("non_existent_folder_xyz_123")
        self.assertEqual(findings, [])


# ==============================================================================
# 5. CLI RUNNER
# ==============================================================================

if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Run ESLint against a JavaScript repository and normalize results into Finding objects."
    )
    cli.add_argument(
        "repository",
        nargs="?",
        default=".",
        help="Path to JavaScript repository or source file (default: .)",
    )
    cli.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to custom ESLint configuration file (.eslintrc.js, eslint.config.js, etc.)",
    )
    cli.add_argument(
        "--json",
        action="store_true",
        help="Output normalized findings as JSON",
    )
    cli.add_argument(
        "--test",
        action="store_true",
        help="Run unit test suite",
    )

    args = cli.parse_args()

    if args.test:
        print("[+] Running JavaScript Analyzer (ESLint) unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestJavaScriptAnalyzer)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    target_path = Path(args.repository).resolve()
    print(f"[+] Scanning JavaScript target: '{target_path}'")

    results = run_eslint(target_path, config=args.config)

    if args.json:
        print(json.dumps([f.to_dict() for f in results], indent=2))
    else:
        print(f"\n[+] Total ESLint findings: {len(results)}")
        for f in results:
            print(f"  [{f.severity.upper()}] {f.rule_id} at {f.file}:{f.start_line} - {f.message}")
