"""
behavioral_engine.py - Behavioral Test Execution Engine for AI Code Verification SaaS

Executes generated or repository verification tests in an isolated subprocess,
captures runtime outcomes, failures, assertion errors, and execution metrics,
and produces structured behavioral evidence for downstream aggregation and verification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Optional
import unittest


@dataclass
class TestItemEvidence:
    name: str
    outcome: str  # 'passed', 'failed', 'skipped', 'error'
    duration_seconds: float = 0.0
    message: Optional[str] = None
    traceback: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BehavioralExecutionResult:
    status: str  # 'completed', 'failed', 'timeout', 'no_tests', 'error'
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    execution_time_seconds: float = 0.0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    raw_report_path: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_behavioral_tests(
    test_target: Optional[str | Path] = None,
    report_file: Optional[str | Path] = None,
    timeout_seconds: int = 60,
    base_dir: Optional[str | Path] = None,
) -> BehavioralExecutionResult:
    root = Path(base_dir).resolve() if base_dir else Path.cwd().resolve()
    target = Path(test_target).resolve() if test_target else root / 'tests' / 'generated'
    report_path = Path(report_file).resolve() if report_file else root / 'pytest_report.json'

    if not target.exists():
        general_tests = root / 'tests'
        if general_tests.exists():
            target = general_tests
        else:
            return BehavioralExecutionResult(
                status='no_tests',
                error_message=f'Test target directory not found: {target}',
            )

    cmd = [
        sys.executable,
        '-m',
        'pytest',
        str(target),
        '--json-report',
        f'--json-report-file={str(report_path)}',
        '-v',
    ]

    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding='utf-8',
            errors='replace',
        )
        elapsed = round(time.perf_counter() - start_time, 3)
    except subprocess.TimeoutExpired:
        return BehavioralExecutionResult(
            status='timeout',
            execution_time_seconds=timeout_seconds,
            error_message=f'Behavioral test execution exceeded timeout of {timeout_seconds}s',
        )
    except Exception as exc:
        return BehavioralExecutionResult(
            status='error',
            execution_time_seconds=round(time.perf_counter() - start_time, 3),
            error_message=f'Failed to execute pytest: {str(exc)}',
        )

    if not report_path.exists():
        return BehavioralExecutionResult(
            status='failed' if proc.returncode != 0 else 'completed',
            execution_time_seconds=elapsed,
            error_message='pytest did not produce a valid json-report output',
        )

    try:
        report_data = json.loads(report_path.read_text(encoding='utf-8'))
    except Exception as exc:
        return BehavioralExecutionResult(
            status='error',
            execution_time_seconds=elapsed,
            error_message=f'Failed to decode pytest JSON report: {str(exc)}',
        )

    summary = report_data.get('summary', {})
    tests_run = summary.get('total', 0)
    tests_passed = summary.get('passed', 0)
    tests_failed = summary.get('failed', 0)
    tests_skipped = summary.get('skipped', 0)

    evidence_list: list[dict[str, Any]] = []
    for test in report_data.get('tests', []):
        node_id = test.get('nodeid', '')
        outcome = test.get('outcome', 'unknown')
        duration = round(test.get('duration', 0.0), 4)

        call_info = test.get('call', {})
        crash = call_info.get('crash', {})
        msg = crash.get('message')
        tb = call_info.get('longrepr')

        evidence_list.append(
            TestItemEvidence(
                name=node_id,
                outcome=outcome,
                duration_seconds=duration,
                message=msg,
                traceback=tb if isinstance(tb, str) else None,
            ).to_dict()
        )

    overall_status = 'completed' if tests_failed == 0 and tests_run > 0 else 'failed'

    return BehavioralExecutionResult(
        status=overall_status,
        tests_run=tests_run,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        tests_skipped=tests_skipped,
        execution_time_seconds=elapsed,
        evidence=evidence_list,
        raw_report_path=str(report_path),
    )


class TestBehavioralEngine(unittest.TestCase):
    def test_run_behavioral_tests(self) -> None:
        result = run_behavioral_tests()
        self.assertIn(result.status, ('completed', 'failed', 'no_tests'))
        if result.status == 'completed':
            self.assertGreater(result.tests_run, 0)
            self.assertEqual(result.tests_failed, 0)
            self.assertGreaterEqual(len(result.evidence), 1)


if __name__ == '__main__':
    res = run_behavioral_tests()
    print('========== BEHAVIORAL EXECUTION RESULT ==========')
    print(json.dumps(res.to_dict(), indent=2))
    print('=================================================')
