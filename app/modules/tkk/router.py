from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.security import get_current_user
from app.modules.tkk.schemas import TKKSubmission, TKKVerificationResult, TKKBase
from app.modules.tkk.service import process_tkk_submission, get_user_tkks

router = APIRouter(
    prefix="/tkk",
    tags=["Tanda Kecakapan Khusus (TKK)"]
)

@router.post("/verify", response_model=TKKVerificationResult)
async def verify_tkk_submission(
    submission: TKKSubmission,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit answers for a TKK assessment.
    If score >= 80, the user is awarded the next level (Purwa -> Madya -> Utama).
    """
    user_id = int(current_user.get("sub"))
    return await process_tkk_submission(
        db=db,
        user_id=user_id,
        slug=submission.tkk_slug,
        answers=submission.answers
    )

@router.get("/mine", response_model=List[TKKBase])
def read_my_tkks(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all TKKs attained by the current user.
    """
    user_id = int(current_user.get("sub"))
    return get_user_tkks(db=db, user_id=user_id)
