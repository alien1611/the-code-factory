from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AnalysisInput(BaseModel):
    """Normalized input payload provided to analysis modules and plugins."""
    verification_id: str
    repository: str
    commit_sha: str
    workspace: str
    changed_files: list[dict[str, Any]] = Field(default_factory=list)
    diff: str | None = None
    pr_metadata: dict[str, Any] | None = Field(default_factory=dict)


class AnalysisFinding(BaseModel):
    """Normalized finding produced by static, security, or regression tools."""
    type: str  # e.g., 'security', 'static_analysis', 'regression', 'dependency'
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    file: str
    line: int | None = None
    message: str
    evidence: dict[str, Any] | None = Field(default_factory=dict)


class AnalysisOutput(BaseModel):
    """Normalized output contract returned by analysis engines."""
    status: str = "completed"  # 'completed', 'failed', 'partial'
    findings: list[AnalysisFinding] = Field(default_factory=list)
    tests: dict[str, Any] = Field(default_factory=dict)
    security: dict[str, Any] = Field(default_factory=dict)
    static_analysis: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisModuleInterface(ABC):
    """Abstract interface that all verification teammate modules must implement."""

    @abstractmethod
    async def analyze(self, input_data: AnalysisInput) -> AnalysisOutput:
        """Run analysis on the prepared workspace and PR diff."""
