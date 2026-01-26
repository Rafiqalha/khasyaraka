"""
Training Data Verification Module

Production-grade verification that core training data exists.
Called on application startup to ensure system is ready.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.modules.training.models import TrainingSection, TrainingUnit, TrainingLevel, TrainingQuestion
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_training_data(db: AsyncSession) -> dict:
    """
    Verify that core training data exists in database.
    
    Returns:
        dict with verification results:
        {
            "sections_count": int,
            "puk_section_exists": bool,
            "puk_section_active": bool,
            "puk_units_count": int,
            "puk_levels_count": int,
            "puk_questions_count": int,
            "is_ready": bool
        }
    """
    try:
        # Check sections
        sections_stmt = select(func.count(TrainingSection.id))
        sections_result = await db.execute(sections_stmt)
        sections_count = sections_result.scalar() or 0
        
        # Check PUK section specifically
        puk_section_stmt = select(TrainingSection).where(TrainingSection.id == "puk")
        puk_section_result = await db.execute(puk_section_stmt)
        puk_section = puk_section_result.scalar_one_or_none()
        
        puk_section_exists = puk_section is not None
        puk_section_active = puk_section.is_active if puk_section else False
        
        # Check PUK units
        puk_units_stmt = select(func.count(TrainingUnit.id)).where(
            TrainingUnit.section_id == "puk"
        )
        puk_units_result = await db.execute(puk_units_stmt)
        puk_units_count = puk_units_result.scalar() or 0
        
        # Check PUK levels
        puk_levels_stmt = select(func.count(TrainingLevel.id)).where(
            TrainingLevel.unit_id.like("puk_%")
        )
        puk_levels_result = await db.execute(puk_levels_stmt)
        puk_levels_count = puk_levels_result.scalar() or 0
        
        # Check PUK questions
        puk_questions_stmt = select(func.count(TrainingQuestion.id)).where(
            TrainingQuestion.level_id.like("puk_%")
        )
        puk_questions_result = await db.execute(puk_questions_stmt)
        puk_questions_count = puk_questions_result.scalar() or 0
        
        # Determine if system is ready
        is_ready = (
            puk_section_exists and
            puk_section_active and
            puk_units_count > 0 and
            puk_levels_count > 0 and
            puk_questions_count > 0
        )
        
        result = {
            "sections_count": sections_count,
            "puk_section_exists": puk_section_exists,
            "puk_section_active": puk_section_active,
            "puk_units_count": puk_units_count,
            "puk_levels_count": puk_levels_count,
            "puk_questions_count": puk_questions_count,
            "is_ready": is_ready
        }
        
        if not is_ready:
            logger.error(
                "❌ TRAINING DATA VERIFICATION FAILED",
                extra=result
            )
        else:
            logger.info(
                "✅ Training data verification passed",
                extra=result
            )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error verifying training data: {e}", exc_info=True)
        return {
            "sections_count": 0,
            "puk_section_exists": False,
            "puk_section_active": False,
            "puk_units_count": 0,
            "puk_levels_count": 0,
            "puk_questions_count": 0,
            "is_ready": False,
            "error": str(e)
        }
