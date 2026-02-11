"""
Training Module Router

All training-related API endpoints consolidated in one router.
Uses service layer for business logic, which uses repository for database access.
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.session import get_db
from app.core.security import get_current_user, get_current_user_optional
from app.modules.training.service import TrainingService
from app.modules.training.schemas import (
    # Legacy schemas (for backward compatibility)
    PathSchema,
    QuestionSchema,
    # New SQLAlchemy-based schemas
    SectionListResponse,
    TrainingSectionResponse,
    UnitListResponse,
    TrainingUnitResponse,
    LevelListResponse,
    TrainingLevelResponse,
    QuestionListResponse,
    TrainingQuestionResponse,
    LearningPathResponse,
)

router = APIRouter(prefix="/training", tags=["Training"])


# ==================== DEPENDENCY INJECTION ====================

def get_service(db: AsyncSession = Depends(get_db)) -> TrainingService:
    """Dependency for TrainingService with database session"""
    return TrainingService(db=db)


# ==================== LEGACY ENDPOINTS (DEPRECATED - for backward compatibility) ====================

@router.get("/path", response_model=List[PathSchema])
async def get_path(service: TrainingService = Depends(get_service)):
    """
    DEPRECATED: Legacy endpoint for Supabase-based learning paths.
    Kept for backward compatibility but returns empty list.
    TODO: Migrate to use SQLAlchemy models or remove if no longer needed.
    """
    return await service.get_learning_path()


@router.get("/questions/{lesson_id}", response_model=List[QuestionSchema])
async def get_questions(lesson_id: int, service: TrainingService = Depends(get_service)):
    """
    DEPRECATED: Legacy endpoint for Supabase-based questions.
    Kept for backward compatibility but returns empty list.
    TODO: Migrate to use SQLAlchemy models or remove if no longer needed.
    """
    return await service.get_questions_by_lesson(lesson_id)


# ==================== NEW ENDPOINTS (Repository-based via Service) ====================

# ==================== SECTION ENDPOINTS ====================

@router.get(
    "/sections",
    response_model=SectionListResponse,
    summary="Get all training sections",
    description="Retrieve all active training sections ordered by their display order"
)
async def get_sections(
    service: TrainingService = Depends(get_service)
):
    """
    Get all active training sections.
    
    Returns:
        - List of sections with metadata
        - Only includes sections where is_active = true
        - Ordered by 'order' field
    """
    sections = await service.get_all_sections()
    
    return SectionListResponse(
        total=len(sections),
        sections=sections
    )


@router.get(
    "/sections/{section_id}",
    response_model=TrainingSectionResponse,
    summary="Get a specific training section",
    description="Retrieve details of a specific training section by ID"
)
async def get_section(
    section_id: str,
    service: TrainingService = Depends(get_service)
):
    """
    Get a specific training section by ID.
    
    Args:
        - section_id: Section ID (e.g., 'puk')
    
    Returns:
        - Section details
    
    Raises:
        - 404: Section not found or inactive
    """
    section = await service.get_section_by_id(section_id)
    
    if not section:
        raise HTTPException(
            status_code=404,
            detail=f"Section '{section_id}' not found or inactive"
        )
    
    return section


# ==================== UNIT ENDPOINTS ====================

@router.get(
    "/sections/{section_id}/units",
    response_model=UnitListResponse,
    summary="Get units in a section",
    description="Retrieve all active training units for a specific section"
)
async def get_section_units(
    section_id: str,
    service: TrainingService = Depends(get_service)
):
    """
    Get all units for a specific section.
    
    Args:
        - section_id: Parent section ID (e.g., 'puk')
    
    Returns:
        - List of units in this section
        - Only includes units where is_active = true
        - Ordered by 'order' field
    
    Raises:
        - 404: Section not found or inactive
    """
    # First, verify section exists
    section = await service.get_section_by_id(section_id)
    if not section:
        raise HTTPException(
            status_code=404,
            detail=f"Section '{section_id}' not found or inactive"
        )
    
    # Get units for this section
    units = await service.get_units_by_section(section_id)
    
    return UnitListResponse(
        total=len(units),
        section_id=section_id,
        units=units
    )


@router.get(
    "/units/{unit_id}",
    response_model=TrainingUnitResponse,
    summary="Get a specific training unit",
    description="Retrieve details of a specific training unit by ID"
)
async def get_unit(
    unit_id: str,
    service: TrainingService = Depends(get_service)
):
    """
    Get a specific training unit by ID.
    
    Args:
        - unit_id: Unit ID (e.g., 'puk_unit_1')
    
    Returns:
        - Unit details
    
    Raises:
        - 404: Unit not found or inactive
    """
    unit = await service.get_unit_by_id(unit_id)
    
    if not unit:
        raise HTTPException(
            status_code=404,
            detail=f"Unit '{unit_id}' not found or inactive"
        )
    
    return unit


# ==================== LEVEL ENDPOINTS ====================

@router.get(
    "/units/{unit_id}/levels",
    response_model=LevelListResponse,
    summary="Get levels in a unit",
    description="Retrieve all active training levels for a specific unit"
)
async def get_unit_levels(
    unit_id: str,
    service: TrainingService = Depends(get_service)
):
    """
    Get all levels for a specific unit.
    
    Args:
        - unit_id: Parent unit ID (e.g., 'puk_unit_1')
    
    Returns:
        - List of levels in this unit
        - Only includes levels where is_active = true
        - Ordered by 'level_number' field
    
    Raises:
        - 404: Unit not found or inactive
    """
    # First, verify unit exists
    unit = await service.get_unit_by_id(unit_id)
    if not unit:
        raise HTTPException(
            status_code=404,
            detail=f"Unit '{unit_id}' not found or inactive"
        )
    
    # Get levels for this unit
    levels = await service.get_levels_by_unit(unit_id)
    
    return LevelListResponse(
        total=len(levels),
        unit_id=unit_id,
        levels=levels
    )


@router.get(
    "/levels/{level_id}",
    response_model=TrainingLevelResponse,
    summary="Get a specific training level",
    description="Retrieve details of a specific training level by ID"
)
async def get_level(
    level_id: str,
    service: TrainingService = Depends(get_service)
):
    """
    Get a specific training level by ID.
    
    Args:
        - level_id: Level ID (e.g., 'puk_u1_l1')
    
    Returns:
        - Level details including unlock rules and XP rewards
    
    Raises:
        - 404: Level not found or inactive
    """
    level = await service.get_level_by_id(level_id)
    
    if not level:
        raise HTTPException(
            status_code=404,
            detail=f"Level '{level_id}' not found or inactive"
        )
    
    return level


# ==================== QUESTION ENDPOINTS ====================

@router.get(
    "/units/{unit_id}/questions",
    response_model=QuestionListResponse,
    summary="Get all questions in a unit",
    description="Retrieve all active training questions from all levels in a specific unit"
)
async def get_unit_questions(
    unit_id: str,
    service: TrainingService = Depends(get_service)
):
    """
    Get all questions from all levels in a specific unit.
    
    This endpoint aggregates questions from all levels in the unit,
    useful for unit-based quiz sessions.
    
    Args:
        - unit_id: Unit ID (e.g., 'puk_u1')
    
    Returns:
        - List of all questions from all levels in this unit
        - Only includes questions where is_active = true
        - Ordered by level_number, then by question order
        - Includes question payload (options, pairs, etc.)
    
    Raises:
        - 404: Unit not found or inactive
    """
    # First, verify unit exists
    unit = await service.get_unit_by_id(unit_id)
    if not unit:
        raise HTTPException(
            status_code=404,
            detail=f"Unit '{unit_id}' not found or inactive"
        )
    
    # Get all questions from all levels in this unit
    questions = await service.get_questions_by_unit(unit_id)
    
    return QuestionListResponse(
        total=len(questions),
        level_id=unit_id,  # Use unit_id as identifier for unit-based questions
        questions=questions
    )


@router.get(
    "/levels/{level_id}/questions",
    response_model=QuestionListResponse,
    summary="Get questions in a level",
    description="Retrieve all active training questions for a specific level"
)
async def get_level_questions(
    level_id: str,
    service: TrainingService = Depends(get_service)
):
    """
    Get all questions for a specific level.
    
    Args:
        - level_id: Parent level ID (e.g., 'puk_u1_l1')
    
    Returns:
        - List of questions in this level
        - Only includes questions where is_active = true
        - Ordered by 'order' field
        - Includes question payload (options, pairs, etc.)
    
    Raises:
        - 404: Level not found or inactive
    """
    # First, verify level exists
    level = await service.get_level_by_id(level_id)
    if not level:
        raise HTTPException(
            status_code=404,
            detail=f"Level '{level_id}' not found or inactive"
        )
    
    # Get questions for this level
    questions = await service.get_questions_by_level(level_id)
    
    return QuestionListResponse(
        total=len(questions),
        level_id=level_id,
        questions=questions
    )


@router.get(
    "/questions/{question_id}",
    response_model=TrainingQuestionResponse,
    summary="Get a specific training question",
    description="Retrieve details of a specific training question by ID"
)
async def get_question(
    question_id: str,
    service: TrainingService = Depends(get_service)
):
    """
    Get a specific training question by ID.
    
    Args:
        - question_id: Question ID (e.g., 'q_puk_u1_l1_01')
    
    Returns:
        - Question details including payload
        - Payload contains question-specific data (options, correct answer, etc.)
    
    Raises:
        - 404: Question not found or inactive
    """
    question = await service.get_question_by_id(question_id)
    
    if not question:
        raise HTTPException(
            status_code=404,
            detail=f"Question '{question_id}' not found or inactive"
        )
    
    return question


# ==================== LEARNING PATH ENDPOINT ====================

@router.get(
    "/sections/{section_id}/path",
    response_model=LearningPathResponse,
    summary="Get learning path for a section",
    description="Retrieve a Duolingo-style learning path with section → units → levels structure"
)
async def get_learning_path(
    section_id: str,
    request: Request,
    service: TrainingService = Depends(get_service)
):
    """
    Get structured learning path for a section.
    
    Args:
        - section_id: Section ID (e.g., 'puk')
        - request: FastAPI Request (for optional auth)
    
    Returns:
        - Structured learning path with units and levels
        - Level status based on user progress if authenticated
    
    Raises:
        - 404: Section not found or inactive
    """
    # ✅ Get user_id from JWT if authenticated (optional, no 401 if missing)
    current_user = get_current_user_optional(request)
    user_id = None
    if current_user:
        user_id = int(current_user.get("sub"))
    
    learning_path = await service.get_learning_path_for_section(section_id, user_id=user_id)
    
    if not learning_path:
        raise HTTPException(
            status_code=404,
            detail=f"Section '{section_id}' not found or inactive"
        )
    
    return learning_path


# ==================== PROGRESS ENDPOINTS ====================

@router.post(
    "/progress/submit",
    response_model=dict,
    summary="Submit level completion progress",
    description="Submit user progress after completing a level quiz. This is the SINGLE SOURCE OF TRUTH for XP updates."
)
async def submit_progress(
    level_id: str = Body(...),
    score: int = Body(...),
    total_questions: int = Body(...),
    correct_answers: int = Body(...),
    correct_question_ids: List[str] = Body(...),  # ✅ NEW: List of question IDs answered correctly
    time_spent_seconds: int = Body(0),
    current_user: dict = Depends(get_current_user),  # ✅ REQUIRED: Must be authenticated
    service: TrainingService = Depends(get_service)
):
    """
    Submit user progress for a completed level.
    
    **SINGLE SOURCE OF TRUTH FOR XP UPDATES**
    
    This endpoint:
    1. Saves user_progress record
    2. Updates users.total_xp = users.total_xp + xp_earned (calculated from questions.xp)
    3. Commits PostgreSQL transaction
    4. Updates Redis ZSET leaderboard
    
    **SECURITY:** XP is calculated server-side from questions.xp, NOT from client.
    Client cannot manipulate XP by sending fake xp_earned values.
    
    **XP CALCULATION:**
    - Gets questions WHERE id IN correct_question_ids
    - Sums their XP values: xp_earned = SUM(questions.xp WHERE id IN correct_question_ids)
    - This ensures XP is calculated accurately based on which questions were answered correctly
    
    Args:
        - level_id: Level ID (e.g., 'puk_u1_l1')
        - score: Total score
        - total_questions: Total number of questions
        - correct_answers: Number of correct answers (for validation)
        - correct_question_ids: List of question IDs answered correctly (for XP calculation)
        - time_spent_seconds: Time spent in seconds
        - current_user: JWT authenticated user (REQUIRED)
    
    Returns:
        - Progress record with status (completed/in_progress)
        - XP earned (calculated server-side from questions.xp)
        - Next level is automatically unlocked if current level is completed
    
    Raises:
        - 401: Not authenticated
        - 404: Level not found
        - 400: Invalid question IDs (not belonging to level)
    """
    # ✅ Get user_id from JWT authentication (REQUIRED)
    user_id = int(current_user.get("sub"))
    
    # ✅ CRITICAL DEBUG: Log user_id and request details
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info(f"🔍 [SUBMIT_PROGRESS] Request received: user_id={user_id}, level_id={level_id}, correct_answers={correct_answers}")
    logger.info(f"🔍 [SUBMIT_PROGRESS] Correct question IDs: {correct_question_ids}")
    
    try:
        # ✅ service.submit_progress() returns a DICT, use bracket access
        progress = await service.submit_progress(
            user_id=user_id,
            level_id=level_id,
            score=score,
            total_questions=total_questions,
            correct_answers=correct_answers,
            correct_question_ids=correct_question_ids,
            time_spent_seconds=time_spent_seconds,
        )
        
        # ✅ CRITICAL: Get current user state from database AFTER submit_progress
        from app.modules.users.models import User
        from sqlalchemy import select
        from datetime import date, timedelta
        
        stmt = select(User).where(User.id == user_id)
        result = await service.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        current_total_xp = (user.total_xp or 0) if user else 0
        current_streak = (user.streak or 0) if user else 0
        
        # ✅ Calculate and update streak server-side
        today = date.today()
        last_active = user.last_active_date if user else None
        
        if last_active is None:
            new_streak = 1
        elif last_active == today:
            new_streak = current_streak
        elif last_active == today - timedelta(days=1):
            new_streak = current_streak + 1
        else:
            new_streak = 1
        
        # ✅ Update streak and last_active_date in database
        if user:
            user.streak = new_streak
            user.last_active_date = today
            await service.db.commit()
            await service.db.refresh(user)
        
        xp_earned = progress.get("xp_earned", 0)
        logger.info(f"✅ [SUBMIT_PROGRESS] Response: xp_earned={xp_earned}, total_xp={current_total_xp}, streak={new_streak}")
        
        # ✅ Return COMPLETE user state - frontend needs NO additional API calls
        return {
            "success": True,
            "level_id": progress.get("level_id", level_id),
            "status": progress.get("status", "UNLOCKED"),
            "score": score,
            "correct_answers": correct_answers,
            "total_questions": total_questions,
            "xp_earned": xp_earned,
            "total_xp": (user.total_xp or 0) if user else current_total_xp,
            "streak": new_streak,
            "next_level_id": progress.get("next_level_id"),
            "last_active_date": today.isoformat() if today else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/progress/state",
    response_model=dict,
    summary="Get user progress state",
    description="Get progress state for all levels in a section"
)
async def get_progress_state(
    request: Request,
    section_id: Optional[str] = None,
    service: TrainingService = Depends(get_service)
):
    """
    Get progress state for all levels in a section.
    
    Args:
        - section_id: Section ID (e.g., 'puk') - Optional
        - request: FastAPI Request (for optional auth)
    
    Returns:
        - Dict mapping level_id to status (locked/available/in_progress/completed)
        - If not authenticated, returns default statuses (level 1 unlocked)
    """
    # ✅ Get user_id from JWT if authenticated (optional, no 401 if missing)
    current_user = get_current_user_optional(request)
    user_id = None
    if current_user:
        user_id = int(current_user.get("sub"))
    
    progress_dict = await service.get_progress_state(user_id, section_id)
    
    return {
        "success": True,
        "section_id": section_id,
        "progress": progress_dict,
    }
