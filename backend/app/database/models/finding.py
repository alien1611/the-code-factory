import uuid

from app.database.base import Base
from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    verification_id = Column(String(36), ForeignKey("verifications.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Type: static_analysis, security, regression, dependency, syntax, logic
    type = Column(String(50), nullable=False, index=True)
    
    # Severity: critical, high, medium, low, info
    severity = Column(String(50), nullable=False, index=True)
    
    file = Column(String(512), nullable=False)
    line = Column(Integer, nullable=True)
    message = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)

    verification = relationship("Verification", back_populates="findings")

    def __repr__(self):
        return f"<Finding [{self.severity}] {self.type}: {self.file}:{self.line}>"
