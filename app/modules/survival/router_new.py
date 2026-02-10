"""
Survival Module Router - Offline-Friendly Configuration API

This module provides a simplified API for Survival Tools.
Since Survival is now 100% offline (sensors-based), the backend 
only serves static configuration if needed. No gamification endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter()


class SurvivalToolConfig:
    """Configuration for available survival tools"""
    TOOLS = {
        "compass": {
            "name": "🧭 Kompas",
            "description": "Kompas magnetik real-time. Gunakan di lapangan untuk navigasi.",
            "available": True,
        },
        "clinometer": {
            "name": "📐 Klinometer",
            "description": "Alat ukur sudut dan tinggi. Gunakan untuk mengukur ketinggian pohon atau bangunan.",
            "available": True,
        },
        "gps": {
            "name": "📍 GPS Tracker",
            "description": "Pelacak GPS offline. Menampilkan lintang, bujur, ketinggian, dan akurasi.",
            "available": True,
        },
    }


@router.get("/tools/config")
async def get_tools_config(
    current_user: dict = Depends(get_current_user),
):
    """
    Get configuration for all available survival tools.
    
    This is a static endpoint used by the frontend to initialize
    the tool dashboard. No database queries needed.
    """
    return {
        "tools": SurvivalToolConfig.TOOLS,
        "message": "All survival tools are 100% offline. No internet required!",
    }


@router.get("/health")
async def health_check():
    """Simple health check endpoint for survival module"""
    return {
        "status": "ok",
        "module": "survival",
        "note": "All tools are offline. Backend is optional.",
    }
