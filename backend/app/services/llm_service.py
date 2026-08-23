from typing import Any

from app.core.config import settings
from app.core.logging import logger

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class LLMService:
    """Service to interface with Gemini LLM for PR comprehension and evidence explanation."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._initialized = False
        self.client = None
        if self.api_key and GEMINI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self._initialized = True
            except Exception as e:
                logger.warning(f"Failed to configure Gemini LLM: {e}")

    async def explain_verification_evidence(
        self,
        pr_metadata: dict[str, Any],
        diff: str | None,
        evidence: dict[str, Any],
        findings: list[dict[str, Any]],
        verdict: str,
        score: float
    ) -> str:
        """
        Generate a clear, human-readable narrative explaining the deterministic evidence.
        Strictly grounds the explanation on verified findings and test outcomes.
        """
        if not self._initialized:
            return self._generate_fallback_explanation(pr_metadata, evidence, findings, verdict, score)

        prompt = f"""
You are the Evidence Explanation Engine of an automated AI code verification system.
Your job is to explain the verification results to developers clearly, neutrally, and accurately based STRICTLY on the evidence provided below.

CRITICAL INSTRUCTIONS:
1. Do NOT invent findings or test results not listed in the evidence.
2. Clearly state the verdict ({verdict}) and score ({score}/100).
3. Summarize the changes in the Pull Request.
4. Detail the test outcomes, security scan findings, and static analysis results.
5. Provide actionable recommendations if issues were detected.

PULL REQUEST:
Title: {pr_metadata.get('title')}
Description: {pr_metadata.get('description', 'N/A')}
Author: {pr_metadata.get('author')}

EVIDENCE SUMMARY:
Tests: {evidence.get('tests')}
Security Findings: {evidence.get('security')}
Static Analysis: {evidence.get('static_analysis')}
Regressions: {evidence.get('regression')}

DETAILED FINDINGS:
{findings}

DIFF SNIPPET (truncated):
{diff[:2000] if diff else 'N/A'}
"""
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API explanation generation failed: {e}")
            return self._generate_fallback_explanation(pr_metadata, evidence, findings, verdict, score)

    def _generate_fallback_explanation(
        self,
        pr_metadata: dict[str, Any],
        evidence: dict[str, Any],
        findings: list[dict[str, Any]],
        verdict: str,
        score: float
    ) -> str:
        """Deterministic, grounded explanation generator for offline or fallback operation."""
        tests = evidence.get("tests", {})
        sec = evidence.get("security", {})
        static = evidence.get("static_analysis", {})
        regression = evidence.get("regression", {})

        lines = [
            f"### Verification Verdict: **{verdict}** (Score: {score}/100)",
            "",
            f"**PR Overview:** #{pr_metadata.get('number', 'N/A')} - *{pr_metadata.get('title', 'Unknown')}* by @{pr_metadata.get('author', 'author')}",
            "",
            "#### Evidence Breakdown:",
            f"- **Test Suite:** {tests.get('passed', 0)} passed, {tests.get('failed', 0)} failed, {tests.get('errors', 0)} errors (Total: {tests.get('total', 0)})",
            f"- **Security Scans:** {sec.get('critical', 0)} critical, {sec.get('high', 0)} high, {sec.get('medium', 0)} medium, {sec.get('low', 0)} low vulnerabilities",
            f"- **Static Analysis:** {static.get('errors', 0)} errors, {static.get('warnings', 0)} warnings ({static.get('total_issues', 0)} total issues)",
            f"- **Regression Status:** {'Detected' if regression.get('detected') else 'None detected'}",
        ]

        if findings:
            lines.append("\n#### Notable Findings:")
            for f in findings[:10]:  # Highlight top 10 findings
                lines.append(f"- `[{f.get('severity', '').upper()}]` {f.get('type')}: {f.get('message')} (File: `{f.get('file')}:{f.get('line')}`)")

        if verdict == "VERIFIED":
            lines.append("\n**Conclusion:** All automated test suites passed with no critical security or static analysis regressions. The change is verified.")
        elif verdict == "REJECTED":
            lines.append("\n**Conclusion:** Blocking defects detected. Ensure all regressions and security findings are addressed before merging.")
        elif verdict == "VERIFIED_WITH_RISKS":
            lines.append("\n**Conclusion:** The code functions but contains non-blocking warnings or potential risks requiring reviewer attention.")
        else:
            lines.append("\n**Conclusion:** Inconclusive evidence. Ensure tests are present to validate the change.")

        return "\n".join(lines)


llm_service = LLMService()
