"""
Cyber Module Router

API endpoints for CyberScout challenges.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.cyber.models import CyberCategory, CyberChallenge, CyberModule
from app.modules.cyber.service import CyberService
from app.modules.cyber.schemas import (
    CyberDashboardResponse,
    CyberChallengeResponse,
    CyberSubmitRequest,
    CyberSubmitResponse,
    CyberModuleListResponse,
    CyberModuleResponse,
    CyberLevelsResponse,
    CyberLevelQuestionsResponse,
    SandiListResponse,
    SandiResponse,
    CyberToolRequest,
    CyberToolResponse,
    SandiExamResponse
)

router = APIRouter(prefix="/cyber", tags=["Cyber"])


def get_service(db: AsyncSession = Depends(get_db)) -> CyberService:
    return CyberService(db=db)


def parse_category(category: str) -> CyberCategory:
    try:
        return CyberCategory(category)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'"
        ) from exc


@router.get(
    "/modules",
    response_model=CyberModuleListResponse,
    summary="Get all cyber modules"
)
async def get_modules(
    service: CyberService = Depends(get_service)
):
    modules = await service.get_modules()
    return CyberModuleListResponse(total=len(modules), modules=modules)


@router.get(
    "/modules/{module_id}",
    response_model=CyberModuleResponse,
    summary="Get cyber module detail"
)
async def get_module(
    module_id: str,
    service: CyberService = Depends(get_service)
):
    module = await service.get_module(module_id)
    if not module:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
    return module


@router.get(
    "/modules/{module_id}/challenge",
    response_model=CyberChallengeResponse,
    summary="Get random challenge for module"
)
async def get_module_challenge(
    module_id: str,
    service: CyberService = Depends(get_service)
):
    challenge = await service.get_random_challenge_by_module(module_id)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"No challenges for module '{module_id}'")
    return challenge


@router.get(
    "/modules/{module_id}/levels",
    response_model=CyberLevelsResponse,
    summary="Get level status for module"
)
async def get_module_levels(
    module_id: str,
    current_user: dict = Depends(get_current_user),
    service: CyberService = Depends(get_service)
):
    user_id = int(current_user.get("sub")) if current_user.get("sub") else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user session")
    levels = await service.get_levels_status(user_id, module_id)
    return CyberLevelsResponse(module_id=module_id, levels=levels)


@router.get(
    "/modules/{module_id}/levels/{level}/questions",
    response_model=CyberLevelQuestionsResponse,
    summary="Get questions for module level"
)
async def get_level_questions(
    module_id: str,
    level: int,
    service: CyberService = Depends(get_service)
):
    questions = await service.get_level_questions(module_id, level)
    return CyberLevelQuestionsResponse(
        module_id=module_id,
        level=level,
        total=len(questions),
        questions=questions
    )


@router.get(
    "/dashboard",
    response_model=CyberDashboardResponse,
    summary="Get cyber dashboard stats"
)
async def get_dashboard(
    current_user: dict = Depends(get_current_user),
    service: CyberService = Depends(get_service)
):
    user_id = int(current_user.get("sub")) if current_user.get("sub") else None
    stats = await service.get_dashboard_stats(user_id=user_id)
    return CyberDashboardResponse(**stats)


@router.get(
    "/challenges/{category}",
    response_model=CyberChallengeResponse,
    summary="Get a random cyber challenge by category"
)
async def get_challenge(
    category: str,
    service: CyberService = Depends(get_service)
):
    parsed_category = parse_category(category)
    challenge = await service.get_random_challenge(parsed_category)
    if not challenge:
        raise HTTPException(
            status_code=404,
            detail=f"No challenges found for category '{category}'"
        )
    return challenge


@router.post(
    "/submit",
    response_model=CyberSubmitResponse,
    summary="Submit a cyber challenge answer"
)
async def submit_answer(
    payload: CyberSubmitRequest = Body(...),
    current_user: dict = Depends(get_current_user),
    service: CyberService = Depends(get_service)
):
    try:
        user_id = int(current_user.get("sub")) if current_user.get("sub") else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user session")
        return await service.submit_answer(
            user_id=user_id,
            module_id=payload.module_id,
            level=payload.level,
            correct_answers=payload.correct_answers,
            total_questions=payload.total_questions,
            score=payload.score
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/seed",
    summary="Seed database with Cyber Scout modules and challenges (Dev only)"
)
async def seed_cyber_data(
    force: bool = Body(False, embed=True, description="Force reseed even if data exists"),
    db: AsyncSession = Depends(get_db)
):
    """
    Seed the database with 5 cipher modules (Caesar, Morse, Atbash, Binary, Reverse).
    Each module has 5 levels, with Level 1 containing 5 real questions.
    Levels 2-5 are locked placeholders.
    """
    # Check if data already exists
    if not force:
        challenge_count = await db.execute(select(func.count(CyberChallenge.id)))
        if challenge_count.scalar() > 0:
            return {"message": "Database already seeded. Use force=true to reseed."}

    # Define modules
    modules_data = [
        {
            "id": "mod_caesar",
            "title": "Caesar Cipher",
            "original_title": "Sandi Geser",
            "difficulty": 1,
            "min_read_seconds": 20,
            "intel_content": {
                "description": "Pelajari dasar-dasar Caesar Cipher (Sandi Geser).",
                "clue": "Shift by -1"
            }
        },
        {
            "id": "mod_morse",
            "title": "Morse Code",
            "original_title": "Sandi Morse",
            "difficulty": 1,
            "min_read_seconds": 25,
            "intel_content": {
                "description": "Pelajari dasar-dasar Morse Code (Sandi Morse).",
                "clue": "Listen carefully"
            }
        },
        {
            "id": "mod_atbash",
            "title": "Atbash Cipher",
            "original_title": "Sandi Cermin",
            "difficulty": 1,
            "min_read_seconds": 20,
            "intel_content": {
                "description": "Pelajari dasar-dasar Atbash Cipher (A=Z, B=Y...).",
                "clue": "A=Z, B=Y, C=X..."
            }
        },
        {
            "id": "mod_binary",
            "title": "Binary Code",
            "original_title": "Sandi Biner",
            "difficulty": 1,
            "min_read_seconds": 20,
            "intel_content": {
                "description": "Pelajari dasar-dasar Binary Code (Sandi Biner).",
                "clue": "Binary to decimal"
            }
        },
        {
            "id": "mod_reverse",
            "title": "Reverse Cipher",
            "original_title": "Sandi Balik",
            "difficulty": 1,
            "min_read_seconds": 15,
            "intel_content": {
                "description": "Pelajari dasar-dasar Reverse Cipher (Sandi Balik).",
                "clue": "Read backwards"
            }
        }
    ]

    # Insert modules
    for module_data in modules_data:
        existing = await db.execute(
            select(CyberModule).where(CyberModule.id == module_data["id"])
        )
        if existing.scalar_one_or_none():
            continue
        
        module = CyberModule(**module_data)
        db.add(module)
    
    await db.commit()

    # Define challenges (Level 1 only - 5 questions per module)
    challenges_data = [
        # CAESAR CIPHER - Level 1
        {
            "id": "ch_caesar_1_1",
            "module_id": "mod_caesar",
            "level": 1,
            "category": CyberCategory.caesar_cipher,
            "difficulty": 1,
            "encrypted_data": {"cipher": "QSBNVLB", "hint": "Shift -1", "answer": "PRAMUKA"},
            "decrypted_answer": "PRAMUKA",
            "xp_reward": 10
        },
        {
            "id": "ch_caesar_1_2",
            "module_id": "mod_caesar",
            "level": 1,
            "category": CyberCategory.caesar_cipher,
            "difficulty": 1,
            "encrypted_data": {"cipher": "CVEJ", "hint": "Shift -1", "answer": "BUDI"},
            "decrypted_answer": "BUDI",
            "xp_reward": 10
        },
        {
            "id": "ch_caesar_1_3",
            "module_id": "mod_caesar",
            "level": 1,
            "category": CyberCategory.caesar_cipher,
            "difficulty": 1,
            "encrypted_data": {"cipher": "UFOEB", "hint": "Shift -1", "answer": "TENDA"},
            "decrypted_answer": "TENDA",
            "xp_reward": 10
        },
        {
            "id": "ch_caesar_1_4",
            "module_id": "mod_caesar",
            "level": 1,
            "category": CyberCategory.caesar_cipher,
            "difficulty": 1,
            "encrypted_data": {"cipher": "LQNQBT", "hint": "Shift -1", "answer": "KOMPAS"},
            "decrypted_answer": "KOMPAS",
            "xp_reward": 10
        },
        {
            "id": "ch_caesar_1_5",
            "module_id": "mod_caesar",
            "level": 1,
            "category": CyberCategory.caesar_cipher,
            "difficulty": 1,
            "encrypted_data": {"cipher": "BMBN", "hint": "Shift -1", "answer": "ALAM"},
            "decrypted_answer": "ALAM",
            "xp_reward": 10
        },
        # MORSE CODE - Level 1
        {
            "id": "ch_morse_1_1",
            "module_id": "mod_morse",
            "level": 1,
            "category": CyberCategory.morse,
            "difficulty": 1,
            "encrypted_data": {"cipher": "...", "hasAudio": True, "answer": "S"},
            "decrypted_answer": "S",
            "xp_reward": 15
        },
        {
            "id": "ch_morse_1_2",
            "module_id": "mod_morse",
            "level": 1,
            "category": CyberCategory.morse,
            "difficulty": 1,
            "encrypted_data": {"cipher": "---", "hasAudio": True, "answer": "O"},
            "decrypted_answer": "O",
            "xp_reward": 15
        },
        {
            "id": "ch_morse_1_3",
            "module_id": "mod_morse",
            "level": 1,
            "category": CyberCategory.morse,
            "difficulty": 1,
            "encrypted_data": {"cipher": ".-", "hasAudio": True, "answer": "A"},
            "decrypted_answer": "A",
            "xp_reward": 15
        },
        {
            "id": "ch_morse_1_4",
            "module_id": "mod_morse",
            "level": 1,
            "category": CyberCategory.morse,
            "difficulty": 1,
            "encrypted_data": {"cipher": "-...", "hasAudio": True, "answer": "B"},
            "decrypted_answer": "B",
            "xp_reward": 15
        },
        {
            "id": "ch_morse_1_5",
            "module_id": "mod_morse",
            "level": 1,
            "category": CyberCategory.morse,
            "difficulty": 1,
            "encrypted_data": {"cipher": ".--", "hasAudio": True, "answer": "W"},
            "decrypted_answer": "W",
            "xp_reward": 15
        },
        # ATBASH CIPHER - Level 1
        {
            "id": "ch_atbash_1_1",
            "module_id": "mod_atbash",
            "level": 1,
            "category": CyberCategory.atbash,
            "difficulty": 1,
            "encrypted_data": {"cipher": "ZYX", "hint": "A=Z, B=Y, C=X...", "answer": "ABC"},
            "decrypted_answer": "ABC",
            "xp_reward": 12
        },
        {
            "id": "ch_atbash_1_2",
            "module_id": "mod_atbash",
            "level": 1,
            "category": CyberCategory.atbash,
            "difficulty": 1,
            "encrypted_data": {"cipher": "KIZNFPZ", "hint": "A=Z, B=Y...", "answer": "PRAMUKA"},
            "decrypted_answer": "PRAMUKA",
            "xp_reward": 12
        },
        {
            "id": "ch_atbash_1_3",
            "module_id": "mod_atbash",
            "level": 1,
            "category": CyberCategory.atbash,
            "difficulty": 1,
            "encrypted_data": {"cipher": "TzIFWz", "hint": "A=Z, B=Y...", "answer": "GARUDA"},
            "decrypted_answer": "GARUDA",
            "xp_reward": 12
        },
        {
            "id": "ch_atbash_1_4",
            "module_id": "mod_atbash",
            "level": 1,
            "category": CyberCategory.atbash,
            "difficulty": 1,
            "encrypted_data": {"cipher": "WzHR", "hint": "A=Z, B=Y...", "answer": "DASI"},
            "decrypted_answer": "DASI",
            "xp_reward": 12
        },
        {
            "id": "ch_atbash_1_5",
            "module_id": "mod_atbash",
            "level": 1,
            "category": CyberCategory.atbash,
            "difficulty": 1,
            "encrypted_data": {"cipher": "YFPF", "hint": "A=Z, B=Y...", "answer": "BUKU"},
            "decrypted_answer": "BUKU",
            "xp_reward": 12
        },
        # BINARY CODE - Level 1
        {
            "id": "ch_binary_1_1",
            "module_id": "mod_binary",
            "level": 1,
            "category": CyberCategory.binary,
            "difficulty": 1,
            "encrypted_data": {"cipher": "0001", "hint": "Binary to decimal", "answer": "1"},
            "decrypted_answer": "1",
            "xp_reward": 12
        },
        {
            "id": "ch_binary_1_2",
            "module_id": "mod_binary",
            "level": 1,
            "category": CyberCategory.binary,
            "difficulty": 1,
            "encrypted_data": {"cipher": "0010", "hint": "Binary to decimal", "answer": "2"},
            "decrypted_answer": "2",
            "xp_reward": 12
        },
        {
            "id": "ch_binary_1_3",
            "module_id": "mod_binary",
            "level": 1,
            "category": CyberCategory.binary,
            "difficulty": 1,
            "encrypted_data": {"cipher": "0101", "hint": "Binary to decimal", "answer": "5"},
            "decrypted_answer": "5",
            "xp_reward": 12
        },
        {
            "id": "ch_binary_1_4",
            "module_id": "mod_binary",
            "level": 1,
            "category": CyberCategory.binary,
            "difficulty": 1,
            "encrypted_data": {"cipher": "0011", "hint": "Binary to decimal", "answer": "3"},
            "decrypted_answer": "3",
            "xp_reward": 12
        },
        {
            "id": "ch_binary_1_5",
            "module_id": "mod_binary",
            "level": 1,
            "category": CyberCategory.binary,
            "difficulty": 1,
            "encrypted_data": {"cipher": "1001", "hint": "Binary to decimal", "answer": "9"},
            "decrypted_answer": "9",
            "xp_reward": 12
        },
        # REVERSE CIPHER - Level 1
        {
            "id": "ch_reverse_1_1",
            "module_id": "mod_reverse",
            "level": 1,
            "category": CyberCategory.reverse,
            "difficulty": 1,
            "encrypted_data": {"cipher": "AKUMARP", "hint": "Balik kata", "answer": "PRAMUKA"},
            "decrypted_answer": "PRAMUKA",
            "xp_reward": 12
        },
        {
            "id": "ch_reverse_1_2",
            "module_id": "mod_reverse",
            "level": 1,
            "category": CyberCategory.reverse,
            "difficulty": 1,
            "encrypted_data": {"cipher": "ISAD", "hint": "Balik kata", "answer": "DASI"},
            "decrypted_answer": "DASI",
            "xp_reward": 12
        },
        {
            "id": "ch_reverse_1_3",
            "module_id": "mod_reverse",
            "level": 1,
            "category": CyberCategory.reverse,
            "difficulty": 1,
            "encrypted_data": {"cipher": "NATUH", "hint": "Balik kata", "answer": "HUTAN"},
            "decrypted_answer": "HUTAN",
            "xp_reward": 12
        },
        {
            "id": "ch_reverse_1_4",
            "module_id": "mod_reverse",
            "level": 1,
            "category": CyberCategory.reverse,
            "difficulty": 1,
            "encrypted_data": {"cipher": "ADNET", "hint": "Balik kata", "answer": "TENDA"},
            "decrypted_answer": "TENDA",
            "xp_reward": 12
        },
        {
            "id": "ch_reverse_1_5",
            "module_id": "mod_reverse",
            "level": 1,
            "category": CyberCategory.reverse,
            "difficulty": 1,
            "encrypted_data": {"cipher": "GNALAGNEP", "hint": "Balik kata", "answer": "PENGGALANG"},
            "decrypted_answer": "PENGGALANG",
            "xp_reward": 12
        }
    ]

    # Insert challenges
    for challenge_data in challenges_data:
        existing = await db.execute(
            select(CyberChallenge).where(CyberChallenge.id == challenge_data["id"])
        )
        if existing.scalar_one_or_none():
            continue
        
        challenge = CyberChallenge(**challenge_data)
        db.add(challenge)
    
    await db.commit()

    return {
        "message": "Database seeded successfully",
        "modules_created": len(modules_data),
        "challenges_created": len(challenges_data),
        "total_levels": 25  # 5 modules × 5 levels
    }


# ============ SANDI PRAMUKA ENDPOINTS ============

@router.get(
    "/list",
    response_model=SandiListResponse,
    summary="Get all Sandi Pramuka types",
    description="Returns list of all 15 Sandi Pramuka cipher types"
)
async def get_sandi_list(
    service: CyberService = Depends(get_service)
):
    """Get all Sandi types"""
    sandi_types = await service.get_all_sandi_types()
    return SandiListResponse(
        total=len(sandi_types),
        sandi_types=[SandiResponse.model_validate(st) for st in sandi_types]
    )


@router.post(
    "/tool/process",
    response_model=CyberToolResponse,
    summary="Process encryption/decryption",
    description="Encrypt or decrypt text using a Sandi cipher (Tool Mode)"
)
async def process_cipher_tool(
    request: CyberToolRequest,
    current_user: User = Depends(get_current_user),
    service: CyberService = Depends(get_service)
):
    """
    Process text encryption/decryption using cipher tool.
    Records activity in EncryptionLog for audit trail.
    """
    try:
        result = await service.process_cipher_tool(
            user_id=current_user.id,
            request=request
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@router.get(
    "/exam/{sandi_id}",
    response_model=SandiExamResponse,
    summary="Get Sandi exam questions",
    description="Returns random exam questions for a specific Sandi type"
)
async def get_sandi_exam(
    sandi_id: int,
    limit: int = 5,
    service: CyberService = Depends(get_service)
):
    """
    Get random exam questions for a Sandi type.
    
    Args:
        sandi_id: Sandi Type ID
        limit: Number of questions (default: 5, max: 20)
    """
    if limit > 20:
        limit = 20
    if limit < 1:
        limit = 5
    
    try:
        result = await service.get_sandi_exam(sandi_id=sandi_id, limit=limit)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching exam: {str(e)}")
