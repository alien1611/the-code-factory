import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, DateTime, Integer, String
from app.database.base import Base


class UserQuota(Base):
    """Tracks monthly verification credits & automatic 30-day token regeneration per GitHub account."""
    __tablename__ = "user_quotas"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    github_username = Column(String(255), unique=True, index=True, nullable=False)
    
    # Tier and monthly allowances
    plan_tier = Column(String(50), default="free", nullable=False)
    monthly_limit = Column(Integer, default=100, nullable=False)
    credits_used = Column(Integer, default=0, nullable=False)
    
    # 30-Day Auto-Regeneration Dates
    last_reset_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    next_reset_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30), nullable=False)

    def is_expired(self) -> bool:
        """Check if 30-day billing cycle has passed."""
        return datetime.utcnow() >= self.next_reset_at

    def reset_cycle(self) -> None:
        """Reset usage and advance next reset date by 30 days."""
        self.credits_used = 0
        self.last_reset_at = datetime.utcnow()
        self.next_reset_at = datetime.utcnow() + timedelta(days=30)

    @property
    def credits_remaining(self) -> int:
        return max(0, self.monthly_limit - self.credits_used)
