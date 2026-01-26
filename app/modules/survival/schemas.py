from pydantic import BaseModel, Field
from typing import List
from enum import Enum


class ToolType(str, Enum):
    """Survival tool types"""
    compass = "compass"
    clinometer = "clinometer"
    pedometer = "pedometer"
    morse = "morse"
    leveler = "leveler"
    gps_tracker = "gps_tracker"


class MasteryStatsResponse(BaseModel):
    """Stats for a single tool"""
    tool_type: ToolType
    current_xp: int
    current_level: int
    total_actions: int
    highest_streak: int
    max_altitude: float
    total_distance_tracked: float
    xp_to_next_level: int
    rank_title: str


class AllMasteryResponse(BaseModel):
    """All mastery stats for a user"""
    tools: List[MasteryStatsResponse]


class RecordActionRequest(BaseModel):
    """Request to record a survival tool action"""
    tool_type: ToolType
    xp_gained: int = Field(default=10, ge=0, le=1000)
    action_metadata: dict = Field(default_factory=dict)


class RecordActionResponse(BaseModel):
    """Response after recording an action"""
    success: bool
    tool_type: ToolType
    new_xp: int
    new_level: int
    is_level_up: bool
    xp_gained: int
    rank_title: str
