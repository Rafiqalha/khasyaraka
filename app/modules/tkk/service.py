import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException

from app.core.config import settings
from app.core.redis import get_redis

from app.modules.tkk.models import UserTKK, TKKLevel
from app.modules.tkk.schemas import TKKVerificationResult, TKKBase, TKKLevelEnum
# Assuming a way to load metadata. For now, reading file directly or using a helper.
# In a real app, this might be loaded at startup.

from pathlib import Path

# Calculate project root (assuming standard structure: app/modules/tkk/service.py)
# Parent of app/modules/tkk/service.py is app/modules/tkk
# Parent x2 is app/modules
# Parent x3 is app
# Parent x4 is project root (scout_os_backend)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
METADATA_PATH = BASE_DIR / "app/data/tkk_metadata.json"

def load_metadata():
    if not os.path.exists(METADATA_PATH):
        return []
    with open(METADATA_PATH, "r") as f:
        return json.load(f)

TKK_METADATA = load_metadata()

def get_tkk_metadata(slug: str) -> Optional[Dict[str, Any]]:
    for item in TKK_METADATA:
        if item["slug"] == slug:
            return item
    return None

async def process_tkk_submission(
    db: Session, user_id: int, slug: str, answers: Dict[str, Any]
) -> TKKVerificationResult:
    # 1. Validate TKK exists
    metadata = get_tkk_metadata(slug)
    if not metadata:
        raise HTTPException(status_code=404, detail="TKK not found")

    # 2. Calculate Score (Simplified logic: mocked score calculation)
    # In reality, this would check answers against a key or use an LLM grader.
    # For now, we assume 'answers' contains a 'score' field for testing, or we default to 100 if not provided
    # to simulate a pass. In a real implementation, this needs proper grading.
    score = answers.get("score", 85)  # Default high score for dev/testing if not specified
    is_passing = score >= 80

    if not is_passing:
        return TKKVerificationResult(
            success=False,
            score=score,
            message="Score insufficient to pass.",
            awarded_level=None
        )

    # 3. Check existing level
    stmt = select(UserTKK).where(UserTKK.user_id == user_id, UserTKK.tkk_slug == slug)
    existing_entry = db.execute(stmt).scalar_one_or_none()
    
    new_level = None
    previous_level = None

    if existing_entry:
        previous_level = existing_entry.level
        # Progression Logic
        if existing_entry.level == TKKLevel.PURWA:
            new_level = TKKLevel.MADYA
        elif existing_entry.level == TKKLevel.MADYA:
            new_level = TKKLevel.UTAMA
        else:
            # Already UTAMA
             return TKKVerificationResult(
                success=True,
                score=score,
                message="You have already attained the highest level (Utama).",
                awarded_level=TKKLevel.UTAMA,
                previous_level=TKKLevel.UTAMA
            )
        
        # Update existing
        existing_entry.level = new_level
        existing_entry.attained_at = datetime.utcnow()
    else:
        # New Award -> Purwa
        new_level = TKKLevel.PURWA
        new_entry = UserTKK(
            user_id=user_id,
            tkk_slug=slug,
            level=new_level,
            attained_at=datetime.utcnow()
        )
        db.add(new_entry)

    db.commit()
    # No refresh needed usually unless we need ID, but db.commit() expires objects.

    # 4. Invalidate Redis Cache
    redis = await get_redis()
    if redis:
        await redis.delete(f"user_profile:{user_id}")

    return TKKVerificationResult(
        success=True,
        score=score,
        message=f"Congratulations! You have been awarded the {new_level.value.title()} level for {metadata['name']}.",
        awarded_level=new_level,
        previous_level=previous_level
    )

def get_user_tkks(db: Session, user_id: int) -> List[TKKBase]:
    stmt = select(UserTKK).where(UserTKK.user_id == user_id)
    user_tkks = db.execute(stmt).scalars().all()

    results = []
    for ut in user_tkks:
        metadata = get_tkk_metadata(ut.tkk_slug)
        if metadata:
            results.append(TKKBase(
                slug=ut.tkk_slug,
                name=metadata.get("name", "Unknown"),
                description=metadata.get("description", ""),
                level=ut.level,
                attained_at=ut.attained_at,
                image_url=metadata.get("image_url")
            ))
    
    return results
