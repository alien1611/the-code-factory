# AI Code Verification SaaS - Evaluation Benchmark Dataset

A ground-truth benchmark suite designed to evaluate multi-layered, complementary code verification methods across AST parsers, static linters, semantic rule engines, dependency scanners, test generators, domain-specific rules, and LLM verification agents.

---

## 📁 Directory Structure

```text
benchmark/
├── benchmark_dataset.json   # Machine-readable ground truth dataset (17 cases)
├── evaluate_benchmark.py    # Automated evaluator & metrics reporter
└── README.md                # Benchmark documentation & specifications
```

---

## 🎯 Verification Categories & Distribution

| Category | Description | Safe (PASS) | Flawed (FAIL) | Total |
| :--- | :--- | :---: | :---: | :---: |
| **Authentication** | Constant-time comparisons, token verification | 1 | 1 | 2 |
| **Authorization** | Broken object level access (BOLA/IDOR), tenant checks | 1 | 1 | 2 |
| **Input Validation** | SQL injection, untrusted query parameters | 1 | 1 | 2 |
| **Security** | Command injection, insecure deserialization | 0 | 2 | 2 |
| **Logic Errors** | Off-by-one boundary checks, excessive refund flaws | 1 | 1 | 2 |
| **Dependency Vulnerabilities** | Outdated/vulnerable third-party package manifests | 1 | 1 | 2 |
| **RFID / IoT Authentication** | Hardware UID extraction, whitelist validation, relay control | 2 | 3 | 5 |
| **TOTAL** | | **7** | **10** | **17** |

---

## 🔬 Complementary Tool Detection Matrix

This benchmark is specifically architected to demonstrate that **no single verification method is sufficient on its own**. Different classes of flaws require complementary tools:

```text
┌─────────────────────────┬─────────────────────────────────────────────────────────────────┐
│ Verification Layer      │ Target Flaw Classes                                             │
├─────────────────────────┼─────────────────────────────────────────────────────────────────┤
│ Static Analysis / Linter│ Syntax errors, simple taint patterns, deprecated/unsafe calls   │
│ Semgrep Rules           │ Structural AST antipatterns, missing guards, hardcoded tokens   │
│ Dependency Scanner      │ Known CVEs/GHSA in requirements.txt and package.json            │
│ Domain-Specific Rules   │ IoT/RFID 5-step authentication invariants, state machines       │
│ Generated Unit Tests    │ Boundary/logic errors, mathematical errors, off-by-one limits   │
│ LLM Reasoning Agent     │ Complex business logic flaws, IDOR, multi-file intent violation │
└─────────────────────────┴─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Benchmark Case Schema

Each case in [`benchmark_dataset.json`](./benchmark_dataset.json) follows this standard schema:

```json
{
  "case_id": "BENCH-RFID-014",
  "language": "cpp",
  "requirement": "Card presence must not grant access without reading and validating UID serial.",
  "source_code": "...",
  "expected_verdict": "FAIL",
  "expected_findings": [
    {
      "rule_id": "RFID-001-UNAUTHORIZED-UNLOCK",
      "severity": "critical",
      "message": "Critical RFID flaw: Door unlock triggered immediately on card presence without reading or checking UID."
    }
  ],
  "bug_category": "rfid_iot_authentication",
  "severity": "critical",
  "detection_methods_expected": ["rfid_domain_rule", "semgrep", "llm_reasoning"]
}
```

---

## 🚀 Running Benchmark Evaluation

```bash
# Run the automated benchmark evaluation
python benchmark/evaluate_benchmark.py

# Evaluate a custom dataset file
python benchmark/evaluate_benchmark.py --dataset ./benchmark/benchmark_dataset.json
```
