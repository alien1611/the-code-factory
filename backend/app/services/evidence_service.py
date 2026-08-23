from typing import Any

from app.core.logging import logger
from app.integrations.analysis_contract import AnalysisFinding


class EvidenceService:
    """
    Normalizes multi-source evidence and executes the Deterministic Verification Engine.
    Evaluates tests, security scans, static analysis, and regression signals.
    """

    def aggregate_evidence(
        self,
        docker_artifacts: dict[str, Any],
        custom_findings: list[AnalysisFinding],
        metadata: dict[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Aggregate and normalize all raw artifacts into structured evidence, findings, and test results.
        """
        findings: list[dict[str, Any]] = []
        test_results: list[dict[str, Any]] = []

        # 1. Process Pytest Artifacts
        pytest_data = docker_artifacts.get("pytest", {})
        pytest_summary = pytest_data.get("summary", {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0})
        for t in pytest_data.get("tests", []):
            test_results.append({
                "test_name": t.get("name"),
                "status": t.get("status"),
                "duration": t.get("duration", 0.0),
                "output": t.get("output", "")
            })

        # 2. Process Ruff Static Analysis Artifacts
        ruff_data = docker_artifacts.get("ruff", [])
        ruff_errors = 0
        ruff_warnings = 0
        for r in ruff_data:
            code = r.get("code", "E")
            severity = "high" if code.startswith("E9") or code.startswith("F") else "medium"
            if severity == "high":
                ruff_errors += 1
            else:
                ruff_warnings += 1
            
            loc = r.get("location", {})
            findings.append({
                "type": "static_analysis",
                "severity": severity,
                "file": r.get("filename", ""),
                "line": loc.get("row"),
                "message": f"[{r.get('code')}] {r.get('message')}",
                "evidence": {"tool": "ruff", "details": r}
            })

        # 3. Process Bandit Security Scan Artifacts
        bandit_data = docker_artifacts.get("bandit", {})
        bandit_results = bandit_data.get("results", [])
        sec_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for b in bandit_results:
            b_severity = b.get("issue_severity", "LOW").lower()
            b_conf = b.get("issue_confidence", "LOW").lower()
            
            # Map severity
            if b_severity == "high" and b_conf in ["high", "medium"]:
                severity = "critical" if b_conf == "high" else "high"
            elif b_severity == "medium":
                severity = "medium"
            else:
                severity = "low"

            sec_counts[severity] = sec_counts.get(severity, 0) + 1
            findings.append({
                "type": "security",
                "severity": severity,
                "file": b.get("filename", ""),
                "line": b.get("line_number"),
                "message": f"[{b.get('test_id')}] {b.get('issue_text')}",
                "evidence": {"tool": "bandit", "confidence": b_conf, "more_info": b.get("more_info")}
            })

        # 4. Integrate Custom Findings from Analysis Modules
        for cf in custom_findings:
            findings.append({
                "type": cf.type,
                "severity": cf.severity,
                "file": cf.file,
                "line": cf.line,
                "message": cf.message,
                "evidence": cf.evidence
            })
            if cf.type == "security":
                sec_counts[cf.severity] = sec_counts.get(cf.severity, 0) + 1

        # 5. Build Normalized Evidence Map
        normalized_evidence = {
            "tests": {
                "total": pytest_summary.get("total", 0),
                "passed": pytest_summary.get("passed", 0),
                "failed": pytest_summary.get("failed", 0),
                "errors": pytest_summary.get("errors", 0),
                "skipped": pytest_summary.get("skipped", 0)
            },
            "static_analysis": {
                "errors": ruff_errors,
                "warnings": ruff_warnings,
                "total_issues": len(ruff_data)
            },
            "security": sec_counts,
            "regression": {
                "detected": pytest_summary.get("failed", 0) > 0 or pytest_summary.get("errors", 0) > 0,
                "failed_tests": [t["test_name"] for t in test_results if t["status"] in ["failed", "error"]]
            },
            "metadata": metadata
        }

        return normalized_evidence, findings, test_results

    def compute_verdict(self, evidence: dict[str, Any], findings: list[dict[str, Any]]) -> tuple[str, float]:
        """
        Deterministic Verification Engine.
        Returns (Verdict, Score).
        Verdicts:
          - REJECTED
          - VERIFIED
          - VERIFIED_WITH_RISKS
          - INCONCLUSIVE
        """
        tests = evidence.get("tests", {})
        security = evidence.get("security", {})
        static = evidence.get("static_analysis", {})
        regression = evidence.get("regression", {})

        total_tests = tests.get("total", 0)
        failed_tests = tests.get("failed", 0) + tests.get("errors", 0)
        passed_tests = tests.get("passed", 0)

        critical_sec = security.get("critical", 0)
        high_sec = security.get("high", 0)
        medium_sec = security.get("medium", 0)

        # Rule 1: Fatal / Critical Blockers -> REJECTED
        if critical_sec > 0:
            logger.info(f"Verification REJECTED: {critical_sec} critical security issue(s) detected.")
            return "REJECTED", 0.0

        if regression.get("detected", False) and failed_tests > 0:
            logger.info(f"Verification REJECTED: {failed_tests} test failures/regressions detected.")
            return "REJECTED", 20.0

        # Rule 2: High security risks -> REJECTED
        if high_sec > 0:
            logger.info(f"Verification REJECTED: {high_sec} high severity security issues detected.")
            return "REJECTED", 35.0

        # Rule 3: Static analysis fatal syntax/import errors -> REJECTED
        if static.get("errors", 0) > 0:
            logger.info("Verification REJECTED: Fatal static analysis / syntax errors detected.")
            return "REJECTED", 30.0

        # Calculate Score
        base_score = 100.0
        if total_tests > 0:
            test_rate = (passed_tests / total_tests) * 60.0  # 60 pts from tests
            base_score = 40.0 + test_rate
        else:
            # No tests found
            base_score = 70.0  # Baseline when static/sec are clean

        # Deduct penalties for warnings
        base_score -= min(30.0, medium_sec * 10.0 + static.get("warnings", 0) * 2.0)
        score = max(0.0, min(100.0, base_score))

        # Rule 4: Clean passes -> VERIFIED
        if medium_sec == 0 and static.get("warnings", 0) <= 2:
            if total_tests == 0:
                # No tests run, only static/security passed -> VERIFIED_WITH_RISKS or INCONCLUSIVE
                return "INCONCLUSIVE", round(score, 1)
            return "VERIFIED", round(score, 1)

        # Rule 5: Non-critical warnings -> VERIFIED_WITH_RISKS
        if medium_sec > 0 or static.get("warnings", 0) > 2:
            return "VERIFIED_WITH_RISKS", round(score, 1)

        return "INCONCLUSIVE", round(score, 1)


evidence_service = EvidenceService()
