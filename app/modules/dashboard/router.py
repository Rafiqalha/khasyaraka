from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_dashboard():
    """
    Aggregated dashboard data
    """
    return {
        "user": {
            "level": 3,
            "xp": 240,
            "streak": 5,
        },
        "modes": {
            "training": {"status": "active"},
            "hiking": {"status": "locked"},
            "cyber": {"status": "locked"},
        },
    }
