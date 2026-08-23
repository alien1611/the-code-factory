"""
typescript_analyzer.py - TypeScript ESLint Analysis Layer for AI Code Verification SaaS

Executes ESLint configured with TypeScript ESLint against TypeScript source code (.ts, .tsx, .d.ts, .mts, .cts)
and normalizes diagnostics into the common Finding dataclass defined in models.py.

Designed for resilience:
- Uses subprocess to request machine-readable JSON output.
- Avoids regex for JSON parsing.
- Extracts exact source code lines for evidence.
- Gracefully handles missing ESLint installations, subprocess timeouts, and missing configs.
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

from models import Finding, FindingCategory, FindingSeverity, extract_source_evidence, relativize_path


logger = logging.getLogger("typescript_analyzer")

# Supported TypeScript file extensions
TYPESCRIPT_EXTENSIONS = [".ts", ".tsx", ".mts", ".cts", ".d.ts"]

# ESLint severity mapping into normalized FindingSeverity levels
# 0 = off/info, 1 = warning (low), 2 = error (high)
ESLINT_TS_SEVERITY_MAP: dict[int, str] = {
    0: FindingSeverity.INFO.value,
    1: FindingSeverity.LOW.value,
    2: FindingSeverity.HIGH.value,
}

# TypeScript ESLint rules classified as Security / Type-Safety Flaws
TS_SECURITY_RULES = (
    "@typescript-eslint/no-implied-eval",
    "@typescript-eslint/no-unsafe-assignment",
    "@typescript-eslint/no-unsafe-call",
    "@typescript-eslint/no-unsafe-member-access",
    "@typescript-eslint/no-unsafe-return",
    "@typescript-eslint/no-unsafe-argument",
    "@typescript-eslint/no-base-to-string",
    "@typescript-eslint/restrict-template-expressions",
    "security/",
    "no-eval",
    "no-implied-eval",
)


def _infer_category_from_ts_rule(rule_id: Optional[str]) -> str:
    """
    Infers finding category (security vs lint) from TypeScript ESLint rule identifier.
    Defaults to 'lint' as requested.
    """
    if not rule_id:
        return FindingCategory.LINT.value
    rule_lower = rule_id.lower()
    if any(prefix in rule_lower for prefix in TS_SECURITY_RULES):
        return FindingCategory.SECURITY.value
    return FindingCategory.LINT.value


# ==============================================================================
# 1. JSON NORMALIZATION ENGINE
# ==============================================================================

def parse_typescript_eslint_json(
    raw_json: str,
    repo_base_path: Optional[Path] = None,
) -> list[Finding]:
    """
    Parses ESLint's JSON output format into structured Finding models.
    Parses data directly using Python's json module without regex.
    """
    if not raw_json or not raw_json.strip():
        return []

    try:
        report_data = json.loads(raw_json)
    except json.JSONDecodeError as err:
        logger.warning(f"Failed to parse TypeScript ESLint JSON: {err}")
        return []

    if not isinstance(report_data, list):
        logger.warning("Unexpected ESLint JSON root structure; expected a list of file entries.")
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

            rule_id = msg.get("ruleId") or "@typescript-eslint/syntax-error"
            message_text = msg.get("message", "TypeScript ESLint diagnostic issue")
            raw_severity = msg.get("severity", 2)
            fatal = msg.get("fatal", False)

            # Map fatal/compilation syntax errors to CRITICAL, otherwise normalize 0/1/2
            if fatal:
                normalized_severity = FindingSeverity.CRITICAL.value
            else:
                normalized_severity = ESLINT_TS_SEVERITY_MAP.get(raw_severity, FindingSeverity.MEDIUM.value)

            start_line = msg.get("line")
            end_line = msg.get("endLine") or start_line
            start_col = msg.get("column")
            end_col = msg.get("endColumn")

            # Extract evidence line if available from source or disk
            evidence: Optional[str] = None
            if source_lines and start_line and 1 <= start_line <= len(source_lines):
                evidence = source_lines[start_line - 1].strip()
            elif "source" in msg:
                evidence = str(msg["source"]).strip()
            elif repo_base_path and normalized_file:
                evidence = extract_source_evidence(repo_base_path / normalized_file, start_line, end_line)

            category = _infer_category_from_ts_rule(rule_id)

            metadata: dict[str, Any] = {
                "column": start_col,
                "end_column": end_col,
                "node_type": msg.get("nodeType"),
                "message_id": msg.get("messageId"),
                "fatal": fatal,
            }

            if "fix" in msg:
                metadata["fixable"] = True
                metadata["fix"] = msg["fix"]

            finding = Finding(
                tool="eslint-typescript",
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
# 2. SUBPROCESS EXECUTION
# ==============================================================================

def run_typescript_eslint(
    repo_path: str | Path,
    config: Optional[str | Path] = None,
    extensions: Optional[list[str]] = None,
) -> list[Finding]:
    """
    Executes ESLint configured with TypeScript ESLint against a TypeScript repository.

    Requirements:
    1. Returns normalized list[Finding].
    2. Sets tool = "eslint-typescript", category = "lint".
    3. Handles missing ESLint executable or config gracefully.
    4. Handles process non-zero exit codes (ESLint exits with 1 on lint findings).
    5. Avoids crashes on malformed JSON.
    """
    target = Path(repo_path).resolve()

    if not target.exists():
        logger.warning(f"Target TypeScript path does not exist: {target}")
        return []

    # Locate ESLint or NPX executable
    eslint_bin = shutil.which("eslint") or shutil.which("eslint.cmd")
    npx_bin = shutil.which("npx") or shutil.which("npx.cmd")

    cmd: list[str] = []
    if eslint_bin:
        cmd.append(eslint_bin)
    elif npx_bin:
        cmd.extend([npx_bin, "--no-install", "eslint"])
    else:
        logger.info("ESLint executable not found on PATH. Skipping TypeScript analysis.")
        return []

    cmd.append(str(target))
    cmd.extend(["--format", "json"])

    # Attach TypeScript extensions when scanning directories
    ext_list = extensions or TYPESCRIPT_EXTENSIONS
    if target.is_dir():
        cmd.extend(["--ext", ",".join(ext_list)])

    if config:
        cfg_path = Path(config).resolve()
        if cfg_path.exists():
            cmd.extend(["--config", str(cfg_path)])

    try:
        # ESLint exits with code 1 when lint errors/warnings are detected (contains valid JSON)
        # Code 0 when completely clean, Code 2 on fatal configuration error
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
            return parse_typescript_eslint_json(stdout, repo_base_path=base_dir)

        if process.returncode not in (0, 1) and stderr:
            logger.warning(f"TypeScript ESLint execution notice (code {process.returncode}): {stderr}")

    except subprocess.TimeoutExpired:
        logger.warning(f"TypeScript ESLint timed out while scanning {target}")
    except FileNotFoundError:
        logger.info("ESLint executable not available.")
    except Exception as exc:
        logger.warning(f"Unexpected error running TypeScript ESLint: {exc}")

    return []


# ==============================================================================
# 3. UNIT TESTS
# ==============================================================================

class TestTypeScriptAnalyzer(unittest.TestCase):
    """Unit test suite for TypeScript ESLint output parsing and normalization."""

    def setUp(self) -> None:
        self.sample_ts_eslint_json = json.dumps([
            {
                "filePath": "/home/user/project/src/userService.ts",
                "messages": [
                    {
                        "ruleId": "@typescript-eslint/no-explicit-any",
                        "severity": 2,
                        "message": "Unexpected any. Specify a different type.",
                        "line": 15,
                        "column": 23,
                        "nodeType": "TSAnyKeyword",
                        "messageId": "unexpectedAny",
                        "endLine": 15,
                        "endColumn": 26,
                    },
                    {
                        "ruleId": "@typescript-eslint/explicit-function-return-type",
                        "severity": 1,
                        "message": "Missing return type on function.",
                        "line": 28,
                        "column": 5,
                        "nodeType": "FunctionDeclaration",
                        "endLine": 28,
                        "endColumn": 21,
                    },
                    {
                        "ruleId": "@typescript-eslint/no-implied-eval",
                        "severity": 2,
                        "message": "Implied eval in setTimeout with string argument.",
                        "line": 42,
                        "column": 5,
                        "nodeType": "CallExpression",
                        "endLine": 42,
                        "endColumn": 35,
                    },
                    {
                        "ruleId": None,
                        "fatal": True,
                        "severity": 2,
                        "message": "Parsing error: Unexpected token",
                        "line": 50,
                        "column": 1,
                    }
                ],
                "errorCount": 3,
                "warningCount": 1,
                "source": "export function processUser(data: any) {\n    return data;\n}\n",
            }
        ])

    def test_parse_typescript_eslint_json(self) -> None:
        """Verifies parsing of TypeScript ESLint diagnostics into Finding models."""
        findings = parse_typescript_eslint_json(
            self.sample_ts_eslint_json,
            repo_base_path=Path("/home/user/project"),
        )

        self.assertEqual(len(findings), 4)

        # Finding 1: @typescript-eslint/no-explicit-any (Severity 2 -> High, Lint)
        f1 = findings[0]
        self.assertEqual(f1.tool, "eslint-typescript")
        self.assertEqual(f1.file, "src/userService.ts")
        self.assertEqual(f1.start_line, 15)
        self.assertEqual(f1.rule_id, "@typescript-eslint/no-explicit-any")
        self.assertEqual(f1.severity, FindingSeverity.HIGH.value)
        self.assertEqual(f1.category, FindingCategory.LINT.value)

        # Finding 2: explicit-function-return-type (Severity 1 -> Low, Lint)
        f2 = findings[1]
        self.assertEqual(f2.rule_id, "@typescript-eslint/explicit-function-return-type")
        self.assertEqual(f2.severity, FindingSeverity.LOW.value)
        self.assertEqual(f2.category, FindingCategory.LINT.value)

        # Finding 3: no-implied-eval (Security inference)
        f3 = findings[2]
        self.assertEqual(f3.rule_id, "@typescript-eslint/no-implied-eval")
        self.assertEqual(f3.severity, FindingSeverity.HIGH.value)
        self.assertEqual(f3.category, FindingCategory.SECURITY.value)

        # Finding 4: Fatal syntax error (Critical severity)
        f4 = findings[3]
        self.assertEqual(f4.severity, FindingSeverity.CRITICAL.value)
        self.assertTrue(f4.metadata.get("fatal"))

    def test_empty_and_malformed_json(self) -> None:
        """Verifies handling of empty and invalid JSON payloads without crashing."""
        self.assertEqual(parse_typescript_eslint_json(""), [])
        self.assertEqual(parse_typescript_eslint_json("not valid json"), [])
        self.assertEqual(parse_typescript_eslint_json("{}"), [])

    def test_nonexistent_repository_path(self) -> None:
        """Verifies that non-existent target path returns empty list gracefully."""
        self.assertEqual(run_typescript_eslint("non_existent_folder_ts_123"), [])


# ==============================================================================
# 4. CLI RUNNER
# ==============================================================================

if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Run ESLint with TypeScript rules against TypeScript source code."
    )
    cli.add_argument(
        "repository",
        nargs="?",
        default=".",
        help="Path to TypeScript repository or source file (default: .)",
    )
    cli.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to custom ESLint configuration file",
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
        print("[+] Running TypeScript Analyzer (ESLint-TypeScript) unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTypeScriptAnalyzer)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    target_path = Path(args.repository).resolve()
    print(f"[+] Scanning TypeScript target: '{target_path}'")

    results = run_typescript_eslint(target_path, config=args.config)

    if args.json:
        print(json.dumps([f.to_dict() for f in results], indent=2))
    else:
        print(f"\n[+] Total TypeScript ESLint findings: {len(results)}")
        for f in results:
            print(f"  [{f.severity.upper()}] {f.rule_id} at {f.file}:{f.start_line} - {f.message}")
