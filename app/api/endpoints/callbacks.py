import base64
import time
from typing import Dict, Optional, Tuple

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi import APIRouter, Request, HTTPException
from app.services.user_service import increment_hearts
from app.core.logging import get_logger
from app.core.config import settings

router = APIRouter(prefix="/callbacks", tags=["Callbacks"])
logger = get_logger(__name__)

ROUTES_VERIFIER_KEYS_URL = "https://www.gstatic.com/admob/reward/verifier-keys.json"


_KEYS_CACHE: Dict[int, ec.EllipticCurvePublicKey] = {}
_KEYS_CACHE_EXPIRES_AT: float = 0.0
_KEYS_CACHE_TTL_SECONDS: int = 60 * 60  # 1 hour (docs recommend <= 24h)


def _urlsafe_b64decode_padded(data: bytes) -> bytes:
    # AdMob signature is url-safe base64 without padding.
    missing = (-len(data)) % 4
    if missing:
        data += b"=" * missing
    return base64.urlsafe_b64decode(data)


def _extract_verification_material(raw_query: bytes) -> Tuple[bytes, bytes, int]:
    """
    Extract:
    - data_to_verify: query string bytes up to (but excluding) '&signature='
    - signature: DER-encoded ECDSA signature bytes (decoded from urlsafe base64)
    - key_id: int

    IMPORTANT: Uses raw query bytes (percent-encoded) to match AdMob's signing input.
    Per Google docs, the last two query params are always signature and key_id (in that order).
    """
    sig_marker = b"signature="
    key_marker = b"&key_id="

    sig_index = raw_query.find(sig_marker)
    if sig_index == -1:
        raise ValueError("Missing signature query parameter")

    # Content to verify ends right before '&signature=' (hence -1 to drop the '&')
    if sig_index == 0 or raw_query[sig_index - 1 : sig_index] != b"&":
        raise ValueError("Invalid query format: signature must be preceded by '&'")
    data_to_verify = raw_query[: sig_index - 1]

    key_index = raw_query.find(key_marker, sig_index)
    if key_index == -1:
        raise ValueError("Missing key_id query parameter")

    sig_b64 = raw_query[sig_index + len(sig_marker) : key_index]
    key_id_bytes = raw_query[key_index + len(key_marker) :]

    # signature and key_id values are not expected to contain percent-escapes,
    # but we defensively decode any escapes by operating on raw bytes only.
    signature = _urlsafe_b64decode_padded(sig_b64)

    try:
        key_id = int(key_id_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid key_id: {e}") from e

    return data_to_verify, signature, key_id


async def _get_verifying_keys() -> Dict[int, ec.EllipticCurvePublicKey]:
    global _KEYS_CACHE, _KEYS_CACHE_EXPIRES_AT

    now = time.time()
    if _KEYS_CACHE and now < _KEYS_CACHE_EXPIRES_AT:
        return _KEYS_CACHE

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(ROUTES_VERIFIER_KEYS_URL)
        resp.raise_for_status()
        payload = resp.json()

    keys = {}
    for item in payload.get("keys", []):
        key_id = item.get("keyId")
        pem = item.get("pem")
        if key_id is None or not pem:
            continue
        public_key = load_pem_public_key(pem.encode("utf-8"))
        # AdMob uses ECDSA public keys.
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            continue
        keys[int(key_id)] = public_key

    if not keys:
        raise RuntimeError("No AdMob verifying keys available")

    _KEYS_CACHE = keys
    _KEYS_CACHE_EXPIRES_AT = now + _KEYS_CACHE_TTL_SECONDS
    return _KEYS_CACHE


async def _verify_admob_ssv(request: Request) -> None:
    """
    Verifies AdMob SSV signature according to Google docs:
    - data_to_verify is the query string bytes before '&signature='
    - signature is DER-encoded ECDSA signature over SHA-256(data_to_verify)
    - key_id selects the public key from verifier-keys.json
    """
    raw_query: bytes = request.scope.get("query_string", b"")
    data_to_verify, signature, key_id = _extract_verification_material(raw_query)
    keys = await _get_verifying_keys()

    public_key = keys.get(key_id)
    if public_key is None:
        raise ValueError(f"Unknown key_id: {key_id}")

    try:
        public_key.verify(signature, data_to_verify, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as e:
        raise ValueError("Invalid AdMob SSV signature") from e


@router.get("/admob")
async def admob_ssv(request: Request):
    """
    AdMob Server-Side Verification (SSV) callback.
    Verifies signature and rewards user with hearts.
    
    URL format: /api/v1/callbacks/admob?ad_network=...&ad_unit=...&custom_data={user_id}&signature=...
    """
    # 1. Verify Signature (Strict in Production)
    try:
        await _verify_admob_ssv(request)
        logger.info("✅ AdMob SSV verification passed")

    except Exception as e:
        logger.warning(f"❌ AdMob SSV verification failed: {e}")
        if settings.ENVIRONMENT == "production":
            raise HTTPException(400, "Invalid AdMob SSV signature")

    # 2. Extract User ID, Transaction ID, and Reward Type
    user_id = request.query_params.get("user_id") or request.query_params.get("custom_data")
    transaction_id = (
        request.query_params.get("transaction_id")
        or request.query_params.get("ad_network_transaction_id")
        or request.query_params.get("signature")
    )
    reward_item = request.query_params.get("reward_item", "")
    reward_amount = request.query_params.get("reward_amount", "")
    
    if not user_id:
        logger.warning("⚠️ AdMob callback received without custom_data")
        raise HTTPException(400, "Missing user_id/custom_data")

    if not transaction_id:
         logger.warning("⚠️ AdMob callback received without transaction ID or signature")
         raise HTTPException(400, "Missing transaction ID")

    # 3. Strict Reward Type Check — ONLY accept "hearts" in PRODUCTION
    # Google test ad units use "coins" — reward_item is only configurable on real ad units
    if reward_item != "hearts":
        if settings.ENVIRONMENT == "production":
            logger.warning(f"🚫 Rejected unexpected reward type: '{reward_item}' (amount: {reward_amount}) for user {user_id}")
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
