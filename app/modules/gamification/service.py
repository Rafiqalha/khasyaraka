"""
Leaderboard Service

Business logic for leaderboard operations using Redis Sorted Sets.
PostgreSQL is the SINGLE SOURCE OF TRUTH for users.total_xp.
Redis is used ONLY for fast leaderboard queries and ranking.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.redis import get_redis
from app.modules.users.models import User
from app.modules.gamification.schemas import LeaderboardResponse, LeaderboardUser, MyRank
from app.core.logging import get_logger

logger = get_logger(__name__)

# Redis key for leaderboard
LEADERBOARD_KEY = "leaderboard:training"


class LeaderboardService:
    """
    Leaderboard Service
    
    Handles leaderboard operations using Redis Sorted Sets (ZSET) for high performance.
    
    **ARCHITECTURE:**
    - PostgreSQL (users.total_xp) = SINGLE SOURCE OF TRUTH
    - Redis ZSET = Cache for fast leaderboard queries
    - If Redis fails/empty → Fallback to PostgreSQL query
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize service with database session"""
        self.db = db
    
    async def _get_redis_client(self):
        """Helper to get Redis client"""
        try:
            return await get_redis()
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}")
            return None
    
    async def update_user_score(self, user_id: str, total_xp: int) -> None:
        """
        Update user's score in Redis leaderboard.
        
        **NOTE:** This method ONLY updates Redis cache.
        PostgreSQL (users.total_xp) should already be updated by the caller.
        
        Args:
            user_id: User ID (as string)
            total_xp: Total XP from PostgreSQL (source of truth)
        
        Raises:
            None - Redis failures are logged but don't raise exceptions
        """
        try:
            redis_client = await get_redis()
            
            # ✅ Ensure user_id is string and total_xp is int
            user_id_str = str(user_id)
            total_xp_int = int(total_xp)
            
            logger.info(f"🔄 [REDIS_UPDATE] ZADD {LEADERBOARD_KEY}: member={user_id_str}, score={total_xp_int}")
            
            # ✅ Update Redis Sorted Set (ZSET) ONLY
            # ZADD leaderboard:training <score> <member>
            result = await redis_client.zadd(LEADERBOARD_KEY, {user_id_str: total_xp_int})
            
            logger.info(f"✅ [REDIS_UPDATE] ZADD result: {result} (1=new, 0=updated)")
            
            # ✅ VERIFY: Immediately check if update succeeded
            verify_score = await redis_client.zscore(LEADERBOARD_KEY, user_id_str)
            verify_rank = await redis_client.zrevrank(LEADERBOARD_KEY, user_id_str)
            
            if verify_score is not None:
                logger.info(f"✅ [REDIS_VERIFY] User {user_id_str}: score={int(verify_score)}, rank={int(verify_rank) + 1 if verify_rank is not None else 'N/A'}")
            else:
                logger.error(f"❌ [REDIS_VERIFY] User {user_id_str}: Redis update FAILED - score is None after ZADD!")
            
        except Exception as e:
            # ✅ Don't raise - Redis failure should not break the request
            # PostgreSQL is still the source of truth
            logger.error(f"❌ [REDIS_UPDATE] Failed to update Redis leaderboard: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
    
    async def publish_leaderboard_update(self, user_id: str, total_xp: int) -> None:
        """
        Publish leaderboard change event to Redis Pub/Sub channel.
        Subscribers (SSE clients) will receive real-time notifications.
        
        **Complexity:** O(N+M) where N = subscribers, M = message size
        **Channel:** leaderboard:updates
        """
        import json
        try:
            redis_client = await get_redis()
            event = json.dumps({
                "type": "score_update",
                "user_id": user_id,
                "total_xp": total_xp,
                "timestamp": __import__('time').time()
            })
            await redis_client.publish("leaderboard:updates", event)
            logger.info(f"📡 [PUBSUB] Published leaderboard update: user={user_id}, xp={total_xp}")
        except Exception as e:
            logger.warning(f"⚠️ [PUBSUB] Failed to publish update: {e}")

    async def _get_users_from_cache_or_db(self, user_ids: List[str]) -> List[dict]:
        """
        Get user profiles from Redis cache or fallback to PostgreSQL.
        
        Optimizes N+1 query problem by caching user details (name, avatar, etc.) in Redis.
        Response is a list of dicts (for flexibility) that mimics User object fields.
        """
        import json
        
        # Keys for Redis MGET
        cache_keys = [f"user:profile:{uid}" for uid in user_ids]
        
        try:
            redis_client = await get_redis()
            cached_profiles_raw = await redis_client.mget(cache_keys)
        except Exception as e:
            logger.warning(f"⚠️ [LEADERBOARD_CACHE] Redis MGET failed: {e}")
            cached_profiles_raw = [None] * len(user_ids)

        found_profiles = []
        missing_ids = []
        
        # Map IDs to their cached data (or None)
        for i, uid in enumerate(user_ids):
            data = cached_profiles_raw[i]
            if data:
                try:
                    found_profiles.append(json.loads(data))
                except:
                    missing_ids.append(uid)
            else:
                missing_ids.append(uid)
        
        # Fetch missing from PostgreSQL
        if missing_ids:
            logger.info(f"🔍 [LEADERBOARD_CACHE] Fetching {len(missing_ids)} missing profiles from PostgreSQL")
            try:
                stmt = select(User).where(User.id.in_([int(uid) for uid in missing_ids]))
                result = await self.db.execute(stmt)
                db_users = result.scalars().all()
                
                # Cache fetched users
                redis_updates = {}
                db_user_map = {}
                
                for user in db_users:
                    profile_data = {
                        "id": str(user.id),
                        "full_name": user.full_name or "Unknown",
                        "picture_url": user.picture_url,
                        "xp": getattr(user, "total_xp", 0) # Just in case
                    }
                    found_profiles.append(profile_data)
                    
                    # Store in Redis (TTL 1 hour)
                    redis_updates[f"user:profile:{user.id}"] = json.dumps(profile_data)
                
                if redis_updates:
                    try:
                        # Pipeline for better performance
                        pipe = redis_client.pipeline()
                        for key, val in redis_updates.items():
                            pipe.setex(key, 3600, val) # 1 hour TTL
                        await pipe.execute()
                        logger.info(f"✅ [LEADERBOARD_CACHE] Cached {len(redis_updates)} profiles")
                    except Exception as e:
                        logger.warning(f"⚠️ [LEADERBOARD_CACHE] Failed to cache profiles: {e}")
                        
            except Exception as e:
                 logger.error(f"❌ [LEADERBOARD_CACHE] PostgreSQL fetch failed: {e}")
        
        return found_profiles

    async def get_leaderboard(
        self,
        limit: int = 50,
        current_user_id: Optional[str] = None
    ) -> LeaderboardResponse:
        """
        Get leaderboard with top users and current user's rank.
        
        **FALLBACK MECHANISM:**
        - Try Redis first (fast)
        - If Redis empty/error → Query PostgreSQL and populate Redis
        
        Args:
            limit: Number of top users to return (default 50)
            current_user_id: Current user ID to get their rank
        
        Returns:
            LeaderboardResponse with top_users and my_rank
        """
        logger.info(f"🔍 [LEADERBOARD_SERVICE] get_leaderboard called: limit={limit}, current_user_id={current_user_id}")
        
        try:
            redis_client = await get_redis()
            
            # ✅ CRITICAL: Check Redis cardinality BEFORE using it
            zcard = await redis_client.zcard(LEADERBOARD_KEY)
            
            # ✅ CRITICAL DEBUG: Log if Redis is empty
            if zcard == 0:
                logger.warning(f"⚠️ [LEADERBOARD_SERVICE] Redis key '{LEADERBOARD_KEY}' is EMPTY (zcard=0)")
                logger.info("📊 [LEADERBOARD_SERVICE] Falling back to PostgreSQL...")
                return await self._get_leaderboard_from_postgres(limit, current_user_id)
            
            # Try to get top users from Redis (sorted by score descending)
            top_entries = await redis_client.zrevrange(
                LEADERBOARD_KEY,
                0,
                limit - 1,
                withscores=True
            )
            
            # ✅ FALLBACK: If Redis is empty, query from PostgreSQL
            if not top_entries:
                return await self._get_leaderboard_from_postgres(limit, current_user_id)
            
            # Extract user IDs and scores from Redis
            user_ids = [entry[0] for entry in top_entries]
            scores = {entry[0]: int(entry[1]) for entry in top_entries}
            
            # ✅ OPTIMIZED: Get User Details from Cache or DB
            users_data = await self._get_users_from_cache_or_db(user_ids)
            
            # Create user map for quick lookup
            user_map = {str(user['id']): user for user in users_data}
            
            # Track stale user IDs to remove from Redis
            stale_user_ids = []
            
            # Build leaderboard users list
            top_users = []
            for user_id_str in user_ids:
                user = user_map.get(user_id_str)
                if user:
                    top_users.append(
                        LeaderboardUser(
                            rank=0,  # Will be set after filtering
                            id=str(user['id']),
                            name=user.get('full_name') or "Unknown",
                            xp=scores[user_id_str],  # ✅ Use XP from Redis (fast)
                            avatar=user.get('picture_url')
                        )
                    )
                else:
                    # User not found in PostgreSQL/Cache - mark as stale
                    stale_user_ids.append(user_id_str)
            
            # ✅ Rebuild ranks after filtering stale entries
            top_users.sort(key=lambda u: u.xp, reverse=True)
            for rank, user in enumerate(top_users, start=1):
                user.rank = rank
            
            # ✅ Remove stale entries from Redis (non-blocking)
            if stale_user_ids:
                try:
                    await redis_client.zrem(LEADERBOARD_KEY, *stale_user_ids)
                    logger.info(f"✅ [LEADERBOARD_SERVICE] Removed {len(stale_user_ids)} stale entries")
                except Exception as e:
                    logger.warning(f"⚠️ [LEADERBOARD_SERVICE] Failed to remove stale entries: {e}")
            
            # Get current user's rank
            my_rank = None
            if current_user_id:
                my_rank = await self._get_my_rank(current_user_id)
                # Ensure my_rank is never None for the contract if ID provided, return Unranked object
                if my_rank is None:
                     my_rank = MyRank(rank=0, xp=0)
            
            return LeaderboardResponse(
                top_users=top_users,
                my_rank=my_rank
            )
            
        except Exception as e:
            # ✅ FALLBACK: If Redis fails, query from PostgreSQL
            logger.error(f"❌ [LEADERBOARD_SERVICE] Redis error: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return await self._get_leaderboard_from_postgres(limit, current_user_id)
            
    async def _get_leaderboard_from_postgres(
        self,
        limit: int,
        current_user_id: Optional[str]
    ) -> LeaderboardResponse:
        """
        Fallback: Get leaderboard from PostgreSQL (source of truth).
        Also populates Redis for next time.
        """
        logger.info(f"🔍 [LEADERBOARD_SERVICE] _get_leaderboard_from_postgres called: limit={limit}, current_user_id={current_user_id}")
        
        try:
            # Query top users from PostgreSQL
            stmt = (
                select(User)
                .where(User.total_xp > 0)  # Only users with XP
                .order_by(User.total_xp.desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            # Build leaderboard
            top_users = []
            redis_updates = {}
            
            for rank, user in enumerate(users, start=1):
                top_users.append(
                    LeaderboardUser(
                        rank=rank,
                        id=str(user.id),
                        name=user.full_name or "Unknown",
                        xp=user.total_xp or 0,
                        avatar=user.picture_url
                    )
                )
                redis_updates[str(user.id)] = user.total_xp or 0
            
            # Populate Redis - Background
            if redis_updates:
                try:
                    redis_client = await get_redis()
                    await redis_client.zadd(LEADERBOARD_KEY, redis_updates)
                except Exception as e:
                    logger.warning(f"⚠️ [LEADERBOARD_SERVICE] Redis sync failed: {e}")
            
            # Get my rank
            my_rank = None
            if current_user_id:
                my_rank = await self._get_my_rank_from_postgres(current_user_id)
                if my_rank is None:
                    my_rank = MyRank(rank=0, xp=0)

            return LeaderboardResponse(
                top_users=top_users,
                my_rank=my_rank
            )
            
        except Exception as e:
            logger.error(f"❌ Error DB: {e}")
            return LeaderboardResponse(top_users=[], my_rank=None)

    async def _get_my_rank(self, user_id: str) -> Optional[MyRank]:
        """
        Returns rank >= 1 or rank=0 if unranked.
        NEVER returns None for authenticated users.
        """
        try:
            redis_client = await get_redis()
            user_id_str = str(user_id)
            
            # Get user's score
            score = await redis_client.zscore(LEADERBOARD_KEY, user_id_str)
            
            if score is None:
                return await self._get_my_rank_from_postgres(user_id_str)
            
            # Get rank
            rank = await redis_client.zrevrank(LEADERBOARD_KEY, user_id_str)
            
            if rank is None:
                return await self._get_my_rank_from_postgres(user_id_str)
            
            return MyRank(rank=int(rank) + 1, xp=int(score))
            
        except Exception as e:
            logger.warning(f"⚠️ Rank Redis Error: {e}")
            return await self._get_my_rank_from_postgres(user_id)
    
    async def _get_my_rank_from_postgres(self, user_id: str) -> Optional[MyRank]:
        """
        Get rank from Postgres.
        If user has 0 XP, return Rank 0 (Unranked).
        If user not found, return None.
        """
        try:
            user_id_int = int(user_id)
            stmt = select(User).where(User.id == user_id_int)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None # User doesn't exist at all
            
            user_total_xp = user.total_xp or 0
            
            # ✅ FIX: Handle 0 XP as Unranked (Rank 0) instead of None
            if user_total_xp == 0:
                logger.info(f"📊 [RANK_POSTGRES] User {user_id} has 0 XP -> Rank 0 (Unranked)")
                return MyRank(rank=0, xp=0)
            
            # Calculate rank
            stmt = select(func.count(User.id)).where(User.total_xp > user_total_xp)
            result = await self.db.execute(stmt)
            rank_count = result.scalar() or 0
            
            calculated_rank = rank_count + 1
            
            # Sync to Redis
            try:
                redis_client = await get_redis()
                await redis_client.zadd(LEADERBOARD_KEY, {str(user_id): user_total_xp})
            except:
                pass
            
            return MyRank(rank=calculated_rank, xp=user_total_xp)
            
        except Exception as e:
            logger.error(f"❌ DB Rank Error: {e}")
            # Fallback for errors: Return unranked 0
            return MyRank(rank=0, xp=0)
    
    async def get_leaderboard_compact(
        self,
        limit: int = 10,
        current_user_id: Optional[str] = None
    ) -> dict:
        """
        Lightweight leaderboard query optimized for real-time polling.
        Returns minimal data to reduce bandwidth and latency.
        
        **Big O Complexity (Redis path):**
        - ZREVRANGE: O(log N + M) where N = total users, M = limit
        - ZSCORE:    O(1) per user
        - ZREVRANK:  O(log N) per user
        - ZCARD:     O(1)
        - MGET:      O(K) where K = number of profile cache keys
        - Total:     O(log N + M + K) — sublinear in total users
        
        **Big O Complexity (PostgreSQL fallback):**
        - SELECT ... ORDER BY total_xp DESC LIMIT M: O(N log N) worst case
        - With index on total_xp: O(M log N)
        
        Args:
            limit: Number of top users (default 10, keep small for real-time)
            current_user_id: Current user ID for rank info
        
        Returns:
            Compact dict with top_users list and my_rank
        """
        import json as json_lib
        
        try:
            redis_client = await get_redis()
            zcard = await redis_client.zcard(LEADERBOARD_KEY)  # O(1)
            
            if zcard == 0:
                # Fallback to PostgreSQL — O(N log N) or O(M log N) with index
                full = await self._get_leaderboard_from_postgres(limit, current_user_id)
                return {
                    "top": [{"id": u.id, "name": u.name, "xp": u.xp, "rank": u.rank, "avatar": u.avatar} for u in full.top_users[:limit]],
                    "me": {"rank": full.my_rank.rank, "xp": full.my_rank.xp} if full.my_rank else None,
                    "total": 0,
                }
            
            # O(log N + M) — Redis Sorted Set range query
            top_entries = await redis_client.zrevrange(
                LEADERBOARD_KEY, 0, limit - 1, withscores=True
            )
            
            user_ids = [e[0] for e in top_entries]
            scores = {e[0]: int(e[1]) for e in top_entries}
            
            # O(K) — batch profile fetch from Redis cache / PostgreSQL
            users_data = await self._get_users_from_cache_or_db(user_ids)
            user_map = {str(u['id']): u for u in users_data}
            
            top = []
            for rank_idx, uid in enumerate(user_ids, start=1):
                u = user_map.get(uid)
                if u:
                    top.append({
                        "id": uid,
                        "name": u.get('full_name', 'Unknown'),
                        "xp": scores[uid],
                        "rank": rank_idx,
                        "avatar": u.get('picture_url'),
                    })
            
            # O(log N) + O(1) — current user rank + score
            me = None
            if current_user_id:
                my_score = await redis_client.zscore(LEADERBOARD_KEY, str(current_user_id))  # O(1)
                my_rank = await redis_client.zrevrank(LEADERBOARD_KEY, str(current_user_id))  # O(log N)
                if my_score is not None and my_rank is not None:
                    me = {"rank": int(my_rank) + 1, "xp": int(my_score)}
                else:
                    pg_rank = await self._get_my_rank_from_postgres(current_user_id)
                    if pg_rank:
                        me = {"rank": pg_rank.rank, "xp": pg_rank.xp}
            
            return {"top": top, "me": me, "total": zcard}
        
        except Exception as e:
            logger.error(f"❌ [COMPACT] Error: {e}")
            return {"top": [], "me": None, "total": 0}

    async def rebuild_leaderboard(self) -> int:
        """
        Rebuild Redis leaderboard from PostgreSQL.
        """
        try:
            logger.info("🔄 Starting leaderboard rebuild from PostgreSQL...")
            
            # Get all users with XP from PostgreSQL
            stmt = (
                select(User)
                .where(User.total_xp > 0)
                .order_by(User.total_xp.desc())
            )
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            if not users:
                logger.info("📊 No users with XP found")
                return 0
            
            # Clear existing Redis leaderboard
            try:
                redis_client = await get_redis()
                await redis_client.delete(LEADERBOARD_KEY)
            except Exception as e:
                logger.warning(f"⚠️ Failed to clear Redis: {e}")
            
            # Populate Redis with all users
            redis_updates = {}
            for user in users:
                redis_updates[str(user.id)] = user.total_xp or 0
            
            if redis_updates:
                try:
                    redis_client = await get_redis()
                    await redis_client.zadd(LEADERBOARD_KEY, redis_updates)
                    logger.info(f"✅ Rebuilt leaderboard: {len(redis_updates)} users")
                    return len(redis_updates)
                except Exception as e:
                    logger.error(f"❌ Failed to populate Redis: {e}")
                    return 0
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Error rebuilding leaderboard: {e}")
            return 0