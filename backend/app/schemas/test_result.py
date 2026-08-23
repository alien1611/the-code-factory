
from pydantic import BaseModel, ConfigDict


class TestResultBase(BaseModel):
    __test__ = False
    test_name: str
    status: str  # passed, failed, skipped, error
    duration: float | None = None
    output: str | None = None


class TestResultCreate(TestResultBase):
    pass


class TestResultResponse(TestResultBase):
    id: str
    verification_id: str

    model_config = ConfigDict(from_attributes=True)
