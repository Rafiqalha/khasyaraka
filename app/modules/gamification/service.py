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
            logger.info(f"🔍 [LEADERBOARD_SERVICE] Redis key '{LEADERBOARD_KEY}' has {zcard} entries")
            
            # ✅ CRITICAL DEBUG: Log if Redis is empty
            if zcard == 0:
                logger.warning(f"⚠️ [LEADERBOARD_SERVICE] Redis key '{LEADERBOARD_KEY}' is EMPTY (zcard=0)")
                logger.info("📊 [LEADERBOARD_SERVICE] Falling back to PostgreSQL...")
                return await self._get_leaderboard_from_postgres(limit, current_user_id)
            
            # Try to get top users from Redis (sorted by score descending)
            # ZREVRANGE leaderboard:training 0 <limit-1> WITHSCORES
            top_entries = await redis_client.zrevrange(
                LEADERBOARD_KEY,
                0,
                limit - 1,
                withscores=True
            )
            
            logger.info(f"🔍 [LEADERBOARD_SERVICE] Redis ZREVRANGE returned {len(top_entries)} entries")
            
            # ✅ FALLBACK: If Redis is empty, query from PostgreSQL
            if not top_entries:
                logger.warning("📊 [LEADERBOARD_SERVICE] Redis leaderboard empty (top_entries=[]), falling back to PostgreSQL")
                return await self._get_leaderboard_from_postgres(limit, current_user_id)
            
            # Extract user IDs and scores from Redis
            user_ids = [entry[0] for entry in top_entries]
            scores = {entry[0]: int(entry[1]) for entry in top_entries}
            
            logger.info(f"🔍 [LEADERBOARD_SERVICE] Extracted user_ids: {user_ids[:5]}... (showing first 5)")
            
            # Enrich with user data from PostgreSQL
            stmt = select(User).where(User.id.in_([int(uid) for uid in user_ids]))
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            logger.info(f"🔍 [LEADERBOARD_SERVICE] PostgreSQL query returned {len(users)} users")
            
            # ✅ CRITICAL: Detect stale data in Redis after Supabase migration
            # If most users from Redis are not found in PostgreSQL, Redis is stale
            stale_threshold = 0.5  # If >50% users not found, consider Redis stale
            found_count = len(users)
            total_count = len(user_ids)
            stale_ratio = 1 - (found_count / total_count) if total_count > 0 else 0
            
            if stale_ratio > stale_threshold and total_count > 0:
                logger.warning(f"⚠️ [LEADERBOARD_SERVICE] STALE DATA DETECTED: {found_count}/{total_count} users found in PostgreSQL (stale_ratio={stale_ratio:.2%})")
                logger.info("🔄 [LEADERBOARD_SERVICE] Auto-rebuilding Redis from PostgreSQL (source of truth)...")
                # Clear stale Redis entries and rebuild from PostgreSQL
                try:
                    await redis_client.delete(LEADERBOARD_KEY)
                    logger.info("✅ [LEADERBOARD_SERVICE] Cleared stale Redis leaderboard")
                except Exception as e:
                    logger.warning(f"⚠️ [LEADERBOARD_SERVICE] Failed to clear Redis: {e}")
                # Fallback to PostgreSQL query which will rebuild Redis
                return await self._get_leaderboard_from_postgres(limit, current_user_id)
            
            # Create user map for quick lookup
            user_map = {str(user.id): user for user in users}
            
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
                            id=user_id_str,
                            name=user.full_name or "Unknown",
                            xp=scores[user_id_str],  # ✅ Use XP from Redis (fast)
                            avatar=user.picture_url
                        )
                    )
                else:
                    # User not found in PostgreSQL - mark as stale
                    stale_user_ids.append(user_id_str)
                    logger.warning(f"⚠️ [LEADERBOARD_SERVICE] User not found in PostgreSQL: user_id={user_id_str} (will be removed from Redis)")
                    # Don't include stale users in leaderboard
            
            # ✅ Rebuild ranks after filtering stale entries
            # Sort by XP descending and assign ranks
            top_users.sort(key=lambda u: u.xp, reverse=True)
            for rank, user in enumerate(top_users, start=1):
                user.rank = rank
            
            # ✅ Remove stale entries from Redis (non-blocking)
            if stale_user_ids:
                try:
                    await redis_client.zrem(LEADERBOARD_KEY, *stale_user_ids)
                    logger.info(f"✅ [LEADERBOARD_SERVICE] Removed {len(stale_user_ids)} stale entries from Redis: {stale_user_ids}")
                except Exception as e:
                    logger.warning(f"⚠️ [LEADERBOARD_SERVICE] Failed to remove stale entries from Redis: {e}")
            
            logger.info(f"🔍 [LEADERBOARD_SERVICE] Built {len(top_users)} top_users from Redis")
            
            # Get current user's rank
            my_rank = None
            if current_user_id:
                logger.info(f"🔍 [LEADERBOARD_SERVICE] Getting my_rank for user_id={current_user_id}")
                my_rank = await self._get_my_rank(current_user_id)
                if my_rank:
                    logger.info(f"✅ [LEADERBOARD_SERVICE] my_rank found: rank={my_rank.rank}, xp={my_rank.xp}")
                else:
                    logger.warning(f"⚠️ [LEADERBOARD_SERVICE] my_rank is None for user_id={current_user_id}")
            else:
                logger.info("🔍 [LEADERBOARD_SERVICE] No current_user_id provided, skipping my_rank")
            
            logger.info(f"📊 [LEADERBOARD_SERVICE] Leaderboard fetched from Redis: {len(top_users)} users, my_rank={'present' if my_rank else 'null'}")
            
            return LeaderboardResponse(
                top_users=top_users,
                my_rank=my_rank
            )
            
        except Exception as e:
            # ✅ FALLBACK: If Redis fails, query from PostgreSQL
            logger.error(f"❌ [LEADERBOARD_SERVICE] Error fetching leaderboard from Redis: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            logger.info("📊 [LEADERBOARD_SERVICE] Falling back to PostgreSQL query")
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
            # ✅ CRITICAL DEBUG: Check total users and users with XP
            total_users_stmt = select(func.count(User.id))
            total_users_result = await self.db.execute(total_users_stmt)
            total_users = total_users_result.scalar() or 0
            
            users_with_xp_stmt = select(func.count(User.id)).where(User.total_xp > 0)
            users_with_xp_result = await self.db.execute(users_with_xp_stmt)
            users_with_xp = users_with_xp_result.scalar() or 0
            
            logger.info(f"🔍 [LEADERBOARD_SERVICE] PostgreSQL stats: total_users={total_users}, users_with_xp={users_with_xp}")
            
            # Query top users from PostgreSQL
            stmt = (
                select(User)
                .where(User.total_xp > 0)  # Only users with XP
                .order_by(User.total_xp.desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            logger.info(f"🔍 [LEADERBOARD_SERVICE] PostgreSQL query returned {len(users)} users")
            
            if not users:
                logger.warning("📊 [LEADERBOARD_SERVICE] No users with XP found in PostgreSQL")
                logger.info(f"   PostgreSQL stats: total_users={total_users}, users_with_xp={users_with_xp}")
                return LeaderboardResponse(
                    top_users=[],
                    my_rank=await self._get_my_rank_from_postgres(current_user_id) if current_user_id else None
                )
            
            # Build leaderboard from PostgreSQL
            top_users = []
            redis_updates = {}  # Batch Redis updates
            
            for rank, user in enumerate(users, start=1):
                top_users.append(
                    LeaderboardUser(
                        rank=rank,
                        id=str(user.id),
                        name=user.full_name or "Unknown",
                        xp=user.total_xp or 0,  # ✅ Use XP from PostgreSQL (source of truth)
                        avatar=user.picture_url
                    )
                )
                # Prepare Redis update
                redis_updates[str(user.id)] = user.total_xp or 0
            
            logger.info(f"🔍 [LEADERBOARD_SERVICE] Built {len(top_users)} top_users from PostgreSQL")
            
            # ✅ Populate Redis for next time (non-blocking)
            try:
                redis_client = await get_redis()
                if redis_updates:
                    await redis_client.zadd(LEADERBOARD_KEY, redis_updates)
                    logger.info(f"✅ [LEADERBOARD_SERVICE] Populated Redis leaderboard with {len(redis_updates)} users")
            except Exception as e:
                logger.warning(f"⚠️ [LEADERBOARD_SERVICE] Failed to populate Redis (non-critical): {e}")
            
            # Get current user's rank
            my_rank = None
            if current_user_id:
                logger.info(f"🔍 [LEADERBOARD_SERVICE] Getting my_rank from PostgreSQL for user_id={current_user_id}")
                my_rank = await self._get_my_rank_from_postgres(current_user_id)
                if my_rank:
                    logger.info(f"✅ [LEADERBOARD_SERVICE] my_rank found: rank={my_rank.rank}, xp={my_rank.xp}")
                else:
                    logger.warning(f"⚠️ [LEADERBOARD_SERVICE] my_rank is None for user_id={current_user_id}")
            
            logger.info(f"📊 [LEADERBOARD_SERVICE] Leaderboard fetched from PostgreSQL: {len(top_users)} users, my_rank={'present' if my_rank else 'null'}")
            
            return LeaderboardResponse(
                top_users=top_users,
                my_rank=my_rank
            )
            
        except Exception as e:
            logger.error(f"❌ [LEADERBOARD_SERVICE] Error fetching leaderboard from PostgreSQL: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            # Return empty leaderboard if all else fails
            return LeaderboardResponse(
                top_users=[],
                my_rank=None
            )
    
    async def _get_my_rank(self, user_id: str) -> Optional[MyRank]:
        """
        Get current user's rank and XP from Redis.
        
        Falls back to PostgreSQL if Redis fails or user not found.
        
        **CRITICAL:** Returns rank >= 1 if user has XP, None if user has no XP.
        """
        try:
            redis_client = await get_redis()
            
            # ✅ Ensure user_id is string
            user_id_str = str(user_id)
            
            # Get user's score from Redis
            score = await redis_client.zscore(LEADERBOARD_KEY, user_id_str)
            
            if score is None:
                logger.info(f"📊 [RANK] User {user_id_str} not found in Redis, falling back to PostgreSQL")
                # ✅ Fallback to PostgreSQL
                return await self._get_my_rank_from_postgres(user_id_str)
            
            # Get rank (0-indexed, so add 1)
            rank = await redis_client.zrevrank(LEADERBOARD_KEY, user_id_str)
            
            if rank is None:
                logger.warning(f"⚠️ [RANK] User {user_id_str} has score but no rank in Redis, falling back to PostgreSQL")
                # ✅ Fallback to PostgreSQL
                return await self._get_my_rank_from_postgres(user_id_str)
            
            # ✅ Ensure rank is >= 1
            calculated_rank = int(rank) + 1  # Convert to 1-indexed
            
            logger.info(f"📊 [RANK] User {user_id_str}: rank={calculated_rank}, xp={int(score)} (from Redis)")
            
            return MyRank(
                rank=calculated_rank,
                xp=int(score)
            )
            
        except Exception as e:
            logger.warning(f"⚠️ [RANK] Error getting rank from Redis: {e}")
            # ✅ Fallback to PostgreSQL
            return await self._get_my_rank_from_postgres(user_id)
    
    async def _get_my_rank_from_postgres(self, user_id: str) -> Optional[MyRank]:
        """
        Get current user's rank and XP from PostgreSQL (source of truth).
        
        **CRITICAL:** Returns rank >= 1 if user has XP, None if user has no XP.
        """
        logger.info(f"🔍 [RANK_POSTGRES] Getting rank from PostgreSQL for user_id={user_id}")
        
        try:
            # ✅ Ensure user_id is int for PostgreSQL query
            user_id_int = int(user_id)
            
            # Get user's total_xp
            stmt = select(User).where(User.id == user_id_int)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"⚠️ [RANK_POSTGRES] User {user_id} not found in PostgreSQL")
                return None
            
            user_total_xp = user.total_xp or 0
            logger.info(f"🔍 [RANK_POSTGRES] User {user_id} found: total_xp={user_total_xp}")
            
            if user_total_xp == 0:
                logger.info(f"📊 [RANK_POSTGRES] User {user_id} has 0 XP, returning None")
                return None
            
            # ✅ Calculate rank: COUNT users with higher XP + 1
            # This ensures rank is always >= 1
            stmt = select(func.count(User.id)).where(User.total_xp > user_total_xp)
            result = await self.db.execute(stmt)
            rank_count = result.scalar() or 0
            
            calculated_rank = rank_count + 1  # ✅ Always >= 1
            
            logger.info(f"📊 [RANK_POSTGRES] User {user_id}: rank={calculated_rank}, xp={user_total_xp} (from PostgreSQL)")
            
            # ✅ Add to Redis for next time (non-blocking)
            try:
                redis_client = await get_redis()
                await redis_client.zadd(LEADERBOARD_KEY, {str(user_id): user_total_xp})
                logger.info(f"✅ [RANK_POSTGRES] Added user {user_id} to Redis for next time")
            except Exception as e:
                logger.warning(f"⚠️ [RANK_POSTGRES] Failed to add user {user_id} to Redis: {e}")
            
            return MyRank(
                rank=calculated_rank,  # ✅ Always >= 1
                xp=user_total_xp
            )
            
        except Exception as e:
            logger.error(f"❌ [RANK_POSTGRES] Error getting rank from PostgreSQL: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None
    
    async def rebuild_leaderboard(self) -> int:
        """
        Rebuild Redis leaderboard from PostgreSQL (source of truth).
        
        Useful for:
        - Redis restart/recovery
        - Data migration
        - Manual admin trigger
        
        Returns:
            Number of users added to Redis
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