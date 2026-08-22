import uuid
from datetime import datetime

from app.database.base import Base
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class Verification(Base):
    __tablename__ = "verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    pull_request_number = Column(Integer, nullable=False, index=True)
    commit_sha = Column(String(64), nullable=False, index=True)
    
    # Status lifecycle: QUEUED, CLONING, PREPARING, ANALYZING, VERIFYING, AGGREGATING, COMPLETED, FAILED
    status = Column(String(50), default="QUEUED", nullable=False, index=True)
    
    # Verdict: VERIFIED, VERIFIED_WITH_RISKS, REJECTED, INCONCLUSIVE
    verdict = Column(String(50), nullable=True, index=True)
    
    # Verification score (0.0 to 100.0 or 0.0 to 1.0)
    score = Column(Float, nullable=True)
    
    # Safe error message if failed
    error = Column(Text, nullable=True)
    
    # Summary explanation / narrative (LLM explanation over deterministic evidence)
    summary = Column(Text, nullable=True)
    
    # Raw normalized evidence stored as JSON
    evidence = Column(JSON, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    repository = relationship("Repository", back_populates="verifications")
    findings = relationship("Finding", back_populates="verification", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="verification", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Verification {self.id} [{self.status}] -> {self.verdict}>"
