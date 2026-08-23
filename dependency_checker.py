"""
dependency_checker.py - Dependency & Vulnerability Analysis Layer for AI Code Verification SaaS

Discovers project dependency manifests across Python (requirements.txt, pyproject.toml)
and JavaScript/Node.js (package.json, package-lock.json), extracts declared packages/versions,
and queries security vulnerability scanners (pip-audit, npm audit).

All identified vulnerabilities are normalized into the common Finding model defined in models.py.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from typing import Any, Optional
import unittest

from models import Finding, FindingCategory, FindingSeverity


# ==============================================================================
# 1. DIRECTORIES TO IGNORE DURING MANIFEST DISCOVERY
# ==============================================================================

IGNORE_DIRS: set[str] = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    "build",
    "dist",
    "target",
    ".idea",
    ".vscode",
    ".tox",
}


# ==============================================================================
# 2. SEVERITY NORMALIZATION
# ==============================================================================

def map_dependency_severity(raw_severity: Optional[str]) -> str:
    """
    Normalizes third-party vulnerability severity ratings (npm, OSV, PyPI) into FindingSeverity.

    Mappings:
    - critical / blocker -> 'critical'
    - high / error       -> 'high'
    - moderate / medium  -> 'medium'
    - low                -> 'low'
    - info               -> 'info'
    """
    if not raw_severity:
        return FindingSeverity.HIGH.value

    sev = raw_severity.strip().lower()
    if sev in ("critical", "blocker"):
        return FindingSeverity.CRITICAL.value
    elif sev in ("high", "error"):
        return FindingSeverity.HIGH.value
    elif sev in ("moderate", "medium", "warning"):
        return FindingSeverity.MEDIUM.value
    elif sev == "low":
        return FindingSeverity.LOW.value
    elif sev in ("info", "informational"):
        return FindingSeverity.INFO.value

    return FindingSeverity.HIGH.value


# ==============================================================================
# 3. MANIFEST DETECTION & DEPENDENCY EXTRACTION
# ==============================================================================

def detect_dependency_files(repo_path: str | Path) -> dict[str, list[Path]]:
    """
    Recursively discovers dependency manifest files in a repository.

    Supported ecosystems:
    - Python: 'requirements.txt', 'requirements-*.txt', 'pyproject.toml'
    - JavaScript: 'package.json', 'package-lock.json'

    Returns:
        Dictionary mapping ecosystem name to list of discovered Path objects.
    """
    repo = Path(repo_path).resolve()
    manifests: dict[str, list[Path]] = {
        "python": [],
        "javascript": [],
    }

    if not repo.exists():
        return manifests

    if repo.is_file():
        name_lower = repo.name.lower()
        if (name_lower.endswith(".txt") and "requirement" in name_lower) or name_lower == "pyproject.toml":
            manifests["python"].append(repo)
        elif name_lower in ("package.json", "package-lock.json"):
            manifests["javascript"].append(repo)
        return manifests

    for root, dirs, files in os.walk(repo, topdown=True):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for filename in files:
            file_path = Path(root) / filename
            fname_lower = filename.lower()

            # Python manifests
            if (
                fname_lower == "requirements.txt"
                or (fname_lower.startswith("requirements") and fname_lower.endswith(".txt"))
                or fname_lower == "pyproject.toml"
            ):
                manifests["python"].append(file_path)

            # JavaScript manifests
            elif fname_lower in ("package.json", "package-lock.json"):
                manifests["javascript"].append(file_path)

    return manifests


def extract_python_dependencies(manifest_path: str | Path) -> list[dict[str, str]]:
    """
    Parses package names and declared version constraints from requirements.txt or pyproject.toml.
    """
    path = Path(manifest_path)
    if not path.is_file():
        return []

    dependencies: list[dict[str, str]] = []

    try:
        if path.suffix.lower() == ".toml":
            data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))

            # Standard PEP 621 [project.dependencies]
            if "project" in data and "dependencies" in data["project"]:
                for dep_str in data["project"]["dependencies"]:
                    parts = re.split(r"(==|>=|<=|~=|>|<|!=)", dep_str, maxsplit=1)
                    pkg_name = parts[0].strip()
                    version_spec = "".join(parts[1:]).strip() if len(parts) > 1 else "*"
                    dependencies.append({"name": pkg_name, "version": version_spec})

            # Poetry [tool.poetry.dependencies]
            if "tool" in data and "poetry" in data["tool"] and "dependencies" in data["tool"]["poetry"]:
                for pkg_name, ver in data["tool"]["poetry"]["dependencies"].items():
                    if pkg_name.lower() != "python":
                        dependencies.append({"name": pkg_name, "version": str(ver)})

        else:
            # Standard requirements.txt lines
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                clean_line = line.split("#")[0].strip()
                parts = re.split(r"(==|>=|<=|~=|>|<|!=)", clean_line, maxsplit=1)
                pkg_name = parts[0].strip()
                version_spec = "".join(parts[1:]).strip() if len(parts) > 1 else "*"
                if pkg_name:
                    dependencies.append({"name": pkg_name, "version": version_spec})

    except Exception:
        return []

    return dependencies


def extract_javascript_dependencies(manifest_path: str | Path) -> list[dict[str, str]]:
    """
    Parses package names and declared version constraints from package.json or package-lock.json.
    """
    path = Path(manifest_path)
    if not path.is_file():
        return []

    dependencies: list[dict[str, str]] = []

    try:
        content = json.loads(path.read_text(encoding="utf-8", errors="replace"))

        # package.json
        if path.name.lower() == "package.json":
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                for pkg_name, ver in content.get(section, {}).items():
                    dependencies.append({"name": pkg_name, "version": str(ver)})

        # package-lock.json
        elif path.name.lower() == "package-lock.json":
            packages = content.get("packages", {})
            for pkg_key, pkg_info in packages.items():
                if isinstance(pkg_info, dict) and "version" in pkg_info:
                    name = pkg_info.get("name") or pkg_key.replace("node_modules/", "")
                    if name:
                        dependencies.append({"name": name, "version": pkg_info["version"]})
    except Exception:
        return []

    return dependencies


# ==============================================================================
# 4. EXTERNAL VULNERABILITY SCANNER INTEGRATIONS (pip-audit & npm audit)
# ==============================================================================

def _extract_json_payload(raw_text: str) -> Optional[Any]:
    """Helper to locate and deserialize JSON from CLI output that may have leading text banners."""
    start_obj = raw_text.find("{")
    start_arr = raw_text.find("[")

    if start_obj == -1 and start_arr == -1:
        return None

    if start_obj != -1 and (start_arr == -1 or start_obj < start_arr):
        start_idx = start_obj
    else:
        start_idx = start_arr

    try:
        return json.loads(raw_text[start_idx:])
    except json.JSONDecodeError:
        return None


def run_pip_audit(manifest_path: Path) -> list[Finding]:
    """
    Executes pip-audit on a Python requirements file and normalizes results into Findings.
    """
    findings: list[Finding] = []
    pip_audit_bin = shutil.which("pip-audit")
    cmd = (
        [pip_audit_bin, "-r", str(manifest_path), "-f", "json", "--desc"]
        if pip_audit_bin
        else [sys.executable, "-m", "pip_audit", "-r", str(manifest_path), "-f", "json", "--desc"]
    )

    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except FileNotFoundError:
        return []
    except Exception:
        return []

    stdout_raw = process.stdout.strip()
    if not stdout_raw:
        return []

    data = _extract_json_payload(stdout_raw)
    if data is None:
        return []

    dep_list = data.get("dependencies", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

    for dep in dep_list:
        if not isinstance(dep, dict):
            continue
        pkg_name = dep.get("name", "unknown")
        version = dep.get("version", "unknown")
        vulns = dep.get("vulns", [])

        for vuln in vulns:
            if not isinstance(vuln, dict):
                continue

            vuln_id = vuln.get("id") or "VULN-UNKNOWN"
            aliases = vuln.get("aliases", [])
            primary_id = aliases[0] if aliases else vuln_id
            description = vuln.get("description") or f"Known vulnerability in {pkg_name} {version}"
            fix_versions = vuln.get("fix_versions", [])

            fix_info = f" Upgrade to: {', '.join(fix_versions)}" if fix_versions else ""
            message = f"Vulnerability {primary_id} detected in dependency '{pkg_name}' ({version}).{fix_info}"

            meta: dict[str, Any] = {
                "package": pkg_name,
                "installed_version": version,
                "vuln_id": vuln_id,
                "aliases": aliases,
                "fix_versions": fix_versions,
                "description": description,
            }

            findings.append(
                Finding(
                    tool="pip-audit",
                    category=FindingCategory.DEPENDENCY.value,
                    severity=FindingSeverity.HIGH.value,
                    file=str(manifest_path),
                    rule_id=primary_id,
                    message=message,
                    evidence=f"{pkg_name}=={version}",
                    confidence=1.0,
                    metadata=meta,
                )
            )

    return findings


def run_npm_audit(manifest_path: Path) -> list[Finding]:
    """
    Executes npm audit on a Node.js project directory and normalizes results into Findings.
    """
    findings: list[Finding] = []
    npm_bin = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    project_dir = manifest_path.parent

    cmd = [npm_bin, "audit", "--json"]

    try:
        process = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
        )
    except FileNotFoundError:
        return []
    except Exception:
        return []

    stdout_raw = process.stdout.strip()
    if not stdout_raw:
        return []

    data = _extract_json_payload(stdout_raw)
    if data is None or not isinstance(data, dict):
        return []

    # npm audit v2 report format
    vulnerabilities = data.get("vulnerabilities", {})
    if isinstance(vulnerabilities, dict):
        for pkg_name, vuln_data in vulnerabilities.items():
            if not isinstance(vuln_data, dict):
                continue

            raw_severity = vuln_data.get("severity", "moderate")
            severity = map_dependency_severity(raw_severity)
            range_spec = vuln_data.get("range", "")
            via_list = vuln_data.get("via", [])

            advisory_title = ""
            rule_id = f"NPM-{pkg_name}"
            advisory_url = ""
            cwe_list = []

            for via in via_list:
                if isinstance(via, dict):
                    advisory_title = via.get("title", "")
                    advisory_url = via.get("url", "")
                    cwe_list = via.get("cwe", [])
                    if via.get("url") and "GHSA-" in via["url"]:
                        rule_id = via["url"].split("/")[-1]
                    break

            msg_title = advisory_title or f"Vulnerable dependency version in '{pkg_name}'"
            message = f"{msg_title} (affects {range_spec})"

            meta: dict[str, Any] = {
                "package": pkg_name,
                "vulnerable_range": range_spec,
                "is_direct": vuln_data.get("isDirect", False),
                "fix_available": vuln_data.get("fixAvailable", False),
            }
            if advisory_url:
                meta["url"] = advisory_url
            if cwe_list:
                meta["cwe"] = cwe_list

            findings.append(
                Finding(
                    tool="npm-audit",
                    category=FindingCategory.DEPENDENCY.value,
                    severity=severity,
                    file=str(manifest_path),
                    rule_id=rule_id,
                    message=message,
                    evidence=f"{pkg_name}@{range_spec}",
                    confidence=1.0,
                    metadata=meta,
                )
            )

    return findings


# ==============================================================================
# 5. UNIFIED DEPENDENCY CHECK COORDINATOR
# ==============================================================================

def check_dependencies(repo_path: str | Path) -> list[Finding]:
    """
    Discovers all dependency manifest files in the repository and checks them for vulnerabilities.

    Returns:
        List of normalized Finding objects. If no manifests are found or no vulnerabilities
        are identified, returns an empty list. Never crashes on missing tools or network timeouts.
    """
    target = Path(repo_path).resolve()
    all_findings: list[Finding] = []

    # 1. Discover manifests
    manifest_map = detect_dependency_files(target)
    python_manifests = manifest_map.get("python", [])
    js_manifests = manifest_map.get("javascript", [])

    # If no dependency files found, return empty list per requirements
    if not python_manifests and not js_manifests:
        return []

    # 2. Check Python manifests with pip-audit
    for py_file in python_manifests:
        if py_file.suffix.lower() == ".txt":
            all_findings.extend(run_pip_audit(py_file))

    # 3. Check JavaScript manifests with npm audit
    checked_js_dirs: set[Path] = set()
    for js_file in js_manifests:
        parent_dir = js_file.parent
        if parent_dir not in checked_js_dirs:
            checked_js_dirs.add(parent_dir)
            all_findings.extend(run_npm_audit(js_file))

    return all_findings


# ==============================================================================
# 6. UNIT TESTS & CLI RUNNER
# ==============================================================================

class TestDependencyChecker(unittest.TestCase):
    """Unit tests for dependency manifest detection and parsing."""

    def test_detect_dependency_files(self) -> None:
        p = Path("test_repository")
        if p.exists():
            manifests = detect_dependency_files(p)
            self.assertIn("python", manifests)
            self.assertIn("javascript", manifests)

    def test_extract_python_dependencies(self) -> None:
        p = Path("test_repository/requirements.txt")
        if p.exists():
            deps = extract_python_dependencies(p)
            self.assertGreaterEqual(len(deps), 1)
            self.assertEqual(deps[0]["name"], "requests")

    def test_extract_javascript_dependencies(self) -> None:
        p = Path("test_repository/package.json")
        if p.exists():
            deps = extract_javascript_dependencies(p)
            self.assertGreaterEqual(len(deps), 1)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Scan project dependencies for known security vulnerabilities."
    )
    cli.add_argument(
        "--test",
        action="store_true",
        help="Run dependency checker unit tests",
    )
    cli.add_argument(
        "repository_path",
        nargs="?",
        default="./test_repository",
        help="Path to repository or project directory to scan (default: ./test_repository)",
    )
    cli.add_argument(
        "--list-deps",
        action="store_true",
        help="List declared project dependencies and version constraints without auditing",
    )

    args = cli.parse_args()

    if args.test:
        print("[+] Running Dependency Checker unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDependencyChecker)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    target_repo = Path(args.repository_path)

    print(f"[+] Detecting dependency manifests in: '{target_repo}'")
    manifests = detect_dependency_files(target_repo)
    print(f" - Python manifests    : {[str(p.name) for p in manifests.get('python', [])]}")
    print(f" - JavaScript manifests: {[str(p.name) for p in manifests.get('javascript', [])]}")

    if args.list_deps:
        print("\nDeclared Dependencies:")
        for py_p in manifests.get("python", []):
            print(f"\n[{py_p.name}]")
            for d in extract_python_dependencies(py_p):
                print(f"  - {d['name']}: {d['version']}")
        for js_p in manifests.get("javascript", []):
            print(f"\n[{js_p.name}]")
            for d in extract_javascript_dependencies(js_p):
                print(f"  - {d['name']}: {d['version']}")
        sys.exit(0)

    print("\n[+] Checking dependencies for vulnerabilities...")
    findings = check_dependencies(target_repo)

    # Print results as readable JSON
    json_output = json.dumps([f.to_dict() for f in findings], indent=2)
    print(json_output)

    # Print summary statistics
    print("\n" + "=" * 50)
    print("DEPENDENCY VULNERABILITY SUMMARY")
    print("=" * 50)
    print(f"Total Vulnerabilities : {len(findings)}")
    by_severity: dict[str, int] = {}
    for item in findings:
        by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
    for sev, count in sorted(by_severity.items()):
        print(f" - {sev.upper():<10}: {count}")
    print("=" * 50)

