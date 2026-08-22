from typing import Any

from pydantic import BaseModel, ConfigDict


class FindingBase(BaseModel):
    type: str  # static_analysis, security, regression, dependency
    severity: str  # critical, high, medium, low, info
    file: str
    line: int | None = None
    message: str
    evidence: dict[str, Any] | None = None


class FindingCreate(FindingBase):
    pass


class FindingResponse(FindingBase):
    id: str
    verification_id: str

    model_config = ConfigDict(from_attributes=True)
