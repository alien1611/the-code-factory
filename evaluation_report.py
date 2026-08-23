"""
evaluation_report.py - React Dashboard Data Transformer for AI Code Verification Benchmark

Transforms raw benchmark evaluation results into structured, deterministic, and
machine-readable JSON designed specifically for consumption by modern web dashboards.

Includes:
1. Overall summary & KPI metrics
2. Standardized per-tool performance breakdown (Ruff, Semgrep, Dependency Scanner, Domain Rules, Generated Tests, AI Verification)
3. Category metrics (Security, Logic, Authentication, Authorization, RFID, Dependency)
4. Performance & timing metrics (Average, Median, Min, Max, Total)
5. Comprehensive case-by-case detection matrix
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Optional
import unittest

from evaluation import EvaluationReport, evaluate_dataset


# ==============================================================================
# 1. CONSTANTS & CANONICAL MAPPINGS
# ==============================================================================

CANONICAL_TOOLS = [
    {"id": "ruff", "displayName": "Ruff Linter", "aliases": ["ruff", "static_analysis"]},
    {"id": "semgrep", "displayName": "Semgrep AST Rules", "aliases": ["semgrep"]},
    {"id": "dependency_scanner", "displayName": "Dependency Scanner", "aliases": ["dependency_scanner", "pip_audit", "npm_audit"]},
    {"id": "domain_rules", "displayName": "Domain Rules (RFID)", "aliases": ["rfid_domain_rule", "domain_rules", "rfid_verifier"]},
    {"id": "generated_tests", "displayName": "Generated Property Tests", "aliases": ["generated_tests"]},
    {"id": "ai_verification", "displayName": "AI / LLM Verification", "aliases": ["llm_reasoning", "ai_verification", "llm"]},
]

CATEGORY_DISPLAY_NAMES = {
    "security": "Security Vulnerabilities",
    "logic": "Business Logic",
    "logic_errors": "Business Logic",
    "authentication": "Authentication",
    "authorization": "Authorization (IDOR)",
    "rfid": "RFID / IoT Hardware",
    "rfid_iot_authentication": "RFID / IoT Hardware",
    "dependency": "Dependency Security",
    "dependency_vulnerabilities": "Dependency Security",
    "input_validation": "Input Validation",
}

CANONICAL_CATEGORIES = [
    "security",
    "logic",
    "authentication",
    "authorization",
    "rfid",
    "dependency",
    "input_validation",
]


def _normalize_category_key(raw_cat: str) -> str:
    """Normalizes category strings into canonical keys."""
    raw = raw_cat.lower().strip()
    if "rfid" in raw or "iot" in raw:
        return "rfid"
    if "dep" in raw:
        return "dependency"
    if "logic" in raw:
        return "logic"
    if "authz" in raw or "authorization" in raw:
        return "authorization"
    if "auth" in raw or "authentication" in raw:
        return "authentication"
    if "input" in raw or "validation" in raw:
        return "input_validation"
    if "sec" in raw or "security" in raw:
        return "security"
    return raw


# ==============================================================================
# 2. DASHBOARD DATA TRANSFORMER
# ==============================================================================

def generate_react_dashboard_data(
    report_data: dict[str, Any] | EvaluationReport,
) -> dict[str, Any]:
    """
    Transforms raw benchmark evaluation results into a clean, deterministic,
    and React-dashboard-ready structured JSON payload.
    """
    if isinstance(report_data, EvaluationReport):
        raw = report_data.to_dict()
    else:
        raw = report_data

    metrics_raw = raw.get("metrics", {})
    timing_raw = raw.get("timing", {})
    case_results = raw.get("case_results", [])
    benchmark_name = raw.get("benchmark_name", "AI Code Verification Benchmark")
    eval_timestamp = raw.get("timestamp", datetime.now(timezone.utc).isoformat())

    # 1. Overall Summary Metrics
    summary = {
        "totalCases": metrics_raw.get("total_cases", len(case_results)),
        "passed": metrics_raw.get("passed_cases", 0),
        "failed": metrics_raw.get("failed_cases", 0),
        "truePositives": metrics_raw.get("true_positives", 0),
        "falsePositives": metrics_raw.get("false_positives", 0),
        "trueNegatives": metrics_raw.get("true_negatives", 0),
        "falseNegatives": metrics_raw.get("false_negatives", 0),
        "precision": round(metrics_raw.get("precision", 0.0), 2),
        "recall": round(metrics_raw.get("recall", 0.0), 2),
        "f1Score": round(metrics_raw.get("f1_score", 0.0), 2),
        "accuracy": round(metrics_raw.get("accuracy", 0.0), 2),
    }

    # 2. Verification Latency & Performance
    performance = {
        "averageExecutionTimeMs": round(timing_raw.get("avg_time_ms", 0.0), 2),
        "medianExecutionTimeMs": round(timing_raw.get("median_time_ms", 0.0), 2),
        "minimumExecutionTimeMs": round(timing_raw.get("min_time_ms", 0.0), 2),
        "maximumExecutionTimeMs": round(timing_raw.get("max_time_ms", 0.0), 2),
        "totalExecutionTimeMs": round(timing_raw.get("total_time_ms", 0.0), 2),
    }

    # 3. Standardized Per-Tool Metrics
    per_tool_metrics = []
    for tool_def in CANONICAL_TOOLS:
        tool_id = tool_def["id"]
        aliases = tool_def["aliases"]

        detected_count = 0
        expected_count = 0

        for c in case_results:
            c_detecting = [t.lower().replace("-", "_") for t in c.get("detecting_tools", [])]
            c_expected = [t.lower().replace("-", "_") for t in c.get("expected_tools", [])]

            if any(alias in c_detecting for alias in aliases):
                detected_count += 1
            if any(alias in c_expected for alias in aliases):
                expected_count += 1

        cov_pct = (detected_count / expected_count * 100.0) if expected_count > 0 else (100.0 if detected_count > 0 else 0.0)

        per_tool_metrics.append({
            "id": tool_id,
            "name": tool_def["displayName"],
            "detectedCount": detected_count,
            "expectedCount": expected_count,
            "coveragePct": round(cov_pct, 2),
        })

    # 4. Per-Category Metrics
    category_buckets: dict[str, dict[str, Any]] = {}
    for cat_id in CANONICAL_CATEGORIES:
        category_buckets[cat_id] = {
            "category": cat_id,
            "displayName": CATEGORY_DISPLAY_NAMES.get(cat_id, cat_id.replace("_", " ").title()),
            "total": 0,
            "passCount": 0,
            "failCount": 0,
            "truePositives": 0,
            "falsePositives": 0,
            "trueNegatives": 0,
            "falseNegatives": 0,
            "accuracy": 0.0,
            "recall": 0.0,
        }

    for c in case_results:
        norm_cat = _normalize_category_key(c.get("bug_category", ""))
        if norm_cat not in category_buckets:
            category_buckets[norm_cat] = {
                "category": norm_cat,
                "displayName": CATEGORY_DISPLAY_NAMES.get(norm_cat, norm_cat.replace("_", " ").title()),
                "total": 0,
                "passCount": 0,
                "failCount": 0,
                "truePositives": 0,
                "falsePositives": 0,
                "trueNegatives": 0,
                "falseNegatives": 0,
                "accuracy": 0.0,
                "recall": 0.0,
            }

        b = category_buckets[norm_cat]
        b["total"] += 1

        exp_v = c.get("expected_verdict", "PASS").upper()
        clf = c.get("classification", "TN").upper()

        if exp_v == "PASS":
            b["passCount"] += 1
        else:
            b["failCount"] += 1

        if clf == "TP":
            b["truePositives"] += 1
        elif clf == "FP":
            b["falsePositives"] += 1
        elif clf == "TN":
            b["trueNegatives"] += 1
        elif clf == "FN":
            b["falseNegatives"] += 1

    per_category_metrics = []
    for cat_id, b in category_buckets.items():
        if b["total"] > 0:
            acc = ((b["truePositives"] + b["trueNegatives"]) / b["total"] * 100.0) if b["total"] > 0 else 0.0
            rec = (b["truePositives"] / (b["truePositives"] + b["falseNegatives"]) * 100.0) if (b["truePositives"] + b["falseNegatives"]) > 0 else (100.0 if b["failCount"] == 0 else 0.0)
            b["accuracy"] = round(acc, 2)
            b["recall"] = round(rec, 2)
            per_category_metrics.append(b)

    # 5. Detection-Method Matrix for Every Benchmark Case
    detection_matrix = []
    for c in case_results:
        c_detecting = [t.lower().replace("-", "_") for t in c.get("detecting_tools", [])]
        c_expected = [t.lower().replace("-", "_") for t in c.get("expected_tools", [])]

        active_tools_map = {}
        expected_tools_map = {}

        for tool_def in CANONICAL_TOOLS:
            tool_id = tool_def["id"]
            aliases = tool_def["aliases"]
            active_tools_map[tool_id] = any(alias in c_detecting for alias in aliases)
            expected_tools_map[tool_id] = any(alias in c_expected for alias in aliases)

        detection_matrix.append({
            "caseId": c.get("case_id"),
            "language": c.get("language"),
            "category": _normalize_category_key(c.get("bug_category", "")),
            "categoryDisplayName": CATEGORY_DISPLAY_NAMES.get(c.get("bug_category", ""), c.get("bug_category", "")),
            "expectedVerdict": c.get("expected_verdict"),
            "actualVerdict": c.get("actual_verdict"),
            "classification": c.get("classification"),
            "severity": c.get("severity"),
            "executionTimeMs": c.get("execution_time_ms", 0.0),
            "isCorrect": c.get("is_correct", True),
            "detectedBy": active_tools_map,
            "expectedFrom": expected_tools_map,
            "findingsCount": len(c.get("findings", [])),
        })

    return {
        "metadata": {
            "title": "AI Code Verification SaaS - Evaluation Dashboard",
            "benchmarkName": benchmark_name,
            "generatedAt": eval_timestamp,
            "schemaVersion": "1.0.0",
        },
        "summary": summary,
        "performance": performance,
        "perToolMetrics": per_tool_metrics,
        "perCategoryMetrics": per_category_metrics,
        "detectionMatrix": detection_matrix,
    }


def generate_dashboard_json_file(
    input_source: str | Path | dict[str, Any],
    output_file: Optional[str | Path] = None,
) -> str:
    """
    Convenience helper that loads benchmark results or evaluates a dataset
    and produces formatted JSON.
    """
    if isinstance(input_source, (str, Path)):
        in_path = Path(input_source)
        data = json.loads(in_path.read_text(encoding="utf-8"))
        if "cases" in data and "metrics" not in data:
            evaluated_report = evaluate_dataset(data)
            dashboard_data = generate_react_dashboard_data(evaluated_report)
        else:
            dashboard_data = generate_react_dashboard_data(data)
    else:
        dashboard_data = generate_react_dashboard_data(input_source)

    formatted_json = json.dumps(dashboard_data, indent=2)

    if output_file:
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(formatted_json, encoding="utf-8")

    return formatted_json


# ==============================================================================
# 3. UNIT TESTS
# ==============================================================================

class TestEvaluationReport(unittest.TestCase):
    """Unit test suite verifying React dashboard data generation."""

    def setUp(self) -> None:
        self.mock_report_dict = {
            "benchmark_name": "Mock Dashboard Suite",
            "timestamp": "2026-08-22T16:00:00Z",
            "metrics": {
                "total_cases": 2,
                "passed_cases": 1,
                "failed_cases": 1,
                "true_positives": 1,
                "false_positives": 0,
                "true_negatives": 1,
                "false_negatives": 0,
                "accuracy": 100.0,
                "precision": 100.0,
                "recall": 100.0,
                "f1_score": 100.0,
            },
            "timing": {
                "total_time_ms": 10.5,
                "avg_time_ms": 5.25,
                "median_time_ms": 5.25,
                "min_time_ms": 2.0,
                "max_time_ms": 8.5,
            },
            "case_results": [
                {
                    "case_id": "MOCK-001",
                    "language": "cpp",
                    "bug_category": "rfid_iot_authentication",
                    "expected_verdict": "FAIL",
                    "actual_verdict": "FAIL",
                    "classification": "TP",
                    "severity": "critical",
                    "execution_time_ms": 8.5,
                    "detecting_tools": ["rfid_domain_rule"],
                    "expected_tools": ["rfid_domain_rule"],
                    "findings": [{"rule_id": "RFID-01"}],
                    "is_correct": True,
                },
                {
                    "case_id": "MOCK-002",
                    "language": "python",
                    "bug_category": "authentication",
                    "expected_verdict": "PASS",
                    "actual_verdict": "PASS",
                    "classification": "TN",
                    "severity": "info",
                    "execution_time_ms": 2.0,
                    "detecting_tools": [],
                    "expected_tools": [],
                    "findings": [],
                    "is_correct": True,
                },
            ],
        }

    def test_summary_and_performance_metrics(self) -> None:
        """Verifies summary metrics structure and performance values."""
        dashboard = generate_react_dashboard_data(self.mock_report_dict)

        self.assertIn("summary", dashboard)
        self.assertIn("performance", dashboard)
        self.assertEqual(dashboard["summary"]["totalCases"], 2)
        self.assertEqual(dashboard["summary"]["precision"], 100.0)
        self.assertEqual(dashboard["performance"]["averageExecutionTimeMs"], 5.25)
        self.assertEqual(dashboard["performance"]["maximumExecutionTimeMs"], 8.5)

    def test_per_tool_metrics(self) -> None:
        """Verifies tool coverage calculation for canonical tools."""
        dashboard = generate_react_dashboard_data(self.mock_report_dict)
        tools = {t["id"]: t for t in dashboard["perToolMetrics"]}

        self.assertIn("domain_rules", tools)
        self.assertEqual(tools["domain_rules"]["detectedCount"], 1)
        self.assertEqual(tools["domain_rules"]["expectedCount"], 1)
        self.assertEqual(tools["domain_rules"]["coveragePct"], 100.0)

        self.assertIn("ruff", tools)
        self.assertEqual(tools["ruff"]["detectedCount"], 0)

    def test_per_category_metrics(self) -> None:
        """Verifies category breakdown aggregation."""
        dashboard = generate_react_dashboard_data(self.mock_report_dict)
        cats = {c["category"]: c for c in dashboard["perCategoryMetrics"]}

        self.assertIn("rfid", cats)
        self.assertEqual(cats["rfid"]["total"], 1)
        self.assertEqual(cats["rfid"]["accuracy"], 100.0)

        self.assertIn("authentication", cats)
        self.assertEqual(cats["authentication"]["total"], 1)
        self.assertEqual(cats["authentication"]["passCount"], 1)

    def test_detection_matrix_mapping(self) -> None:
        """Verifies case-by-case detection matrix."""
        dashboard = generate_react_dashboard_data(self.mock_report_dict)
        matrix = dashboard["detectionMatrix"]

        self.assertEqual(len(matrix), 2)
        self.assertEqual(matrix[0]["caseId"], "MOCK-001")
        self.assertTrue(matrix[0]["detectedBy"]["domain_rules"])
        self.assertFalse(matrix[0]["detectedBy"]["ruff"])
        self.assertEqual(matrix[0]["findingsCount"], 1)


# ==============================================================================
# 4. CLI RUNNER
# ==============================================================================

if __name__ == "__main__":
    parser_cli = argparse.ArgumentParser(
        description="Transform benchmark evaluation results into React-dashboard JSON."
    )
    parser_cli.add_argument(
        "--input",
        type=str,
        default="./benchmark/results.json",
        help="Path to evaluation results JSON or benchmark dataset JSON (default: ./benchmark/results.json)",
    )
    parser_cli.add_argument(
        "--output",
        type=str,
        default="./benchmark/dashboard_data.json",
        help="Path to save React-ready dashboard JSON (default: ./benchmark/dashboard_data.json)",
    )
    parser_cli.add_argument(
        "--test",
        action="store_true",
        help="Execute unit test suite",
    )

    args = parser_cli.parse_args()

    if args.test:
        print("[+] Running EvaluationReport unit tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestEvaluationReport)
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
        sys.exit(0)

    in_path = Path(args.input)
    if not in_path.exists():
        in_path = Path("./benchmark/benchmark_dataset.json")

    print(f"[+] Transforming evaluation results from: '{in_path}'")
    out_json = generate_dashboard_json_file(in_path, args.output)

    print(f"[+] Successfully generated React dashboard JSON: '{args.output}'")
    print("\n--- SAMPLE DASHBOARD PAYLOAD PREVIEW ---")
    data_preview = json.loads(out_json)
    print(json.dumps({
        "summary": data_preview["summary"],
        "performance": data_preview["performance"],
        "perToolMetrics": data_preview["perToolMetrics"][:3],
        "perCategoryMetrics": data_preview["perCategoryMetrics"][:3],
        "sampleMatrixRow": data_preview["detectionMatrix"][0] if data_preview["detectionMatrix"] else {},
    }, indent=2))
