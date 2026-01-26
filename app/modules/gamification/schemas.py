"""
Leaderboard Schemas

Pydantic schemas for leaderboard API responses.
"""

from pydantic import BaseModel
from typing import List, Optional


class LeaderboardUser(BaseModel):
    """Single user entry in leaderboard"""
    rank: int
    id: str
    name: str
    xp: int
    avatar: Optional[str] = None


class MyRank(BaseModel):
    """Current user's rank information"""
    rank: int
    xp: int


class LeaderboardResponse(BaseModel):
    """Leaderboard API response"""
    top_users: List[LeaderboardUser]
    my_rank: Optional[MyRank] = None
