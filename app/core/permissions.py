"""
Feature Permission System (Hardened)

Config-driven feature→tier mapping with strict expiration enforcement.
Tier is determined dynamically from active, non-expired subscriptions only.
Expired subscriptions are invisible to the permission system — zero latency downgrade.

To add features: edit TIER_FEATURES. To gate an endpoint: add Depends(require_tier("mid")).
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone

from app.core.security import get_current_user
from app.db.session import get_db
from app.core.logging import get_logger

logger = get_logger(__name__)


# ==================== FEATURE REGISTRY ====================
# Each tier inherits ALL features from lower tiers.
# Only list NEW features unlocked at each tier level.

TIER_FEATURES = {
    "free": [
        "training_puk",
        "training_ppgd",
        "training_tali",
        "leaderboard",
        "profile",
    ],
    "mid": [
        "training_sandi",
        "training_nav",
        "sku",
        "cyber",
    ],
    "pro": [
        "tkk",
        "hiking",
        "survival",
    ],
}

# Tier hierarchy: higher number = more access
TIER_HIERARCHY = {"free": 0, "mid": 1, "pro": 2}

# Precompute cumulative features per tier (includes lower tiers)
_CUMULATIVE_FEATURES: dict[str, list[str]] = {}
for _tier in ["free", "mid", "pro"]:
    _features = []
    for _t, _level in sorted(TIER_HIERARCHY.items(), key=lambda x: x[1]):
        if TIER_HIERARCHY[_t] <= TIER_HIERARCHY[_tier]:
            _features.extend(TIER_FEATURES.get(_t, []))
    _CUMULATIVE_FEATURES[_tier] = _features


def get_features_for_tier(tier: str) -> list[str]:
    """Get all features available for a given tier (cumulative)."""
    return _CUMULATIVE_FEATURES.get(tier, _CUMULATIVE_FEATURES["free"])


def has_tier_access(user_tier: str, required_tier: str) -> bool:
    """Check if user_tier meets or exceeds required_tier."""
    user_level = TIER_HIERARCHY.get(user_tier, 0)
    required_level = TIER_HIERARCHY.get(required_tier, 0)
    return user_level >= required_level


# ==================== FASTAPI DEPENDENCY (HARDENED) ====================

def require_tier(min_tier: str):
    """
    FastAPI dependency — strict tier check.

    Single query: only matches active, non-expired subscriptions.
    Expired subs are invisible → instant downgrade to free.
    No separate expiration logic needed.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(
            current_user: dict = Depends(get_current_user),
            _tier = Depends(require_tier("pro")),
        ):
            ...
    """
    async def _check_tier(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        user_id = int(current_user.get("sub"))

        # ── LAYER 1: Redis cache (0ms, 60s TTL) ──
        from app.core.tier_cache import get_cached_tier, set_cached_tier
        cached = await get_cached_tier(user_id)
        if cached:
            user_tier = cached["tier"]
            sub_id = cached.get("sub_id")
        else:
            # ── LAYER 2: DB fallback (active + non-expired only) ──
            result = await db.execute(
                text("""
                    SELECT id, tier
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
            user_tier = row.tier if row else "free"
            sub_id = row.id if row else None

            # ── Write to cache for next request ──
            await set_cached_tier(user_id, user_tier, sub_id)

        if not has_tier_access(user_tier, min_tier):
            logger.warning(
                f"🔒 [PERMISSION] User {user_id} denied: has '{user_tier}', needs '{min_tier}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "INSUFFICIENT_TIER",
                    "message": f"This feature requires '{min_tier}' tier or higher",
                    "current_tier": user_tier,
                    "required_tier": min_tier,
                }
            )

        logger.debug(f"✅ [PERMISSION] User {user_id}: tier '{user_tier}' >= '{min_tier}'")
        return {"user_id": user_id, "tier": user_tier, "subscription_id": sub_id}

    return _check_tier
