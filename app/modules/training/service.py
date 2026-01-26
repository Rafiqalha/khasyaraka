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
        """Get all active sections"""
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        return await self.repository.get_all_sections()

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
        Get structured learning path for a section.
        Returns Duolingo-style learning path with section → units → levels.
        
        Args:
            section_id: Section ID (e.g., 'puk')
            user_id: Optional user ID to determine level status based on progress
        """
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        
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
        
        return LearningPathResponse(
            section_id=section.id,
            section_title=section.title,
            units=units_data
        )
    
    async def _determine_level_status(self, level: TrainingLevel, user_id: Optional[int] = None) -> str:
        """
        Determine level status based on unlock_rule and user progress.
        
        Status values:
        - "locked": Level is locked (previous level not completed)
        - "available": Level is unlocked and available to play
        - "in_progress": User has started but not completed this level
        - "completed": User has completed this level
        """
        if not user_id:
            # No user context: only unlock level 1 of each unit
            if level.level_number == 1:
                return "available"
            return "locked"
        
        # Get user progress for this level
        progress = await self.repository.get_user_progress(user_id, level.id)
        
        if progress:
            # User has progress: return their status
            return progress.status
        
        # No progress yet: check unlock rule
        unlock_rule = level.unlock_rule or {}
        rule_type = unlock_rule.get("type")
        
        if rule_type == "start":
            # First level: always available
            return "available"
        elif rule_type == "level_completed":
            # Check if prerequisite level is completed
            prereq_level_id = unlock_rule.get("value")
            if prereq_level_id:
                prereq_progress = await self.repository.get_user_progress(user_id, prereq_level_id)
                if prereq_progress and prereq_progress.status == "completed":
                    return "available"
            return "locked"
        else:
            # Unknown rule: default to locked
            return "locked"
    
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
            status = "completed"
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
            status = "in_progress"
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
        if status == "completed":
            await self._unlock_next_level(user_id, level)
        
        return progress
    
    async def _unlock_next_level(self, user_id: int, completed_level: TrainingLevel):
        """Unlock the next level in the same unit after completing current level"""
        # Get all levels in the unit
        unit_levels = await self.repository.get_levels_by_unit(completed_level.unit_id)
        unit_levels = sorted(unit_levels, key=lambda l: l.level_number)
        
        # Find next level
        next_level = None
        for level in unit_levels:
            if level.level_number == completed_level.level_number + 1:
                next_level = level
                break
        
        if next_level:
            # Check if user already has progress for next level
            existing = await self.repository.get_user_progress(user_id, next_level.id)
            if not existing:
                # Create progress with "available" status
                # ✅ Commit here since this is a separate operation after main transaction
                await self.repository.upsert_user_progress(
                    user_id=user_id,
                    level_id=next_level.id,
                    status="available",
                    commit=True,  # ✅ Commit this separate operation
                )
    
    async def get_progress_state(self, user_id: int, section_id: str) -> dict:
        """
        Get progress state for all levels in a section.
        
        Returns a dict mapping level_id to status.
        """
        if not self.repository:
            raise ValueError("Database session required for repository-based methods")
        
        progress_list = await self.repository.get_user_progress_by_section(user_id, section_id)
        
        # Build dict: level_id -> status
        progress_dict = {}
        for progress in progress_list:
            progress_dict[progress.level_id] = progress.status
        
        return progress_dict