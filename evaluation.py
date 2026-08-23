"""
evaluation.py - Objective Performance & Benchmark Evaluator for AI Code Verification SaaS

Runs actual verification results against labeled ground-truth benchmark datasets,
calculating:
1. Confusion Matrix (TP, FP, TN, FN)
2. Core Classification Metrics (Precision, Recall, F1-score, Accuracy)
3. Latency & Execution Timings (Mean, Median, Min, Max)
4. Granular Per-Tool, Per-Category, and Per-Severity Detection Rates
5. Machine-Readable JSON Export and Formatted Markdown Dashboard Summary
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from typing import Any, Callable, Optional
import unittest

from models import FileMetadata, Finding, FindingCategory, FindingSeverity
from rfid_verifier import verify_rfid_authentication
from dependency_checker import run_pip_audit


# ==============================================================================
# 1. EVALUATION DATA STRUCTURES
# ==============================================================================

def _normalize_tool_name(name: str) -> str:
    """Normalizes tool names (e.g. 'rfid-domain-rule' -> 'rfid_domain_rule')."""
    return name.lower().replace("-", "_").strip()


@dataclass
class CaseEvaluation:
    """
    Evaluation record for an individual benchmark test case.
    """
    case_id: str
    language: str
    bug_category: str
    expected_verdict: str  # "PASS" or "FAIL"
    actual_verdict: str    # "PASS" or "FAIL"
    classification: str    # "TP", "FP", "TN", "FN"
    severity: str
    execution_time_ms: float
    detecting_tools: list[str] = field(default_factory=list)
    expected_tools: list[str] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    is_correct: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MetricSummary:
    """
    Aggregated classification performance metrics.
    """
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TimingSummary:
    """
    Verification latency statistics.
    """
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    median_time_ms: float = 0.0
    min_time_ms: float = 0.0
    max_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolDetectionStat:
    """
    Detection performance for a specific verification tool.
    """
    tool_name: str
    detected_count: int = 0
    expected_count: int = 0
    detection_rate_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationReport:
    """
    Comprehensive evaluation report across the entire benchmark dataset.
    """
    benchmark_name: str
    timestamp: str
    metrics: MetricSummary
    timing: TimingSummary
    tool_performance: dict[str, ToolDetectionStat]
    category_performance: dict[str, dict[str, Any]]
    severity_performance: dict[str, dict[str, Any]]
    case_results: list[CaseEvaluation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_name": self.benchmark_name,
            "timestamp": self.timestamp,
            "metrics": self.metrics.to_dict(),
            "timing": self.timing.to_dict(),
            "tool_performance": {k: v.to_dict() for k, v in self.tool_performance.items()},
            "category_performance": self.category_performance,
            "severity_performance": self.severity_performance,
            "case_results": [c.to_dict() for c in self.case_results],
        }

    def to_json(self, indent: int = 2) -> str:
        """Exports report to structured JSON."""
        return json.dumps(self.to_dict(), indent=indent)

    def generate_dashboard_markdown(self) -> str:
        """Generates a presentation-ready markdown dashboard."""
        m = self.metrics
        t = self.timing

        lines = [
            f"# Verification Benchmark Evaluation Dashboard",
            f"**Dataset:** `{self.benchmark_name}` | **Evaluated At:** `{self.timestamp}`",
            "",
            "## Key Performance Indicators (KPIs)",
            "",
            "| Metric | Score | Status | Description |",
            "| :--- | :---: | :---: | :--- |",
            f"| **Accuracy** | `{m.accuracy}%` | {'[HIGH]' if m.accuracy >= 90 else '[MODERATE]'} | Overall correctness across all safe and flawed cases |",
            f"| **Precision** | `{m.precision}%` | {'[HIGH]' if m.precision >= 90 else '[MODERATE]'} | Freedom from false alarms ($TP / (TP + FP)$) |",
            f"| **Recall (Sensitivity)** | `{m.recall}%` | {'[HIGH]' if m.recall >= 90 else '[MODERATE]'} | Flaw detection coverage ($TP / (TP + FN)$) |",
            f"| **F1-Score** | `{m.f1_score}%` | {'[HIGH]' if m.f1_score >= 90 else '[MODERATE]'} | Harmonic balance of precision and recall |",
            "",
            "## Confusion Matrix",
            "",
            "| | Actual Flaw (Positive) | Actual Safe (Negative) |",
            "| :--- | :---: | :---: |",
            f"| **Predicted Flaw (FAIL)** | **True Positive (TP):** `{m.true_positives}` | **False Positive (FP):** `{m.false_positives}` |",
            f"| **Predicted Safe (PASS)** | **False Negative (FN):** `{m.false_negatives}` | **True Negative (TN):** `{m.true_negatives}` |",
            "",
            "## Verification Latency & Performance",
            "",
            f"- **Total Benchmark Runtime:** `{t.total_time_ms:.2f} ms`",
            f"- **Average Verification Time:** `{t.avg_time_ms:.2f} ms / case`",
            f"- **Median Verification Time:** `{t.median_time_ms:.2f} ms / case`",
            f"- **Min / Max Latency:** `{t.min_time_ms:.2f} ms` / `{t.max_time_ms:.2f} ms`",
            "",
            "## Per-Tool Detection Coverage",
            "",
            "| Verification Tool / Method | Detections | Expected Target Cases | Coverage Rate |",
            "| :--- | :---: | :---: | :---: |",
        ]

        for tool_name, stat in sorted(self.tool_performance.items(), key=lambda x: -x[1].detection_rate_pct):
            lines.append(
                f"| `{tool_name}` | `{stat.detected_count}` | `{stat.expected_count}` | `{stat.detection_rate_pct:.1f}%` |"
            )

        lines.extend([
            "",
            "## Category-Specific Performance",
            "",
            "| Bug Category | Total Cases | PASS | FAIL | Accuracy | Recall |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ])

        for cat, stat in sorted(self.category_performance.items()):
            acc = stat.get("accuracy", 0.0)
            rec = stat.get("recall", 0.0)
            lines.append(
                f"| `{cat}` | `{stat['total']}` | `{stat['pass_count']}` | `{stat['fail_count']}` | `{acc:.1f}%` | `{rec:.1f}%` |"
            )

        return "\n".join(lines)


# ==============================================================================
# 2. LOCAL VERIFICATION RUNNER & ENGINE DISPATCHER
# ==============================================================================

def default_verification_runner(case: dict[str, Any]) -> list[Finding]:
    """
    Executes actual local verification engines on a given benchmark test case.
    Handles tool applicability cleanly (e.g. RFID rule for C++/Arduino code).
    """
    findings: list[Finding] = []
    source = case.get("source_code", "")
    lang = case.get("language", "").lower()
    cat = case.get("bug_category", "")
    case_id = case.get("case_id", "TEST")

    # 1. RFID / IoT Domain Rule
    if cat == "rfid_iot_authentication" or "MFRC522" in source or lang in ("cpp", "c", "arduino"):
        meta = FileMetadata(path=f"{case_id}.ino", language="C++")
        findings.extend(verify_rfid_authentication(source, meta))

    # 2. Dependency Manifest Auditing
    elif cat == "dependency_vulnerabilities" and lang == "python":
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tmp:
            tmp.write(source)
            tmp_path = Path(tmp.name)
        try:
            findings.extend(run_pip_audit(tmp_path))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    return findings


# ==============================================================================
# 3. BENCHMARK EVALUATION ENGINE
# ==============================================================================

def evaluate_case(
    case: dict[str, Any],
    custom_runner: Optional[Callable[[dict[str, Any]], list[Finding]]] = None,
) -> CaseEvaluation:
    """
    Evaluates a single benchmark case against expected ground truth.
    Measures execution time with microsecond precision.
    """
    case_id = case["case_id"]
    language = case.get("language", "unknown")
    category = case.get("bug_category", "unknown")
    expected_verdict = case["expected_verdict"].upper()
    severity = case.get("severity", "medium")
    raw_expected_tools = case.get("detection_methods_expected", [])
    expected_tools = [_normalize_tool_name(t) for t in raw_expected_tools]

    runner = custom_runner or default_verification_runner

    start_time = time.perf_counter()
    findings = runner(case)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    actual_verdict = "FAIL" if len(findings) > 0 else "PASS"

    if expected_verdict == "FAIL" and actual_verdict == "FAIL":
        classification = "TP"
        is_correct = True
    elif expected_verdict == "PASS" and actual_verdict == "PASS":
        classification = "TN"
        is_correct = True
    elif expected_verdict == "PASS" and actual_verdict == "FAIL":
        classification = "FP"
        is_correct = False
    else:
        classification = "FN"
        is_correct = False

    detecting_tools = sorted(list({_normalize_tool_name(f.tool) for f in findings if f.tool}))

    return CaseEvaluation(
        case_id=case_id,
        language=language,
        bug_category=category,
        expected_verdict=expected_verdict,
        actual_verdict=actual_verdict,
        classification=classification,
        severity=severity,
        execution_time_ms=round(elapsed_ms, 3),
        detecting_tools=detecting_tools,
        expected_tools=expected_tools,
        findings=[f.to_dict() for f in findings],
        is_correct=is_correct,
    )


def evaluate_dataset(
    dataset: dict[str, Any] | list[dict[str, Any]],
    custom_runner: Optional[Callable[[dict[str, Any]], list[Finding]]] = None,
) -> EvaluationReport:
    """
    Evaluates an entire labeled benchmark dataset and computes comprehensive performance metrics.
    """
    if isinstance(dataset, dict):
        benchmark_name = dataset.get("benchmark_name", "AI Code Verification Benchmark")
        cases = dataset.get("cases", [])
    else:
        benchmark_name = "AI Code Verification Benchmark"
        cases = dataset

    case_results: list[CaseEvaluation] = []
    latencies: list[float] = []

    tp = fp = tn = fn = 0
    passed_count = failed_count = 0

    tool_detections: dict[str, int] = {}
    tool_expected: dict[str, int] = {}
    category_stats: dict[str, dict[str, Any]] = {}
    severity_stats: dict[str, dict[str, Any]] = {}

    for case in cases:
        eval_record = evaluate_case(case, custom_runner=custom_runner)
        case_results.append(eval_record)
        latencies.append(eval_record.execution_time_ms)

        if eval_record.expected_verdict == "PASS":
            passed_count += 1
        else:
            failed_count += 1

        if eval_record.classification == "TP":
            tp += 1
        elif eval_record.classification == "FP":
            fp += 1
        elif eval_record.classification == "TN":
            tn += 1
        elif eval_record.classification == "FN":
            fn += 1

        for tool in eval_record.expected_tools:
            norm_t = _normalize_tool_name(tool)
            tool_expected[norm_t] = tool_expected.get(norm_t, 0) + 1
        for tool in eval_record.detecting_tools:
            norm_t = _normalize_tool_name(tool)
            tool_detections[norm_t] = tool_detections.get(norm_t, 0) + 1

        cat = eval_record.bug_category
        if cat not in category_stats:
            category_stats[cat] = {
                "total": 0,
                "pass_count": 0,
                "fail_count": 0,
                "tp": 0,
                "fp": 0,
                "tn": 0,
                "fn": 0,
            }
        category_stats[cat]["total"] += 1
        if eval_record.expected_verdict == "PASS":
            category_stats[cat]["pass_count"] += 1
        else:
            category_stats[cat]["fail_count"] += 1

        category_stats[cat][eval_record.classification.lower()] += 1

        sev = eval_record.severity
        if sev not in severity_stats:
            severity_stats[sev] = {"total": 0, "detected": 0, "expected_flawed": 0}
        severity_stats[sev]["total"] += 1
        if eval_record.expected_verdict == "FAIL":
            severity_stats[sev]["expected_flawed"] += 1
            if eval_record.classification == "TP":
                severity_stats[sev]["detected"] += 1

    total_cases = len(cases)

    precision = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else (100.0 if failed_count == 0 else 0.0)
    recall = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else (100.0 if failed_count == 0 else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    accuracy = ((tp + tn) / total_cases * 100.0) if total_cases > 0 else 100.0

    metrics = MetricSummary(
        total_cases=total_cases,
        passed_cases=passed_count,
        failed_cases=failed_count,
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        accuracy=round(accuracy, 2),
        precision=round(precision, 2),
        recall=round(recall, 2),
        f1_score=round(f1, 2),
    )

    timing = TimingSummary(
        total_time_ms=round(sum(latencies), 3),
        avg_time_ms=round(statistics.mean(latencies), 3) if latencies else 0.0,
        median_time_ms=round(statistics.median(latencies), 3) if latencies else 0.0,
        min_time_ms=round(min(latencies), 3) if latencies else 0.0,
        max_time_ms=round(max(latencies), 3) if latencies else 0.0,
    )

    tool_performance: dict[str, ToolDetectionStat] = {}
    all_tool_names = set(tool_detections.keys()) | set(tool_expected.keys())
    for tool_name in all_tool_names:
        det = tool_detections.get(tool_name, 0)
        exp = tool_expected.get(tool_name, 0)
        rate = (det / exp * 100.0) if exp > 0 else (100.0 if det > 0 else 0.0)
        tool_performance[tool_name] = ToolDetectionStat(
            tool_name=tool_name,
            detected_count=det,
            expected_count=exp,
            detection_rate_pct=round(rate, 2),
        )

    for cat, stat in category_stats.items():
        cat_tp = stat["tp"]
        cat_fp = stat["fp"]
        cat_tn = stat["tn"]
        cat_fn = stat["fn"]
        cat_total = stat["total"]
        cat_acc = ((cat_tp + cat_tn) / cat_total * 100.0) if cat_total > 0 else 0.0
        cat_rec = (cat_tp / (cat_tp + cat_fn) * 100.0) if (cat_tp + cat_fn) > 0 else (100.0 if stat["fail_count"] == 0 else 0.0)
        stat["accuracy"] = round(cat_acc, 2)
        stat["recall"] = round(cat_rec, 2)

    for sev, stat in severity_stats.items():
        exp = stat["expected_flawed"]
        det = stat["detected"]
        rate = (det / exp * 100.0) if exp > 0 else 100.0
        stat["detection_rate_pct"] = round(rate, 2)

    now_iso = datetime.now(timezone.utc).isoformat()

    return EvaluationReport(
        benchmark_name=benchmark_name,
        timestamp=now_iso,
        metrics=metrics,
        timing=timing,
        tool_performance=tool_performance,
        category_performance=category_stats,
        severity_performance=severity_stats,
        case_results=case_results,
    )


# ==============================================================================
# 4. UNIT TESTS
# ==============================================================================

class TestEvaluationFramework(unittest.TestCase):
    """Unit test suite for the evaluation metrics and benchmark harness."""

    def setUp(self) -> None:
        self.mock_dataset = {
            "benchmark_name": "Mock Evaluation Suite",
            "cases": [
                {
                    "case_id": "MOCK-001",
                    "language": "python",
                    "bug_category": "input_validation",
                    "expected_verdict": "FAIL",
                    "severity": "critical",
                    "detection_methods_expected": ["semgrep"],
                    "source_code": "def query(x): return f'SELECT {x}'",
                },
                {
                    "case_id": "MOCK-002",
                    "language": "python",
                    "bug_category": "input_validation",
                    "expected_verdict": "PASS",
                    "severity": "info",
                    "detection_methods_expected": [],
                    "source_code": "def query(x): return 'SELECT %s', (x,)",
                },
                {
                    "case_id": "MOCK-003",
                    "language": "cpp",
                    "bug_category": "rfid_iot_authentication",
                    "expected_verdict": "FAIL",
                    "severity": "critical",
                    "detection_methods_expected": ["rfid_domain_rule"],
                    "source_code": "void loop() { if (mfrc522.PICC_IsNewCardPresent()) { unlockDoor(); } }",
                },
            ],
        }

    def test_mock_perfect_evaluation(self) -> None:
        """Verifies calculation when mock runner accurately detects all bugs."""
        def mock_perfect_runner(case: dict[str, Any]) -> list[Finding]:
            if case["expected_verdict"] == "FAIL":
                return [
                    Finding(
                        tool=case["detection_methods_expected"][0] if case["detection_methods_expected"] else "mock-tool",
                        category="security",
                        severity="high",
                        file="test.py",
                        rule_id="RULE-01",
                        message="Bug detected",
                    )
                ]
            return []

        report = evaluate_dataset(self.mock_dataset, custom_runner=mock_perfect_runner)

        self.assertEqual(report.metrics.total_cases, 3)
        self.assertEqual(report.metrics.true_positives, 2)
        self.assertEqual(report.metrics.true_negatives, 1)
        self.assertEqual(report.metrics.false_positives, 0)
        self.assertEqual(report.metrics.false_negatives, 0)
        self.assertEqual(report.metrics.precision, 100.0)
        self.assertEqual(report.metrics.recall, 100.0)
        self.assertEqual(report.metrics.f1_score, 100.0)
        self.assertEqual(report.metrics.accuracy, 100.0)

    def test_confusion_matrix_mixed_classification(self) -> None:
        """Verifies TP, FP, TN, FN computation under mixed results."""
        def mock_flawed_runner(case: dict[str, Any]) -> list[Finding]:
            if case["case_id"] in ("MOCK-001", "MOCK-002"):
                return [Finding(tool="semgrep", category="security", severity="high", file="test.py", rule_id="R1", message="M")]
            return []

        report = evaluate_dataset(self.mock_dataset, custom_runner=mock_flawed_runner)

        self.assertEqual(report.metrics.true_positives, 1)
        self.assertEqual(report.metrics.false_positives, 1)
        self.assertEqual(report.metrics.false_negatives, 1)
        self.assertEqual(report.metrics.true_negatives, 0)

        self.assertEqual(report.metrics.precision, 50.0)
        self.assertEqual(report.metrics.recall, 50.0)
        self.assertEqual(report.metrics.accuracy, 33.33)

    def test_timing_statistics(self) -> None:
        """Verifies that execution latencies and statistics are properly tracked."""
        report = evaluate_dataset(self.mock_dataset)
        self.assertGreaterEqual(report.timing.total_time_ms, 0.0)
        self.assertGreaterEqual(report.timing.avg_time_ms, 0.0)
        self.assertGreaterEqual(report.timing.median_time_ms, 0.0)
        self.assertEqual(len(report.case_results), 3)

    def test_markdown_dashboard_generation(self) -> None:
        """Verifies markdown dashboard formatting and content."""
        report = evaluate_dataset(self.mock_dataset)
        dashboard = report.generate_dashboard_markdown()
        self.assertIn("# Verification Benchmark Evaluation Dashboard", dashboard)
        self.assertIn("Confusion Matrix", dashboard)
        self.assertIn("Per-Tool Detection Coverage", dashboard)


# ==============================================================================
# 5. CLI RUNNER & DASHBOARD REPORTER
# ==============================================================================

if __name__ == "__main__":
    parser_cli = argparse.ArgumentParser(
        description="Evaluate AI verification performance against labeled benchmark datasets."
    )
    parser_cli.add_argument(
        "--dataset",
        type=str,
        default="./benchmark/benchmark_dataset.json",
        help="Path to labeled benchmark dataset JSON file",
    )
    parser_cli.add_argument(
        "--output-json",
        type=str,
        help="Path to save machine-readable evaluation results JSON",
    )
    parser_cli.add_argument(
        "--output-dashboard",
        type=str,
        help="Path to save markdown dashboard summary",
    )
    parser_cli.add_argument(
        "--test",
        action="store_true",
        help="Execute unit tests on evaluation framework",
    )

    args = parser_cli.parse_args()

    if args.test:
        print("[+] Running Evaluation Framework unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestEvaluationFramework)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"[-] Error: Benchmark dataset not found at: {dataset_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[+] Loading and evaluating benchmark dataset: '{dataset_path}'")
    raw_data = json.loads(dataset_path.read_text(encoding="utf-8"))

    report = evaluate_dataset(raw_data)

    print("\n" + report.generate_dashboard_markdown())

    if args.output_json:
        out_json_path = Path(args.output_json)
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(report.to_json(), encoding="utf-8")
        print(f"\n[+] Machine-readable results saved to: {out_json_path}")

    if args.output_dashboard:
        out_dash_path = Path(args.output_dashboard)
        out_dash_path.parent.mkdir(parents=True, exist_ok=True)
        out_dash_path.write_text(report.generate_dashboard_markdown(), encoding="utf-8")
        print(f"[+] Dashboard summary saved to: {out_dash_path}")
