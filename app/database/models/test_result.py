import uuid

from app.database.base import Base
from sqlalchemy import Column, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship


class TestResult(Base):
    __tablename__ = "test_results"
    __test__ = False

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    verification_id = Column(String(36), ForeignKey("verifications.id", ondelete="CASCADE"), nullable=False, index=True)
    
    test_name = Column(String(512), nullable=False)
    # Status: passed, failed, skipped, error
    status = Column(String(50), nullable=False)
    duration = Column(Float, nullable=True)
    output = Column(Text, nullable=True)

    verification = relationship("Verification", back_populates="test_results")

    def __repr__(self):
        return f"<TestResult {self.test_name}: {self.status}>"
