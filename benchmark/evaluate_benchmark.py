"""
evaluate_benchmark.py - Benchmark Harness & Evaluator for AI Code Verification SaaS

Loads ground-truth benchmark cases from benchmark_dataset.json and measures:
1. Verdict accuracy (PASS vs FAIL classification)
2. Precision, Recall, and F1-score across flaw categories
3. Complementary tool coverage (Static Analysis, Semgrep, Dependency Scanner, Domain Rules, LLM Reasoning)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any

# Ensure parent directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import FileMetadata, Finding
from rfid_verifier import verify_rfid_authentication


@dataclass
class EvaluationMetrics:
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    category_breakdown: dict[str, dict[str, int]] = field(default_factory=dict)
    detection_method_distribution: dict[str, int] = field(default_factory=dict)

    def compute_scores(self) -> dict[str, float]:
        tp = self.true_positives
        fp = self.false_positives
        fn = self.false_negatives
        tn = self.true_negatives

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        accuracy = ((tp + tn) / (tp + tn + fp + fn)) if (tp + tn + fp + fn) > 0 else 1.0

        return {
            "accuracy": round(accuracy * 100, 2),
            "precision": round(precision * 100, 2),
            "recall": round(recall * 100, 2),
            "f1_score": round(f1 * 100, 2),
        }


def load_benchmark_dataset(dataset_path: str | Path) -> dict[str, Any]:
    """Loads and validates the benchmark JSON file."""
    path = Path(dataset_path)
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark dataset not found at: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_benchmark_analysis(dataset: dict[str, Any]) -> EvaluationMetrics:
    """
    Evaluates benchmark test cases against available local verification engines
    (such as rfid_verifier.py) and tallies tool detection ground truth.
    """
    metrics = EvaluationMetrics(total_cases=len(dataset.get("cases", [])))

    for case in dataset.get("cases", []):
        case_id = case["case_id"]
        cat = case["bug_category"]
        expected_verdict = case["expected_verdict"]
        methods = case.get("detection_methods_expected", [])

        # Initialize breakdown
        if cat not in metrics.category_breakdown:
            metrics.category_breakdown[cat] = {"PASS": 0, "FAIL": 0}
        metrics.category_breakdown[cat][expected_verdict] += 1

        # Track tool requirements
        for m in methods:
            metrics.detection_method_distribution[m] = (
                metrics.detection_method_distribution.get(m, 0) + 1
            )

        if expected_verdict == "PASS":
            metrics.passed_cases += 1
        else:
            metrics.failed_cases += 1

        # Execute local verification if RFID domain case
        if cat == "rfid_iot_authentication":
            meta = FileMetadata(path=f"{case_id}.ino", language="C++")
            findings = verify_rfid_authentication(case["source_code"], meta)
            actual_verdict = "FAIL" if len(findings) > 0 else "PASS"

            if expected_verdict == "FAIL" and actual_verdict == "FAIL":
                metrics.true_positives += 1
            elif expected_verdict == "PASS" and actual_verdict == "PASS":
                metrics.true_negatives += 1
            elif expected_verdict == "PASS" and actual_verdict == "FAIL":
                metrics.false_positives += 1
            elif expected_verdict == "FAIL" and actual_verdict == "PASS":
                metrics.false_negatives += 1

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate AI Verification Benchmark Dataset.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="./benchmark/benchmark_dataset.json",
        help="Path to benchmark JSON dataset",
    )

    args = parser.parse_args()
    data = load_benchmark_dataset(args.dataset)
    metrics = run_benchmark_analysis(data)

    print("=" * 70)
    print("AI CODE VERIFICATION SAAS - BENCHMARK EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Dataset Name       : {data.get('benchmark_name')}")
    print(f"Total Test Cases   : {metrics.total_cases}")
    print(f" - Safe (PASS)     : {metrics.passed_cases}")
    print(f" - Flawed (FAIL)   : {metrics.failed_cases}")

    print("\n" + "-" * 70)
    print("CATEGORY BREAKDOWN:")
    print("-" * 70)
    for cat, counts in sorted(metrics.category_breakdown.items()):
        total = counts["PASS"] + counts["FAIL"]
        print(f" * {cat:<28}: {total:>2} cases (PASS: {counts['PASS']}, FAIL: {counts['FAIL']})")

    print("\n" + "-" * 70)
    print("COMPLEMENTARY DETECTION METHOD REQUIREMENTS:")
    print("-" * 70)
    for tool, count in sorted(metrics.detection_method_distribution.items(), key=lambda x: -x[1]):
        print(f" * {tool:<28}: {count:>2} benchmark cases")

    print("\n" + "-" * 70)
    print("RFID VERIFIER LOCAL ENGINE VALIDATION (Ground Truth vs Engine):")
    print("-" * 70)
    rfid_scores = metrics.compute_scores()
    print(f" * True Positives  (TP) : {metrics.true_positives}")
    print(f" * True Negatives  (TN) : {metrics.true_negatives}")
    print(f" * False Positives (FP) : {metrics.false_positives}")
    print(f" * False Negatives (FN) : {metrics.false_negatives}")
    print(f" * Precision            : {rfid_scores['precision']}%")
    print(f" * Recall               : {rfid_scores['recall']}%")
    print(f" * F1-Score             : {rfid_scores['f1_score']}%")
    print("=" * 70)
