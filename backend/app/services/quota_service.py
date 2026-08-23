from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.database.models.user_quota import UserQuota


class QuotaService:
    """Manages monthly token/verification quotas and automatic 30-day regeneration per GitHub user."""

    DEFAULT_MONTHLY_LIMIT = 100

    def get_or_create_quota(self, username: str, db: Session) -> UserQuota:
        """Fetch user quota record, automatically regenerating credits if 30 days have elapsed."""
        clean_user = username.strip().lower() if username else "alien1611"
        quota = db.query(UserQuota).filter(UserQuota.github_username == clean_user).first()
        now = datetime.utcnow()

        if not quota:
            quota = UserQuota(
                github_username=clean_user,
                plan_tier="free",
                monthly_limit=self.DEFAULT_MONTHLY_LIMIT,
                credits_used=0,
                last_reset_at=now,
                next_reset_at=now + timedelta(days=30)
            )
            db.add(quota)
            db.commit()
            db.refresh(quota)
            logger.info(f"[QuotaService] Initialized new monthly quota for user @{clean_user} (100 credits)")
        elif quota.is_expired():
            # 🔄 30-Day Auto-Regeneration Trigger
            quota.reset_cycle()
            db.commit()
            db.refresh(quota)
            logger.info(f"[QuotaService] Automatically regenerated 100 monthly credits for @{clean_user}")

        return quota

    def check_and_deduct(self, username: str, db: Session, cost: int = 1) -> tuple[bool, int, str]:
        """
        Check if user has remaining credits and deduct.
        Returns: (success: bool, remaining_credits: int, message: str)
        """
        quota = self.get_or_create_quota(username, db)
        
        if quota.credits_used + cost > quota.monthly_limit:
            reset_str = quota.next_reset_at.strftime("%B %d, %Y")
            return False, quota.credits_remaining, f"Monthly quota limit ({quota.monthly_limit} credits) reached. Credits automatically regenerate on {reset_str}."

        quota.credits_used += cost
        db.commit()
        db.refresh(quota)
        return True, quota.credits_remaining, "OK"

    def get_quota_summary(self, username: str, db: Session) -> dict[str, Any]:
        """Get formatted quota status for frontend rendering."""
        quota = self.get_or_create_quota(username, db)
        days_until_reset = max(0, (quota.next_reset_at - datetime.utcnow()).days)

        return {
            "github_username": quota.github_username,
            "plan_tier": quota.plan_tier,
            "monthly_limit": quota.monthly_limit,
            "credits_used": quota.credits_used,
            "credits_remaining": quota.credits_remaining,
            "percentage_used": round((quota.credits_used / quota.monthly_limit) * 100, 1),
            "last_reset_at": quota.last_reset_at.isoformat(),
            "next_reset_at": quota.next_reset_at.isoformat(),
            "days_until_reset": days_until_reset
        }


quota_service = QuotaService()
