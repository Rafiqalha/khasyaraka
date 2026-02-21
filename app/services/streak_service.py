"""
Streak Service

Atomic, timezone-aware daily streak management.
Uses SELECT ... FOR UPDATE to prevent race conditions.

Rules:
- Streak increments ONLY on lesson completion (not login/app open)
- Max 1 increment per calendar day (user's timezone)
- Resets to 1 if user misses 1+ full days
- Tracks both current_streak and longest_streak
"""

from datetime import datetime, timedelta, timezone as tz
from zoneinfo import ZoneInfo
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEZONE = "Asia/Jakarta"


async def update_streak_atomic(
    db: AsyncSession,
    user_id: int,
    user_timezone: str = None,
) -> dict:
    """
    Atomically update a user's daily streak after lesson completion.
    
    Uses SELECT ... FOR UPDATE to lock the user row, preventing
    concurrent requests from double-incrementing.
    
    Returns:
        dict with: streak, longest_streak, last_active_date, already_counted
    """
    tz_name = user_timezone or DEFAULT_TIMEZONE
    
    try:
        user_tz = ZoneInfo(tz_name)
    except (KeyError, Exception):
        logger.warning(f"⚠️ [STREAK] Invalid timezone '{tz_name}', falling back to {DEFAULT_TIMEZONE}")
        user_tz = ZoneInfo(DEFAULT_TIMEZONE)
    
    # Current date in user's timezone
    now_utc = datetime.now(tz.utc)
    today_user = now_utc.astimezone(user_tz).date()
    
    logger.info(f"🔥 [STREAK] Processing for user {user_id}: today={today_user} (tz={tz_name})")
    
    # Atomic: lock user row to prevent concurrent updates
    row = await db.execute(
        text("""
            SELECT streak, longest_streak, last_active_date, timezone
            FROM users
            WHERE id = :uid
            FOR UPDATE
        """),
        {"uid": user_id}
    )
    user = row.fetchone()
    
    if not user:
        logger.error(f"❌ [STREAK] User {user_id} not found")
        return {"streak": 0, "longest_streak": 0, "last_active_date": None, "already_counted": False}
    
    current_streak = user.streak or 0
    longest_streak = user.longest_streak or 0
    last_active = user.last_active_date
    already_counted = False
    
    # Calculate new streak
    if last_active is None:
        # First ever lesson completion
        new_streak = 1
    elif last_active == today_user:
        # Already completed a lesson today — no change
        new_streak = current_streak
        already_counted = True
    elif (today_user - last_active) == timedelta(days=1):
        # Active yesterday — continue streak
        new_streak = current_streak + 1
    else:
        # Missed 1+ full days — reset to 1
        new_streak = 1
    
    # Update longest_streak if current streak is higher
    new_longest = max(longest_streak, new_streak)
    
    # Write back atomically (still within the FOR UPDATE lock)
    await db.execute(
        text("""
            UPDATE users
            SET streak = :streak,
                longest_streak = :longest,
                last_active_date = :last_active
            WHERE id = :uid
        """),
        {
            "streak": new_streak,
            "longest": new_longest,
            "last_active": today_user,
            "uid": user_id,
        }
    )
    
    if already_counted:
        logger.info(f"🔥 [STREAK] User {user_id}: already counted today, streak stays at {new_streak}")
    else:
        logger.info(f"🔥 [STREAK] User {user_id}: streak {current_streak}→{new_streak}, longest={new_longest}")
    
    return {
        "streak": new_streak,
        "longest_streak": new_longest,
        "last_active_date": today_user.isoformat(),
        "already_counted": already_counted,
    }
