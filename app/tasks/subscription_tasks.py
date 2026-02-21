"""
Subscription Background Tasks (Hardened)

Periodic cron that:
1. Bulk-expires lapsed subscriptions (end_date < NOW())
2. Attempts auto-renewal for subscriptions expiring within 3 days
3. Staggers renewals with random jitter (prevents burst spike to provider)
4. Logs all attempts for audit trail

Runs every 6 hours via asyncio.create_task in main.py startup.
"""

import asyncio
import random
from app.db.session import SessionLocal
from app.modules.subscription.service import SubscriptionService
from app.core.billing_provider import get_billing_provider
from app.core.logging import get_logger

logger = get_logger(__name__)

# Config
CRON_INTERVAL_SECONDS = 6 * 60 * 60  # 6 hours
AUTO_RENEW_LOOKAHEAD_DAYS = 3
RENEWAL_JITTER_MAX_SECONDS = 15 * 60  # ±15 minutes stagger per renewal


async def subscription_cron_loop():
    """
    Long-running background loop. Runs immediately on startup,
    then every CRON_INTERVAL_SECONDS.
    """
    logger.info("🔄 [SUB_CRON] Subscription cron task started")

    while True:
        try:
            await _run_subscription_cron()
        except Exception as e:
            logger.error(f"❌ [SUB_CRON] Cron cycle failed: {e}", exc_info=True)

        await asyncio.sleep(CRON_INTERVAL_SECONDS)


async def _run_subscription_cron():
    """Single cron cycle: expire + auto-renew with jitter."""
    async with SessionLocal() as db:
        service = SubscriptionService(db)

        # 1. Bulk-expire lapsed subscriptions
        expired_count = await service.expire_lapsed_subscriptions()

        # 2. Find auto-renewable subscriptions expiring soon
        renewables = await service.get_auto_renewable(within_days=AUTO_RENEW_LOOKAHEAD_DAYS)
        renewed_count = 0
        failed_count = 0

        for sub in renewables:
            # ── Burst stagger: random jitter per renewal ──
            jitter = random.uniform(0, RENEWAL_JITTER_MAX_SECONDS)
            logger.info(
                f"⏳ [SUB_CRON] Scheduling renewal for user {sub['user_id']} "
                f"in {jitter:.0f}s (jitter)"
            )
            await asyncio.sleep(jitter)

            provider = get_billing_provider(sub["billing_provider"])
            try:
                # ── Server-to-server verification via provider ──
                result = await provider.process_renewal(sub["id"], sub["user_id"])
                if result.success:
                    await service.renew_subscription(
                        user_id=sub["user_id"],
                        payment_reference=result.reference,
                        duration_days=30,
                    )
                    renewed_count += 1
                    logger.info(
                        f"✅ [SUB_CRON] Auto-renewed user {sub['user_id']} "
                        f"(tier={sub['tier']}, provider={sub['billing_provider']}, "
                        f"ref={result.reference})"
                    )
                else:
                    failed_count += 1
                    logger.warning(
                        f"⚠️ [SUB_CRON] Auto-renewal failed for user {sub['user_id']}: "
                        f"{result.error}"
                    )
            except ValueError as e:
                # Idempotency guard fired — payment_reference already used
                logger.warning(
                    f"🛡️ [SUB_CRON] Idempotency block for user {sub['user_id']}: {e}"
                )
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"❌ [SUB_CRON] Auto-renewal error for user {sub['user_id']}: {e}",
                    exc_info=True,
                )

        logger.info(
            f"🔄 [SUB_CRON] Cycle complete: "
            f"expired={expired_count}, renewed={renewed_count}, failed={failed_count}"
        )
