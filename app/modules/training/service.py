"""
Training Service

Business logic layer for Training module.
Uses repository for database access.
All database operations go through repository layer.
"""

from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.training.repository import TrainingRepository
from app.modules.training.models import (
    TrainingSection,
    TrainingUnit,
    TrainingLevel,
    TrainingQuestion,
    UserProgress
)
from app.modules.training.schemas import (
    PathSchema,
    LessonSchema,
    QuestionSchema,
    LearningPathResponse,
    PathUnitSchema,
    PathLevelSchema,
)



import json as json_lib
from app.core.redis import get_redis
from app.services.user_service import CacheKeys, CACHE_TTL_LEVELS, CACHE_TTL_STATIC
from app.core.logging import get_logger

logger = get_logger(__name__)

class TrainingService:
    """
    Training Service
    
    Handles business logic for training operations.
    Uses repository pattern for database access.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize service with database session.
        Repository is required for all operations.
        """
        if db is None:
            raise ValueError("Database session is required")
        self.db = db
        self.repository = TrainingRepository(db)

    # ==================== LEGACY METHODS (DEPRECATED - Requires Migration) ====================
    
    async def get_learning_path(self) -> List[PathSchema]:
        """
        DEPRECATED: Legacy method for Supabase-based learning paths.
        
        This method is kept for backward compatibility but requires migration
        to use SQLAlchemy models. The legacy Supabase tables are:
        - khasyaraka_training_paths
        - khasyaraka_training_lessons
        
        TODO: Migrate to use TrainingSection/TrainingUnit/TrainingLevel models
        or create dedicated legacy models if these tables still exist.
        
        For now, returns empty list to prevent errors.
        """
        # TODO: Implement using SQLAlchemy if legacy tables still exist
        # For now, return empty to prevent breaking existing endpoints
        return []

    async def get_questions_by_lesson(self, lesson_id: int) -> List[QuestionSchema]:
        """
        DEPRECATED: Legacy method for Supabase-based questions.
        
        This method is kept for backward compatibility but requires migration
        to use SQLAlchemy models. The legacy Supabase table is:
        - khasyaraka_training_questions
        
        TODO: Migrate to use TrainingQuestion model or create dedicated
        legacy model if this table still exists.
        
        For now, returns empty list to prevent errors.
        """
        # TODO: Implement using SQLAlchemy if legacy table still exists
        # For now, return empty to prevent breaking existing endpoints
        return []

    # ==================== NEW METHODS (Repository-based) ====================
    
    async def get_all_sections(self) -> List[TrainingSection]:
        """Get all active sections with Redis caching"""
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        
        cache_key = CacheKeys.training_sections()
        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
            if cached:
                logger.info(f"📦 [CACHE HIT] training:sections")
                data = json_lib.loads(cached)
                # Reconstruct ORM-like objects from cache
                from app.modules.training.models import TrainingSection as TSModel
                sections = []
                for item in data:
                    s = TSModel(**item)
                    sections.append(s)
                return sections
        except Exception as e:
            logger.warning(f"⚠️ Redis read failed for sections: {e}")
        
        sections = await self.repository.get_all_sections()
        
        # Cache the result
        try:
            redis = await get_redis()
            serialized = json_lib.dumps([
                {"id": s.id, "title": s.title, "description": s.description,
                 "tier": s.tier, "order": s.order, "is_active": s.is_active,
                 "created_at": s.created_at.isoformat() if s.created_at else None}
                for s in sections
            ])
            await redis.setex(cache_key, CACHE_TTL_STATIC, serialized)
            logger.info(f"💾 [CACHE SET] training:sections ({len(sections)} items)")
        except Exception as e:
            logger.warning(f"⚠️ Redis cache set failed for sections: {e}")
        
        return sections

    async def get_section_by_id(self, section_id: str) -> Optional[TrainingSection]:
        """Get a specific section by ID"""
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        return await self.repository.get_section_by_id(section_id)

    async def get_units_by_section(self, section_id: str) -> List[TrainingUnit]:
        """Get all units for a section"""
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        return await self.repository.get_units_by_section(section_id)

    async def get_unit_by_id(self, unit_id: str) -> Optional[TrainingUnit]:
        """Get a specific unit by ID"""
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        return await self.repository.get_unit_by_id(unit_id)

    async def get_levels_by_unit(self, unit_id: str) -> List[TrainingLevel]:
        """Get all levels for a unit"""
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        return await self.repository.get_levels_by_unit(unit_id)

    async def get_level_by_id(self, level_id: str) -> Optional[TrainingLevel]:
        """Get a specific level by ID"""
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        return await self.repository.get_level_by_id(level_id)

    async def get_questions_by_unit(self, unit_id: str) -> List[TrainingQuestion]:
        """
        Get all questions from all levels in a unit.
        
        Args:
            unit_id: Unit ID (e.g., 'puk_u1')
        
        Returns:
            List of all questions from all active levels in this unit
            Ordered by level_number, then by question order
        """
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        return await self.repository.get_questions_by_unit(unit_id)

    async def get_questions_by_level(self, level_id: str) -> List[TrainingQuestion]:
        """Get all questions for a level"""
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        return await self.repository.get_questions_by_level(level_id)

    async def get_question_by_id(self, question_id: str) -> Optional[TrainingQuestion]:
        """Get a specific question by ID"""
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        return await self.repository.get_question_by_id(question_id)

    async def get_learning_path_for_section(self, section_id: str, user_id: Optional[int] = None) -> LearningPathResponse:
        """
        Get structured learning path for a section with Redis caching.
        Returns Duolingo-style learning path with section → units → levels.
        
        Structure is cached in Redis (static content). User progress (status)
        is handled separately by get_progress_state.
        """
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        
        # Try Redis cache for the structure (user-independent)
        cache_key = CacheKeys.learning_path(section_id)
        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
            if cached:
                logger.info(f"📦 [CACHE HIT] training:path:{section_id}")
                data = json_lib.loads(cached)
                return LearningPathResponse(**data)
        except Exception as e:
            logger.warning(f"⚠️ Redis read failed for learning path {section_id}: {e}")
        
        section = await self.repository.get_section_with_units_and_levels(section_id)
        
        if not section:
            return None
        
        # Build response structure
        units_data = []
        
        for unit in sorted(section.units, key=lambda u: u.order):
            if not unit.is_active:
                continue
                
            # Build levels for this unit
            levels_data = []
            for level in sorted(unit.levels, key=lambda l: l.level_number):
                if not level.is_active:
                    continue
                    
                # Determine status based on unlock_rule and user progress
                status = await self._determine_level_status(level, user_id)
                
                levels_data.append(PathLevelSchema(
                    level_id=level.id,
                    title=f"Level {level.level_number}",  # Generated title
                    level_number=level.level_number,
                    difficulty=level.difficulty,
                    xp_reward=level.xp_reward,
                    status=status
                ))
            
            units_data.append(PathUnitSchema(
                unit_id=unit.id,
                unit_title=unit.title,
                order=unit.order,
                levels=levels_data
            ))
        
        response = LearningPathResponse(
            section_id=section.id,
            section_title=section.title,
            units=units_data
        )
        
        # Cache the structure
        try:
            redis = await get_redis()
            await redis.setex(cache_key, CACHE_TTL_STATIC, response.model_dump_json())
            logger.info(f"💾 [CACHE SET] training:path:{section_id}")
        except Exception as e:
            logger.warning(f"⚠️ Redis cache set failed for learning path {section_id}: {e}")
        
        return response
    
    async def _determine_level_status(self, level: TrainingLevel, user_id: Optional[int] = None) -> str:
        """
        Determine level status based on unlock_rule and user progress.
        
        Status values:
        - "LOCKED": Level is locked (previous level not completed)
        - "UNLOCKED": Level is unlocked and available to play
        - "UNLOCKED": Level is in progress (treated as unlocked)
        - "COMPLETED": User has completed this level
        """
        if not user_id:
            # No user context: only unlock level 1 of each unit
            if level.level_number == 1:
                return "UNLOCKED"
            return "LOCKED"
        
        # Get user progress for this level
        progress = await self.repository.get_user_progress(user_id, level.id)
        
        if progress:
            # User has progress: return their status (ensure UPPERCASE)
            return progress.status.upper()
        
        # No progress yet: check unlock rule
        unlock_rule = level.unlock_rule or {}
        rule_type = unlock_rule.get("type")
        
        if rule_type == "start":
            # First level: always available
            return "UNLOCKED"
        elif rule_type == "level_completed":
            # Check if prerequisite level is completed
            prereq_level_id = unlock_rule.get("value")
            if prereq_level_id:
                prereq_progress = await self.repository.get_user_progress(user_id, prereq_level_id)
                if prereq_progress and prereq_progress.status.upper() == "COMPLETED":
                    return "UNLOCKED"
            return "LOCKED"
        else:
            # Unknown rule: default to locked
            return "LOCKED"
    
    async def submit_progress(
        self,
        user_id: int,
        level_id: str,
        score: int,
        total_questions: int,
        correct_answers: int,
        correct_question_ids: List[str],  # ✅ NEW: List of question IDs answered correctly
        time_spent_seconds: int = 0,
    ) -> UserProgress:
        """
        Submit user progress for a level.
        
        **SINGLE SOURCE OF TRUTH FOR XP UPDATES**
        
        This method:
        1. Calculates XP from questions.xp (server-side, secure)
        2. Sums XP from questions answered correctly (based on question IDs)
        3. Saves user_progress record
        4. Updates users.total_xp = users.total_xp + xp_earned
        5. Commits PostgreSQL transaction
        6. Updates Redis ZSET leaderboard (non-blocking)
        
        **SECURITY:** XP is calculated from questions.xp in database, NOT from client input.
        Client cannot manipulate XP by sending fake values.
        
        **XP CALCULATION:**
        - Gets questions WHERE id IN correct_question_ids AND level_id = level_id
        - Sums their XP values: xp_earned = SUM(questions.xp WHERE id IN correct_question_ids)
        - This ensures XP is calculated accurately based on which questions were answered correctly
        
        Determines status based on score:
        - If correct_answers >= min_correct: status = "completed", XP awarded
        - Else: status = "in_progress", NO XP awarded
        
        Also unlocks next level if current level is completed.
        """
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        
        # Get level to check min_correct
        level = await self.repository.get_level_by_id(level_id)
        if not level:
            raise ValueError(f"Level '{level_id}' not found")
        
        # ✅ VALIDATION: Ensure correct_question_ids length matches correct_answers
        if len(correct_question_ids) != correct_answers:
            logger.warning(f"⚠️ [XP_CALC] Mismatch: len(correct_question_ids)={len(correct_question_ids)} != correct_answers={correct_answers}")
            logger.warning(f"   Using correct_question_ids length for XP calculation")
        
        # ✅ CRITICAL: Calculate XP from questions.xp based on correct question IDs
        from app.modules.training.models import TrainingQuestion
        from sqlalchemy import select
        
        # Get all questions for this level (for validation)
        all_questions_stmt = (
            select(TrainingQuestion)
            .where(
                TrainingQuestion.level_id == level_id,
                TrainingQuestion.is_active == True
            )
        )
        all_questions_result = await self.db.execute(all_questions_stmt)
        all_questions = all_questions_result.scalars().all()
        
        # Get all question IDs for this level (for validation)
        all_question_ids = {q.id for q in all_questions}
        
        # Calculate expected total XP (for validation)
        expected_total_xp = sum(q.xp for q in all_questions)
        logger.info(f"📊 [XP_CALC] Level {level_id}: Total questions={len(all_questions)}, Expected total XP={expected_total_xp}")
        
        # ✅ VALIDATION: Ensure all correct_question_ids belong to this level
        correct_ids_set = set(correct_question_ids)
        invalid_ids = correct_ids_set - all_question_ids
        if invalid_ids:
            logger.error(f"❌ [XP_CALC] Invalid question IDs (not belonging to level {level_id}): {invalid_ids}")
            raise ValueError(f"Invalid question IDs: {list(invalid_ids)} do not belong to level {level_id}")
        
        # Determine status
        if correct_answers >= level.min_correct:
            status = "COMPLETED"
            # ✅ Calculate XP from questions.xp based on correct question IDs
            # Get questions WHERE id IN correct_question_ids
            questions_stmt = (
                select(TrainingQuestion)
                .where(
                    TrainingQuestion.level_id == level_id,
                    TrainingQuestion.id.in_(correct_question_ids),  # ✅ Filter by correct question IDs
                    TrainingQuestion.is_active == True
                )
            )
            questions_result = await self.db.execute(questions_stmt)
            correct_questions = questions_result.scalars().all()
            
            # Calculate XP from correct questions
            xp_earned = sum(q.xp for q in correct_questions)
            
            logger.info(f"💰 [XP_CALC] Level {level_id}: correct_answers={correct_answers}")
            logger.info(f"💰 [XP_CALC] Correct question IDs: {correct_question_ids}")
            logger.info(f"💰 [XP_CALC] Questions found: {[q.id for q in correct_questions]}")
            logger.info(f"💰 [XP_CALC] XP per question: {[q.xp for q in correct_questions]}")
            logger.info(f"💰 [XP_CALC] Total xp_earned={xp_earned}")
            
            # ✅ VALIDATION: Ensure xp_earned doesn't exceed expected total
            if xp_earned > expected_total_xp:
                logger.warning(f"⚠️ [XP_CALC] WARNING: xp_earned ({xp_earned}) > expected_total_xp ({expected_total_xp})")
                logger.warning(f"   This should not happen. Clamping to expected_total_xp.")
                xp_earned = expected_total_xp
            
            # ✅ VALIDATION: Ensure we found all questions
            found_question_ids = {q.id for q in correct_questions}
            missing_ids = correct_ids_set - found_question_ids
            if missing_ids:
                logger.warning(f"⚠️ [XP_CALC] WARNING: Some question IDs not found in database: {missing_ids}")
                logger.warning(f"   XP calculation may be incomplete")
        else:
            status = "UNLOCKED" # Treated as UNLOCKED (in progress)
            # ✅ NO XP for incomplete attempts
            xp_earned = 0
            logger.info(f"📊 [XP_CALC] Level {level_id}: Status=in_progress (correct_answers={correct_answers} < min_correct={level.min_correct}), xp_earned=0")
        
        # ✅ CRITICAL: Save progress WITHOUT committing (commit=False)
        # This allows us to update XP in the same transaction
        progress = await self.repository.upsert_user_progress(
            user_id=user_id,
            level_id=level_id,
            status=status,
            score=score,
            total_questions=total_questions,
            correct_answers=correct_answers,
            xp_earned=xp_earned,  # ✅ Server-calculated XP from questions.xp
            time_spent_seconds=time_spent_seconds,
            commit=False,  # ✅ Don't commit yet - we'll commit after XP update
        )
        
        # ✅ CRITICAL: Update users.total_xp in SAME TRANSACTION as progress save
        # This ensures atomicity: both progress and XP update succeed or fail together
        new_total_xp = None  # Initialize for use after commit
        if xp_earned > 0:
            from app.modules.users.models import User
            from sqlalchemy import select
            
            logger.info(f"🔍 [XP_UPDATE] Starting XP update: user_id={user_id}, xp_earned={xp_earned}")
            
            # ✅ Get user in SAME transaction (before any commit)
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                # ✅ Log BEFORE update
                old_total_xp = user.total_xp or 0
                logger.info(f"💰 [XP_UPDATE] User {user_id}: BEFORE total_xp={old_total_xp}, xp_earned={xp_earned}")
                
                # ✅ Update user.total_xp (SINGLE SOURCE OF TRUTH)
                user.total_xp = old_total_xp + xp_earned
                
                # ✅ Flush to stage changes (but don't commit yet)
                await self.db.flush()
                logger.info(f"🔍 [XP_UPDATE] Flushed changes to database (staged, not committed)")
                
                # ✅ Calculate new_total_xp for logging and Redis update
                new_total_xp = user.total_xp or 0
                logger.info(f"💰 [XP_UPDATE] User {user_id}: NEW total_xp={new_total_xp} (was {old_total_xp}, +{xp_earned})")
            else:
                logger.error(f"❌ [XP_UPDATE] User {user_id} not found in database!")
                logger.error(f"   This should not happen if user is authenticated. Check JWT user_id matches database user.id")
                raise ValueError(f"User {user_id} not found in database")
        
        # ✅ CRITICAL: Commit ONCE for both progress and XP update (atomic transaction)
        await self.db.commit()
        logger.info(f"✅ [XP_UPDATE] Committed transaction (progress + XP update)")
        
        # ✅ REFRESH CACHE: Invalidate map progress to force fresh fetch
        # The new architecture requires deleting the key so next read fetches DB -> Cache
        try:
            redis = await get_redis()
            # 1. Update individual level status (for quick lookups)
            cache_key_levels = CacheKeys.levels(str(user_id))
            await redis.hset(cache_key_levels, level_id, status)
            await redis.expire(cache_key_levels, CACHE_TTL_LEVELS)
            
            # 2. INVALIDATE the full map progress list
            cache_key_map = CacheKeys.map_progress(str(user_id))
            await redis.delete(cache_key_map)
            
            logger.info(f"🔓 [REDIS] Updated level {level_id} -> {status}, Invalidated map cache")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update level status in Redis: {e}")
        
        # ✅ Refresh progress to get latest data
        await self.db.refresh(progress)
        
        # ✅ Verify XP update persisted by querying again (after commit)
        if xp_earned > 0 and new_total_xp is not None:
            from app.modules.users.models import User
            from sqlalchemy import select
            
            verify_stmt = select(User).where(User.id == user_id)
            verify_result = await self.db.execute(verify_stmt)
            verify_user = verify_result.scalar_one_or_none()
            
            if verify_user:
                verify_total_xp = verify_user.total_xp or 0
                logger.info(f"🔍 [XP_UPDATE] Verification query: total_xp={verify_total_xp}")
                
                if verify_total_xp != new_total_xp:
                    logger.error(f"❌ [XP_UPDATE] MISMATCH! Expected total_xp={new_total_xp}, DB total_xp={verify_total_xp}")
                else:
                    logger.info(f"✅ [XP_UPDATE] Verification OK: total_xp={verify_total_xp} matches expected value")
                
                # ✅ THEN update Redis leaderboard AFTER PostgreSQL commit succeeds
                # Redis is cache-only, PostgreSQL is source of truth
                try:
                    from app.modules.gamification.service import LeaderboardService
                    leaderboard_service = LeaderboardService(self.db)
                    
                    logger.info(f"🔄 [REDIS] Updating Redis leaderboard: user_id={user_id}, total_xp={verify_total_xp}")
                    await leaderboard_service.update_user_score(
                        user_id=str(user_id),
                        total_xp=verify_total_xp  # ✅ Use verified total_xp from PostgreSQL
                    )
                    
                    # ✅ VERIFY Redis update succeeded
                    try:
                        from app.core.redis import get_redis
                        from app.modules.gamification.service import LEADERBOARD_KEY
                        redis_client = await get_redis()
                        verify_score = await redis_client.zscore(LEADERBOARD_KEY, str(user_id))
                        verify_rank = await redis_client.zrevrank(LEADERBOARD_KEY, str(user_id))
                        
                        if verify_score is not None:
                            logger.info(f"✅ [REDIS_VERIFY] User {user_id}: score={int(verify_score)}, rank={int(verify_rank) + 1 if verify_rank is not None else 'N/A'}")
                        else:
                            logger.warning(f"⚠️ [REDIS_VERIFY] User {user_id}: Redis update returned None (may be normal if Redis is down)")
                    except Exception as verify_error:
                        logger.warning(f"⚠️ [REDIS_VERIFY] Could not verify Redis update: {verify_error}")
                    
                    # ✅ Publish to Redis Pub/Sub for real-time SSE clients — O(N+M)
                    try:
                        await leaderboard_service.publish_leaderboard_update(
                            user_id=str(user_id),
                            total_xp=verify_total_xp
                        )
                    except Exception as pub_error:
                        logger.warning(f"⚠️ [PUBSUB] Could not publish update: {pub_error}")
                    
                except Exception as e:
                    # ✅ CRITICAL: Don't fail the request if Redis update fails
                    # PostgreSQL is source of truth, Redis is cache-only
                    logger.error(f"❌ [REDIS] Failed to update Redis leaderboard: {e}")
                    import traceback
                    logger.error(f"   Traceback: {traceback.format_exc()}")
                    # PostgreSQL is still updated, so request succeeds
            else:
                logger.error(f"❌ [XP_UPDATE] Verification query failed: User {user_id} not found after commit!")
        
        # If completed, unlock next level
        next_level_id = None
        if status == "COMPLETED":
            next_level_id = await self._unlock_next_level(user_id, level)
            
        # ✅ FORCE REDIS INVALIDATION (FINAL SAFETY NET)
        # This ensures that even if _unlock_next_level failed to invalidate, we do it here
        try:
            redis = await get_redis()
            cache_key_map = CacheKeys.map_progress(str(user_id))
            cache_key_levels = CacheKeys.levels(str(user_id))
            
            # Delete map progress (to refresh path)
            await redis.delete(cache_key_map)
            
            # Update current level status in Redis hash
            await redis.hset(cache_key_levels, level_id, status)
            
            logger.info(f"🧹 [SUBMIT] Final cache invalidation for user {user_id} (Map deleted, Level updated)")
        except Exception as e:
            logger.warning(f"⚠️ Final cache invalidation failed: {e}")
        
        # ✅ Return proper dictionary response
        # This matches what the frontend expects
        return {
            "status": status,
            "xp_earned": xp_earned,
            "total_xp": new_total_xp if new_total_xp is not None else 0,
            "streak": 0, # TODO: Implement streak logic properly
            "next_level_id": next_level_id,
            "level_id": level_id
        }
    
    async def _unlock_next_level(self, user_id: int, completed_level: TrainingLevel):
        """
        GLOBAL LINEAR PROGRESSION: Unlock the NEXT level in GLOBAL order.
        
        Global Order: Section.order → Unit.order → Level.level_number
        
        Example progression (5 sections × 5 units × 5 levels = 125 levels):
        puk_u1_l1 → puk_u1_l2 → ... → puk_u1_l5 → puk_u2_l1 → ... → puk_u5_l5 → ppgd_u1_l1 → ...
        """
        if not self.repository:
            raise ValueError("Repository required")
            
        from sqlalchemy import select
        from app.modules.training.models import TrainingLevel, TrainingUnit, TrainingSection
        
        # ✅ Get current level's global position
        current_unit_stmt = select(TrainingUnit).where(TrainingUnit.id == completed_level.unit_id)
        current_unit_result = await self.db.execute(current_unit_stmt)
        current_unit = current_unit_result.scalar_one_or_none()
        
        if not current_unit:
            logger.error(f"❌ [GLOBAL] Unit not found for level {completed_level.id}")
            return
            
        current_section_stmt = select(TrainingSection).where(TrainingSection.id == current_unit.section_id)
        current_section_result = await self.db.execute(current_section_stmt)
        current_section = current_section_result.scalar_one_or_none()
        
        if not current_section:
            logger.error(f"❌ [GLOBAL] Section not found for unit {current_unit.id}")
            return
        
        logger.info(f"🔍 [GLOBAL] Current position: Section {current_section.order}, Unit {current_unit.order}, Level {completed_level.level_number}")
        
        next_level = None
        
        # ✅ Priority 1: Next level in SAME unit
        next_in_unit_stmt = (
            select(TrainingLevel)
            .where(
                TrainingLevel.unit_id == completed_level.unit_id,
                TrainingLevel.level_number == completed_level.level_number + 1,
                TrainingLevel.is_active == True
            )
        )
        result = await self.db.execute(next_in_unit_stmt)
        next_level = result.scalar_one_or_none()
        
        if next_level:
            logger.info(f"🔓 [GLOBAL] Next level in same unit: {next_level.id}")
        
        # ✅ Priority 2: DONE (Parallel Units Logic)
        # We DO NOT auto-unlock the next unit. Units are parallel and independent.
        # If no next level is found in the current unit, the unit is considered COMPLETED.
        if not next_level:
            logger.info(f"🏁 [GLOBAL] Unit {current_unit.id} completed. No next level to unlock (Parallel Units).")
            return None
        
        # ✅ Priority 3: Removed (Sections are disconnected in Parallel Mode)
        
        # ✅ Create unlock record
        if next_level:
            existing = await self.repository.get_user_progress(user_id, next_level.id)

            if not existing:
                await self.repository.upsert_user_progress(
                    user_id=user_id,
                    level_id=next_level.id,
                    status="UNLOCKED",
                    commit=True,
                )
                
                # Invalidate all cache for this user
                try:
                    redis = await get_redis()
                    cache_key_map = CacheKeys.map_progress(str(user_id))
                    await redis.delete(cache_key_map)
                    logger.info(f"🔓 [GLOBAL] Unlocked {next_level.id} for user {user_id} - Cache Invalidated")
                except Exception as e:
                    logger.warning(f"⚠️ Redis cache invalidation failed: {e}")
            
            return next_level.id
        else:
            logger.info(f"🏁 [GLOBAL] No next level found. User {user_id} completed all content!")
            return None
    
    async def get_progress_state(self, user_id: int, section_id: Optional[str] = None) -> Dict[str, str]:
        """
        Get progress state for ALL levels as a JSON List.
        SERVER-SIDE SOURCE OF TRUTH.
        
        ✅ STRICT LINEAR: If user has NO progress, auto-unlock first level only.
        
        NOTE: We ignore 'section_id' for the DB query to ensure the global 'map_progress' 
        cache key is always populated with COMPLETE data, preventing cache corruption 
        (where partial data overwrites global data).
        """
        import json
        
        if not self.repository:
            raise ValueError("Repository required")
            
        cache_key = CacheKeys.map_progress(str(user_id))
        
        # ✅ Step 1: Try Redis Cache (but validate statuses are normalized)
        try:
            redis = await get_redis()
            cached_json = await redis.get(cache_key)
            if cached_json:
                cached_data = json.loads(cached_json)
                # Check if cache has legacy statuses that need normalization
                has_legacy = any(v in ("AVAILABLE", "IN_PROGRESS") for v in cached_data.values())
                if not has_legacy:
                    logger.info(f"📦 [CACHE HIT] Map progress for user {user_id}")
                    return cached_data
                else:
                    # Invalidate stale cache with legacy statuses
                    await redis.delete(cache_key)
                    logger.info(f"🧹 [CACHE] Invalidated stale cache with legacy statuses for user {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Redis read failed in get_progress_state: {e}")
            
        # ✅ Step 2: DB Fallback (Cache Miss)
        logger.info(f"📊 [CACHE MISS] Fetching map progress from DB for user {user_id}")
        
        # ✅ ALWAYS fetch GLOBAL progress (pass section_id=None)
        # This ensures we don't cache partial data under the global key
        progress_list = await self.repository.get_user_progress_by_section(user_id, None)
        
        # ✅ PARALLEL UNITS: Always ensure ALL Level 1s are UNLOCKED
        # This runs for ALL users (not just new users) to guarantee Level 1 accessibility
        from sqlalchemy import select
        from app.modules.training.models import TrainingLevel, TrainingUnit, TrainingSection
        
        level1_stmt = (
            select(TrainingLevel)
            .join(TrainingUnit, TrainingLevel.unit_id == TrainingUnit.id)
            .join(TrainingSection, TrainingUnit.section_id == TrainingSection.id)
            .where(
                TrainingLevel.level_number == 1,
                TrainingLevel.is_active == True,
                TrainingUnit.is_active == True,
                TrainingSection.is_active == True,
            )
        )
        level1_result = await self.db.execute(level1_stmt)
        all_level1s = level1_result.scalars().all()
        
        # Build set of existing level IDs for quick lookup
        existing_level_ids = {p.level_id for p in progress_list}
        
        # Create UNLOCKED records for any Level 1 that doesn't have a progress record
        new_records_created = 0
        for level in all_level1s:
            if level.id not in existing_level_ids:
                await self.repository.upsert_user_progress(
                    user_id=user_id,
                    level_id=level.id,
                    status="UNLOCKED",
                    commit=False,
                )
                new_records_created += 1
        
        if new_records_created > 0:
            await self.db.commit()
            logger.info(f"🔓 [PROGRESS] Created {new_records_created} missing Level 1 UNLOCKED records for user {user_id}")
            # Re-fetch to include newly created records
            progress_list = await self.repository.get_user_progress_by_section(user_id, None)
        
        # ✅ Normalize legacy statuses to frontend-expected values
        # DB may contain: AVAILABLE, IN_PROGRESS, COMPLETED, UNLOCKED, LOCKED
        # Frontend expects: UNLOCKED, LOCKED, COMPLETED
        STATUS_MAP = {
            "COMPLETED": "COMPLETED",
            "UNLOCKED": "UNLOCKED",
            "AVAILABLE": "UNLOCKED",      # Legacy: AVAILABLE → UNLOCKED
            "IN_PROGRESS": "UNLOCKED",    # Legacy: IN_PROGRESS → UNLOCKED (started but not completed)
            "LOCKED": "LOCKED",
        }
        
        # Format as dict: {level_id: normalized_status}
        result_dict = {
            p.level_id: STATUS_MAP.get(p.status.upper(), "LOCKED")
            for p in progress_list
        }
        
        # ✅ SAFETY NET: Ensure ALL Level 1s are at least UNLOCKED in the result
        for level in all_level1s:
            if level.id not in result_dict or result_dict[level.id] == "LOCKED":
                result_dict[level.id] = "UNLOCKED"
        
        # ✅ Step 3: Cache result
        try:
            redis = await get_redis()
            await redis.setex(
                cache_key,
                3600,  # 1 hour
                json.dumps(result_dict)
            )
            logger.info(f"💾 [CACHE SET] Map progress cached for user {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Redis cache failed in get_progress_state: {e}")
        
        return result_dict