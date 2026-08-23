from datetime import datetime, timedelta
from app.database.models.user_quota import UserQuota
from app.services.quota_service import quota_service


def test_quota_initialization_and_deduction(db_session):
    username = "testuser123"
    
    # 1. First get/create gives 100 limit and 0 used
    quota = quota_service.get_or_create_quota(username, db_session)
    assert quota.github_username == username
    assert quota.monthly_limit == 100
    assert quota.credits_used == 0
    assert quota.credits_remaining == 100

    # 2. Deduct credit
    allowed, remaining, msg = quota_service.check_and_deduct(username, db_session, cost=5)
    assert allowed is True
    assert remaining == 95

    # 3. Check summary
    summary = quota_service.get_quota_summary(username, db_session)
    assert summary["credits_used"] == 5
    assert summary["credits_remaining"] == 95
    assert summary["monthly_limit"] == 100


def test_quota_30_day_auto_regeneration(db_session):
    username = "regenuser"
    
    # 1. Create and exhaust quota
    quota = quota_service.get_or_create_quota(username, db_session)
    quota.credits_used = 100
    db_session.commit()
    assert quota.credits_remaining == 0

    # Verify further deduction is rejected
    allowed, rem, msg = quota_service.check_and_deduct(username, db_session, cost=1)
    assert allowed is False
    assert rem == 0
    assert "Monthly quota limit" in msg

    # 2. Simulate 31 days elapsed
    quota.next_reset_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()

    # 3. Next check triggers automatic regeneration
    quota_after = quota_service.get_or_create_quota(username, db_session)
    assert quota_after.credits_used == 0
    assert quota_after.credits_remaining == 100
    assert quota_after.next_reset_at > datetime.utcnow()
