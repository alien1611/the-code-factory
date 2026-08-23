# Verification Benchmark Evaluation Dashboard
**Dataset:** `AI Code Verification SaaS Evaluation Dataset` | **Evaluated At:** `2026-08-22T16:03:20.426343+00:00`

## Key Performance Indicators (KPIs)

| Metric | Score | Status | Description |
| :--- | :---: | :---: | :--- |
| **Accuracy** | `58.82%` | [MODERATE] | Overall correctness across all safe and flawed cases |
| **Precision** | `100.0%` | [HIGH] | Freedom from false alarms ($TP / (TP + FP)$) |
| **Recall (Sensitivity)** | `30.0%` | [MODERATE] | Flaw detection coverage ($TP / (TP + FN)$) |
| **F1-Score** | `46.15%` | [MODERATE] | Harmonic balance of precision and recall |

## Confusion Matrix

| | Actual Flaw (Positive) | Actual Safe (Negative) |
| :--- | :---: | :---: |
| **Predicted Flaw (FAIL)** | **True Positive (TP):** `3` | **False Positive (FP):** `0` |
| **Predicted Safe (PASS)** | **False Negative (FN):** `7` | **True Negative (TN):** `7` |

## Verification Latency & Performance

- **Total Benchmark Runtime:** `60071.52 ms`
- **Average Verification Time:** `3533.62 ms / case`
- **Median Verification Time:** `0.00 ms / case`
- **Min / Max Latency:** `0.00 ms` / `60066.36 ms`

## Per-Tool Detection Coverage

| Verification Tool / Method | Detections | Expected Target Cases | Coverage Rate |
| :--- | :---: | :---: | :---: |
| `rfid_domain_rule` | `3` | `3` | `100.0%` |
| `static_analysis` | `0` | `3` | `0.0%` |
| `llm_reasoning` | `0` | `9` | `0.0%` |
| `semgrep` | `0` | `6` | `0.0%` |
| `generated_tests` | `0` | `3` | `0.0%` |
| `dependency_scanner` | `0` | `1` | `0.0%` |

## Category-Specific Performance

| Bug Category | Total Cases | PASS | FAIL | Accuracy | Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `authentication` | `2` | `1` | `1` | `50.0%` | `0.0%` |
| `authorization` | `2` | `1` | `1` | `50.0%` | `0.0%` |
| `dependency_vulnerabilities` | `2` | `1` | `1` | `50.0%` | `0.0%` |
| `input_validation` | `2` | `1` | `1` | `50.0%` | `0.0%` |
| `logic_errors` | `2` | `1` | `1` | `50.0%` | `0.0%` |
| `rfid_iot_authentication` | `5` | `2` | `3` | `100.0%` | `100.0%` |
| `security` | `2` | `0` | `2` | `0.0%` | `0.0%` |