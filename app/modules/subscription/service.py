"""
Subscription Service (Hardened)

Atomic, race-condition-safe subscription management.
All tier checks use dynamic query: status='active' AND end_date > NOW().
Supports subscription history (multiple rows per user).

Methods:
- get_effective_subscription() — current active sub with computed fields
- upgrade_subscription() — atomic tier upgrade with FOR UPDATE
- renew_subscription() — atomic renewal extending end_date
- expire_lapsed_subscriptions() — bulk mark expired (for cron)
- get_auto_renewable() — find subs expiring soon with auto_renew=true
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import get_features_for_tier, has_tier_access, TIER_HIERARCHY
from app.core.tier_cache import invalidate_cached_tier
from app.core.logging import get_logger

logger = get_logger(__name__)


def _make_aware(dt):
    """Ensure a datetime is timezone-aware (UTC)."""
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _expires_in_days(end_date) -> int | None:
    """Compute days until expiration. None if no end_date (free tier)."""
    if not end_date:
        return None
    end_dt = _make_aware(end_date)
    delta = end_dt - datetime.now(timezone.utc)
    return max(0, delta.days)


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_effective_subscription(self, user_id: int) -> dict:
        """
        Get the user's EFFECTIVE subscription — only active, non-expired.
        Single query determines tier. No separate expiration check needed.
        """
        result = await self.db.execute(
            text("""
                SELECT id, tier, status, start_date, end_date,
                       billing_provider, auto_renew
                FROM subscriptions
                WHERE user_id = :uid
                  AND status = 'active'
                  AND (end_date IS NULL OR end_date > NOW())
                ORDER BY end_date DESC NULLS FIRST
                LIMIT 1
            """),
            {"uid": user_id}
        )
        row = result.fetchone()

        if not row:
            # No active subscription → free tier
            return {
                "tier": "free",
                "status": "active",
                "features": get_features_for_tier("free"),
                "start_date": None,
                "end_date": None,
                "expires_in_days": None,
                "auto_renew": False,
                "billing_provider": None,
            }

        return {
            "tier": row.tier,
            "status": row.status,
            "features": get_features_for_tier(row.tier),
            "start_date": row.start_date.isoformat() if row.start_date else None,
            "end_date": row.end_date.isoformat() if row.end_date else None,
            "expires_in_days": _expires_in_days(row.end_date),
            "auto_renew": row.auto_renew or False,
            "billing_provider": row.billing_provider,
        }

    async def upgrade_subscription(
        self,
        user_id: int,
        new_tier: str,
        payment_reference: str = None,
        billing_provider: str = None,
        duration_days: int = 30,
    ) -> dict:
        """
        Upgrade a user's subscription tier. Creates a NEW subscription row
        (old one preserved for history). Atomic with FOR UPDATE.
        Idempotent: duplicate payment_reference is rejected.
        """
        if new_tier not in TIER_HIERARCHY:
            raise ValueError(f"Invalid tier: {new_tier}")
        if new_tier == "free":
            raise ValueError("Cannot upgrade to free tier")

        # ── Idempotency guard ──
        if payment_reference:
            dup = await self.db.execute(
                text("SELECT id FROM subscriptions WHERE payment_reference = :ref"),
                {"ref": payment_reference}
            )
            if dup.fetchone():
                logger.warning(f"⚠️ [SUBSCRIPTION] Duplicate payment_reference={payment_reference} for user {user_id}")
                raise ValueError(f"Payment reference '{payment_reference}' already used (idempotency guard)")

        now = datetime.now(timezone.utc)
        new_end = now + timedelta(days=duration_days)

        # Lock current active subscription row (if any)
        result = await self.db.execute(
            text("""
                SELECT id, tier, status, end_date
                FROM subscriptions
                WHERE user_id = :uid
                  AND status = 'active'
                  AND (end_date IS NULL OR end_date > NOW())
                ORDER BY end_date DESC NULLS FIRST
                LIMIT 1
                FOR UPDATE
            """),
            {"uid": user_id}
        )
        existing = result.fetchone()

        if existing:
            current_tier = existing.tier

            # Prevent downgrade while active
            if has_tier_access(current_tier, new_tier) and current_tier != new_tier:
                raise ValueError(
                    f"Cannot downgrade from '{current_tier}' to '{new_tier}'. "
                    f"Current tier is already higher."
                )

            # If upgrading on same tier, extend from current end_date
            if existing.end_date:
                end_dt = _make_aware(existing.end_date)
                if end_dt > now:
                    new_end = end_dt + timedelta(days=duration_days)

            # Mark old subscription as superseded
            await self.db.execute(
                text("UPDATE subscriptions SET status = 'superseded', updated_at = NOW() WHERE id = :sid"),
                {"sid": existing.id}
            )

        # Create NEW subscription row (history preserved)
        await self.db.execute(
            text("""
                INSERT INTO subscriptions
                    (user_id, tier, status, start_date, end_date,
                     payment_reference, billing_provider, auto_renew)
                VALUES (:uid, :tier, 'active', :start, :end, :pref, :bp, FALSE)
            """),
            {
                "uid": user_id,
                "tier": new_tier,
                "start": now,
                "end": new_end,
                "pref": payment_reference,
                "bp": billing_provider or "manual",
            }
        )
        await self.db.commit()

        # ── Instant cache invalidation ──
        await invalidate_cached_tier(user_id)

        logger.info(
            f"🎉 [SUBSCRIPTION] User {user_id} upgraded to '{new_tier}' "
            f"until {new_end.isoformat()}, provider={billing_provider or 'manual'}"
        )

        return {
            "success": True,
            "tier": new_tier,
            "status": "active",
            "features": get_features_for_tier(new_tier),
            "start_date": now.isoformat(),
            "end_date": new_end.isoformat(),
            "expires_in_days": _expires_in_days(new_end),
            "message": f"Successfully upgraded to {new_tier} tier",
        }

    async def renew_subscription(
        self,
        user_id: int,
        payment_reference: str = None,
        duration_days: int = 30,
    ) -> dict:
        """
        Atomically renew a user's subscription.
        - If active + not expired: extends from current end_date
        - If expired: starts fresh from now
        - Uses SELECT FOR UPDATE for race condition safety
        - Idempotent: duplicate payment_reference is rejected
        """
        # ── Idempotency guard ──
        if payment_reference:
            dup = await self.db.execute(
                text("SELECT id FROM subscriptions WHERE payment_reference = :ref"),
                {"ref": payment_reference}
            )
            if dup.fetchone():
                logger.warning(f"⚠️ [SUBSCRIPTION] Duplicate payment_reference={payment_reference} for user {user_id}")
                raise ValueError(f"Payment reference '{payment_reference}' already used (idempotency guard)")

        now = datetime.now(timezone.utc)

        # Find most recent subscription (active or expired)
        result = await self.db.execute(
            text("""
                SELECT id, tier, status, end_date, billing_provider
                FROM subscriptions
                WHERE user_id = :uid
                ORDER BY created_at DESC
                LIMIT 1
                FOR UPDATE
            """),
            {"uid": user_id}
        )
        existing = result.fetchone()

        if not existing or existing.tier == "free":
            raise ValueError("No paid subscription to renew. Use upgrade instead.")

        tier = existing.tier
        bp = existing.billing_provider

        # Determine new end_date
        if existing.status == "active" and existing.end_date:
            end_dt = _make_aware(existing.end_date)
            if end_dt > now:
                new_end = end_dt + timedelta(days=duration_days)
            else:
                new_end = now + timedelta(days=duration_days)
        else:
            new_end = now + timedelta(days=duration_days)

        # Mark old as superseded, create new row
        await self.db.execute(
            text("UPDATE subscriptions SET status = 'renewed', updated_at = NOW() WHERE id = :sid"),
            {"sid": existing.id}
        )
        await self.db.execute(
            text("""
                INSERT INTO subscriptions
                    (user_id, tier, status, start_date, end_date,
                     payment_reference, billing_provider, auto_renew)
                VALUES (:uid, :tier, 'active', :start, :end, :pref, :bp, TRUE)
            """),
            {
                "uid": user_id,
                "tier": tier,
                "start": now,
                "end": new_end,
                "pref": payment_reference,
                "bp": bp,
            }
        )
        await self.db.commit()

        # ── Instant cache invalidation ──
        await invalidate_cached_tier(user_id)

        logger.info(
            f"🔄 [SUBSCRIPTION] User {user_id} renewed '{tier}' until {new_end.isoformat()}"
        )

        return {
            "success": True,
            "tier": tier,
            "status": "active",
            "features": get_features_for_tier(tier),
            "start_date": now.isoformat(),
            "end_date": new_end.isoformat(),
            "expires_in_days": _expires_in_days(new_end),
            "message": f"Successfully renewed {tier} tier for {duration_days} days",
        }

    # ============ CRON HELPERS ============

    async def expire_lapsed_subscriptions(self) -> int:
        """
        Bulk-expire subscriptions past their end_date.
        Returns count of newly expired subscriptions.
        """
        result = await self.db.execute(
            text("""
                UPDATE subscriptions
                SET status = 'expired', updated_at = NOW()
                WHERE status = 'active'
                  AND end_date IS NOT NULL
                  AND end_date < NOW()
                RETURNING id, user_id
            """)
        )
        expired = result.fetchall()
        await self.db.commit()

        if expired:
            user_ids = [r.user_id for r in expired]
            logger.info(f"⏰ [SUB_CRON] Expired {len(expired)} subscriptions: users={user_ids}")

        return len(expired)

    async def get_auto_renewable(self, within_days: int = 3) -> list[dict]:
        """
        Find subscriptions expiring within N days that have auto_renew=true.
        """
        result = await self.db.execute(
            text("""
                SELECT id, user_id, tier, end_date, billing_provider
                FROM subscriptions
                WHERE status = 'active'
                  AND auto_renew = TRUE
                  AND end_date IS NOT NULL
                  AND end_date < NOW() + INTERVAL ':days days'
                  AND end_date > NOW()
            """.replace(":days", str(int(within_days))))
        )
        rows = result.fetchall()
        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "tier": r.tier,
                "end_date": r.end_date,
                "billing_provider": r.billing_provider,
            }
            for r in rows
        ]
