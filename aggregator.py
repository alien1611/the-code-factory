import json
import sys
import subprocess
from pathlib import Path

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


def aggregate():
    run_pytest()

    spec = load_spec()
    report = load_report()

    tests_run = report["summary"].get("total", 0)
    tests_passed = report["summary"].get("passed", 0)
    tests_failed = report["summary"].get("failed", 0)

    evidence = []
    for test in report.get("tests", []):
        evidence.append({
            "name": test["nodeid"],
            "outcome": test["outcome"]
        })

    final_verdict = "PASS" if tests_failed == 0 and tests_run > 0 else "FAIL"

    result = {
        "gemini_verdict": spec.get("verdict"),
        "tests_run": tests_run,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "final_verdict": final_verdict,
        "evidence": evidence
    }

    output_file = BASE_DIR / "final_result.json"
    output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("========== FINAL VERIFICATION RESULT ==========")
    print(json.dumps(result, indent=2))
    print("=================================================")

    return result


if __name__ == "__main__":
    aggregate()