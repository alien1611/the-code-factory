import uuid
from datetime import datetime

from app.database.base import Base
from sqlalchemy import BigInteger, Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    github_id = Column(BigInteger, unique=True, index=True, nullable=True)
    owner = Column(String(255), index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    full_name = Column(String(512), unique=True, index=True, nullable=False)
    private = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    pull_requests = relationship("PullRequest", back_populates="repository", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Repository {self.full_name}>"
