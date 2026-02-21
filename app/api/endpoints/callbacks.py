from fastapi import APIRouter, Request, HTTPException
from app.services.user_service import increment_hearts
from app.core.logging import get_logger
from app.core.config import settings

router = APIRouter(prefix="/callbacks", tags=["Callbacks"])
logger = get_logger(__name__)

ROUTES_VERIFIER_KEYS_URL = "https://www.gstatic.com/admob/reward/verifier-keys.json"

@router.get("/admob")
async def admob_ssv(request: Request):
    """
    AdMob Server-Side Verification (SSV) callback.
    Verifies signature and rewards user with hearts.
    
    URL format: /api/v1/callbacks/admob?ad_network=...&ad_unit=...&custom_data={user_id}&signature=...
    """
    # 1. Verify Signature (Strict in Production)
    try:
        # Check if library is installed
        # pip install google-ads-admob-ssv
        from google.ads.admob.ssv import Verifier
        
        # Note: Verifier expects the full URL with query params
        # Use str(request.url) but ensure it matches what Google sees (https vs http)
        # If behind proxy, X-Forwarded-Proto headers are handled by Uvicorn usually
        verifier = Verifier(str(request.url))
        
        # Verify (fetches keys from Google and validates signature)
        verifier.verify()
        logger.info("✅ AdMob SSV verification passed")
        
    except ImportError:
        msg = "⚠️ google-ads-admob-ssv library not found."
        if settings.ENVIRONMENT == "production":
            logger.error(f"❌ {msg} CANNOT verify rewards!")
            raise HTTPException(500, "Server configuration error")
        logger.warning(f"{msg} Skipping verification (DEV MODE Only)")
        
    except Exception as e:
        logger.warning(f"❌ AdMob SSV verification failed: {e}")
        if settings.ENVIRONMENT == "production":
            raise HTTPException(403, "Invalid AdMob signature")
        # In DEV, we might allow it for testing without real ads, 
        # but better to simulate properly.

    # 2. Extract User ID, Transaction ID, and Reward Type
    user_id = request.query_params.get("custom_data")
    transaction_id = request.query_params.get("ad_network_transaction_id") or request.query_params.get("signature")
    reward_item = request.query_params.get("reward_item", "")
    reward_value = request.query_params.get("reward_value", "")
    
    if not user_id:
        logger.warning("⚠️ AdMob callback received without custom_data")
        raise HTTPException(400, "Missing custom_data (User ID)")

    if not transaction_id:
         logger.warning("⚠️ AdMob callback received without transaction ID or signature")
         raise HTTPException(400, "Missing transaction ID")

    # 3. Strict Reward Type Check — ONLY accept "hearts" in PRODUCTION
    # Google test ad units use "coins" — reward_item is only configurable on real ad units
    if reward_item != "hearts":
        if settings.ENVIRONMENT == "production":
            logger.warning(f"🚫 Rejected unexpected reward type: '{reward_item}' (value: {reward_value}) for user {user_id}")
            raise HTTPException(400, f"Unexpected reward type: {reward_item}. Expected: hearts")
        logger.warning(f"⚠️ DEV MODE: Accepting reward type '{reward_item}' (prod requires 'hearts')")

    # 4. Anti-Replay Check (Idempotency)
    from app.core.redis import get_redis
    redis = await get_redis()
    tx_key = f"admob:tx:{transaction_id}"
    
    # Check if already processed (TTL 24h)
    if await redis.exists(tx_key):
        logger.info(f"♻️ Transaction {transaction_id} already processed. Skipping.")
        return {"status": "ok", "message": "Already processed"}

    # Mark as processed (before or after? after is safer for failures, but before prevents race)
    # SETNX is best here.
    if not await redis.set(tx_key, "1", ex=86400, nx=True):
         logger.info(f"♻️ Transaction {transaction_id} just processed by another worker.")
         return {"status": "ok", "message": "Already processed"}

    # 5. Reward User (Atomic + Write-Behind)
    # Hearts cap at 5 via atomic_add_heart — no separate ad view limit needed.
    # Users can watch ads freely as long as hearts < 5.
    try:
        logger.info(f"🎁 Rewarding user {user_id} for tx {transaction_id}")
        result = await increment_hearts(
            request=request, 
            user_id=user_id, 
            amount=1
        )
        return {"status": "ok", "hearts": result["hearts"]}
        
    except Exception as e:
        logger.error(f"❌ Failed to process reward for user {user_id}: {e}", exc_info=True)
        raise HTTPException(500, "Internal Server Error")
