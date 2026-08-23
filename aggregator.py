import json
import sys
import subprocess
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).parent
SPEC_FILE = BASE_DIR / "test_spec.json"
REPORT_FILE = BASE_DIR / "pytest_report.json"


def run_pytest():
    subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "--json-report",
            f"--json-report-file={REPORT_FILE}",
            "-v"
        ],
        cwd=BASE_DIR
    )


def load_spec():
    return json.loads(SPEC_FILE.read_text(encoding="utf-8"))


def load_report():
    return json.loads(REPORT_FILE.read_text(encoding="utf-8"))


def aggregate(
    spec_path: Optional[Path | str] = None,
    report_path: Optional[Path | str] = None,
    static_findings: Optional[list[dict]] = None,
    output_path: Optional[Path | str] = None,
) -> dict:
    spec_file = Path(spec_path) if spec_path else SPEC_FILE
    report_file = Path(report_path) if report_path else REPORT_FILE
    out_file = Path(output_path) if output_path else (BASE_DIR / "final_result.json")

    run_pytest()

    spec = json.loads(spec_file.read_text(encoding="utf-8")) if spec_file.exists() else {}
    report = json.loads(report_file.read_text(encoding="utf-8")) if report_file.exists() else {"summary": {}, "tests": []}

    tests_run = report.get("summary", {}).get("total", 0)
    tests_passed = report.get("summary", {}).get("passed", 0)
    tests_failed = report.get("summary", {}).get("failed", 0)

    evidence = []
    for test in report.get("tests", []):
        evidence.append({
            "name": test.get("nodeid", ""),
            "outcome": test.get("outcome", "")
        })

    # Check for critical static/security findings if provided
    findings = static_findings or []
    has_critical_findings = any(
        isinstance(f, dict) and f.get("severity") in ("critical", "high") for f in findings
    )

    final_verdict = "PASS" if (tests_failed == 0 and tests_run > 0 and not has_critical_findings) else "FAIL"

    result = {
        "gemini_verdict": spec.get("verdict", "UNKNOWN"),
        "tests_run": tests_run,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "final_verdict": final_verdict,
        "evidence": evidence,
    }

    if findings:
        result["findings"] = findings

    out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("========== FINAL VERIFICATION RESULT ==========")
    print(json.dumps(result, indent=2))
    print("=================================================")

    return result


if __name__ == "__main__":
    aggregate()