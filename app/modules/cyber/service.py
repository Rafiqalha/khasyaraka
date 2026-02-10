"""
Cyber Module Service

Business logic layer for CyberScout.
"""

from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from typing import Optional
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.cyber.repository import CyberRepository
from app.modules.cyber.models import CyberCategory, CyberChallenge, SandiType, SandiQuestion
from app.modules.cyber.cipher_service import CipherFactory
from app.modules.cyber.schemas import (
    CyberSubmitResponse, CyberToolRequest, CyberToolResponse,
    SandiExamResponse, SandiQuestionResponse
)
from app.modules.users.models import User


class CyberService:
    """Service layer for CyberScout operations"""

    def __init__(self, db: AsyncSession):
        if db is None:
            raise ValueError("Database session is required")
        self.db = db
        self.repository = CyberRepository(db)

    async def get_dashboard_stats(self, user_id: Optional[int] = None) -> dict:
        """
        Get cyber dashboard stats for a user.
        NOTE: Placeholder until user progress table is implemented.
        """
        if not user_id:
            return {
                "hack_level": "Script Kiddie",
                "decrypted_messages": 0
            }

        user = await self._get_user(user_id)
        if not user:
            return {
                "hack_level": "Script Kiddie",
                "decrypted_messages": 0
            }

        hack_level = user.hack_level or "Script Kiddie"
        decrypted_messages = user.decrypted_count or 0
        return {
            "hack_level": hack_level,
            "decrypted_messages": decrypted_messages
        }

    async def get_random_challenge(self, category: CyberCategory) -> CyberChallenge:
        challenge = await self.repository.get_random_challenge(category)
        if not challenge:
            return None
        return challenge

    async def get_random_challenge_by_module(self, module_id: str) -> CyberChallenge:
        challenge = await self.repository.get_random_challenge_by_module(module_id)
        if not challenge:
            return None
        return challenge

    async def get_modules(self) -> list:
        return await self.repository.get_all_modules()

    async def get_module(self, module_id: str):
        return await self.repository.get_module_by_id(module_id)

    async def get_level_questions(self, module_id: str, level: int) -> list[CyberChallenge]:
        return await self.repository.get_challenges_by_module_level(module_id, level)

    async def get_levels_status(self, user_id: int, module_id: str) -> list[dict]:
        levels = []
        for level_num in range(1, 6):
            progress = await self.repository.get_level_progress(user_id, module_id, level_num)
            stars = progress.stars if progress else 0
            score = progress.score if progress else 0
            is_completed = progress.is_completed if progress else False
            if level_num == 1:
                is_locked = False
            else:
                prev = await self.repository.get_level_progress(user_id, module_id, level_num - 1)
                is_locked = not (prev and prev.is_completed)
            levels.append({
                "level": level_num,
                "stars": stars,
                "score": score,
                "is_completed": is_completed,
                "is_locked": is_locked
            })
        return levels

    async def submit_answer(
        self,
        user_id: int,
        module_id: str,
        level: int,
        correct_answers: int,
        total_questions: int,
        score: int
    ) -> CyberSubmitResponse:
        user = await self._get_user(user_id)
        if not user:
            raise ValueError("User not found")

        if total_questions <= 0:
            raise ValueError("Invalid total questions")

        if correct_answers == total_questions:
            stars = 3
        elif correct_answers > 8:
            stars = 2
        elif correct_answers > 6:
            stars = 1
        else:
            stars = 0

        is_completed = stars > 0
        progress = await self.repository.get_level_progress(user_id, module_id, level)
        already_completed = progress.is_completed if progress else False

        challenges = await self.repository.get_challenges_by_module_level(module_id, level)
        total_xp_pool = sum([c.xp_reward for c in challenges])
        xp_gained = int((total_xp_pool * correct_answers) / total_questions) if not already_completed else 0

        previous_level = user.hack_level or "Script Kiddie"
        user.total_xp = (user.total_xp or 0) + xp_gained
        if is_completed and not already_completed:
            user.decrypted_count = (user.decrypted_count or 0) + 1

        await self.repository.upsert_level_progress(
            user_id=user_id,
            module_id=module_id,
            level=level,
            stars=stars,
            score=score,
            is_completed=is_completed
        )

        unlocked_next = False
        if is_completed and level < 5:
            await self.repository.upsert_level_progress(
                user_id=user_id,
                module_id=module_id,
                level=level + 1,
                stars=0,
                score=0,
                is_completed=False
            )
            unlocked_next = True

        new_level = self._calculate_hack_level(user.total_xp or 0)
        user.hack_level = new_level
        level_up = previous_level != new_level

        await self.db.commit()

        return CyberSubmitResponse(
            success=is_completed,
            xp_gained=xp_gained,
            new_total_xp=user.total_xp or 0,
            level_up=level_up,
            message="ACCESS GRANTED" if is_completed else "SECURITY BREACH",
            stars=stars,
            unlocked_next_level=unlocked_next
        )

    async def _get_user(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _calculate_hack_level(self, total_xp: int) -> str:
        thresholds: Tuple[Tuple[int, str], ...] = (
            (0, "Script Kiddie"),
            (100, "White Hat"),
            (250, "Cyber Ranger"),
            (500, "Ghost Operator"),
            (1000, "Phantom Chief"),
        )
        current = "Script Kiddie"
        for xp, level in thresholds:
            if total_xp >= xp:
                current = level
        return current

    # ============ SANDI PRAMUKA METHODS ============

    async def get_all_sandi_types(self) -> list[SandiType]:
        """Get all Sandi types"""
        return await self.repository.get_all_sandi_types()

    async def process_cipher_tool(
        self,
        user_id: int,
        request: CyberToolRequest
    ) -> CyberToolResponse:
        """
        Process encryption/decryption using cipher tool.
        
        Args:
            user_id: User ID for logging
            request: CyberToolRequest with text, operation_mode, sandi_codename
            
        Returns:
            CyberToolResponse with result
        """
        # Get Sandi type by codename
        sandi_type = await self.repository.get_sandi_by_codename(request.sandi_codename)
        if not sandi_type:
            raise ValueError(f"Sandi type '{request.sandi_codename}' not found")
        
        # Create cipher instance using factory
        cipher = CipherFactory.create_cipher(sandi_type)
        
        # Process text based on operation mode
        if request.operation_mode.value == "ENCRYPT":
            result_text = cipher.encrypt(request.text)
        else:  # DECRYPT
            result_text = cipher.decrypt(request.text)
        
        # Create hash of input for audit log
        input_hash = hashlib.sha256(request.text.encode('utf-8')).hexdigest()
        
        # Log encryption activity
        await self.repository.create_encryption_log(
            user_id=user_id,
            sandi_id=sandi_type.id,
            input_hash=input_hash,
            operation_mode=request.operation_mode.value
        )
        
        await self.db.commit()
        
        return CyberToolResponse(
            result=result_text,
            sandi_codename=request.sandi_codename,
            operation_mode=request.operation_mode.value
        )

    async def get_sandi_exam(self, sandi_id: int, limit: int = 5) -> SandiExamResponse:
        """
        Get random exam questions for a Sandi type.
        
        Args:
            sandi_id: Sandi Type ID
            limit: Number of questions to return
            
        Returns:
            SandiExamResponse with questions
        """
        sandi_type = await self.repository.get_sandi_by_id(sandi_id)
        if not sandi_type:
            raise ValueError(f"Sandi type with ID {sandi_id} not found")
        
        questions = await self.repository.get_random_sandi_questions(sandi_id, limit)
        
        question_responses = [
            SandiQuestionResponse(
                id=q.id,
                sandi_id=q.sandi_id,
                question_text=q.question_text,
                encrypted_text=q.encrypted_text,
                hint=q.hint,
                difficulty=q.difficulty,
                xp_reward=q.xp_reward
            )
            for q in questions
        ]
        
        return SandiExamResponse(
            sandi_id=sandi_id,
            sandi_name=sandi_type.name,
            total=len(question_responses),
            questions=question_responses
        )