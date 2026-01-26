import math
import logging
from typing import List

from app.modules.survival.repository import SurvivalRepository
from app.modules.survival.models import ToolTypeEnum
from app.modules.survival.schemas import (
    MasteryStatsResponse,
    AllMasteryResponse,
    RecordActionResponse,
    ToolType
)

logger = logging.getLogger(__name__)


class SurvivalService:
    """Business logic for survival mastery system"""
    
    # Rank titles based on level ranges
    RANK_TITLES = {
        "compass": [
            (1, "Novice Navigator"),
            (5, "Scout Navigator"),
            (10, "Expert Navigator"),
            (20, "Master Navigator"),
            (50, "Legendary Pathfinder"),
        ],
        "clinometer": [
            (1, "Height Learner"),
            (5, "Angle Reader"),
            (10, "Elevation Expert"),
            (20, "Peak Master"),
            (50, "Mountain Sage"),
        ],
        "pedometer": [
            (1, "Walker"),
            (5, "Hiker"),
            (10, "Trekker"),
            (20, "Trail Master"),
            (50, "Endless Wanderer"),
        ],
        "morse": [
            (1, "Signal Trainee"),
            (5, "Morse Operator"),
            (10, "Telegraph Expert"),
            (20, "Signal Master"),
            (50, "Code Whisperer"),
        ],
        "leveler": [
            (1, "Balance Seeker"),
            (5, "Level Reader"),
            (10, "Precision Expert"),
            (20, "Balance Master"),
            (50, "Equilibrium Sage"),
        ],
        "gps_tracker": [
            (1, "Location Scout"),
            (5, "Pathfinder"),
            (10, "Coordinate Master"),
            (20, "Geo Expert"),
            (50, "World Mapper"),
        ],
    }
    
    def __init__(self, repository: SurvivalRepository):
        self.repository = repository
    
    @staticmethod
    def calculate_level(xp: int) -> int:
        """
        Calculate level from XP using infinite scaling formula.
        Level = floor(sqrt(xp / 100)) + 1
        
        Examples:
        - 0 XP = Level 1
        - 100 XP = Level 2
        - 400 XP = Level 3
        - 900 XP = Level 4
        - 10000 XP = Level 11
        """
        if xp < 0:
            return 1
        return math.floor(math.sqrt(xp / 100)) + 1
    
    @staticmethod
    def xp_for_level(level: int) -> int:
        """Calculate XP required to reach a specific level"""
        if level <= 1:
            return 0
        return ((level - 1) ** 2) * 100
    
    @staticmethod
    def xp_to_next_level(current_xp: int, current_level: int) -> int:
        """Calculate XP needed for next level"""
        next_level_xp = SurvivalService.xp_for_level(current_level + 1)
        return next_level_xp - current_xp
    
    @staticmethod
    def get_rank_title(tool_type: str, level: int) -> str:
        """Get rank title based on tool type and level"""
        ranks = SurvivalService.RANK_TITLES.get(tool_type, [])
        title = "Survivor"
        
        for min_level, rank_name in ranks:
            if level >= min_level:
                title = rank_name
            else:
                break
        
        return title
    
    async def get_all_mastery(self, user_id: int) -> AllMasteryResponse:
        """Get all mastery stats for a user"""
        masteries = await self.repository.get_all_user_masteries(user_id)
        
        # Ensure all tools have records (create if missing)
        existing_tools = {m.tool_type for m in masteries}
        for tool_type in ToolTypeEnum:
            if tool_type not in existing_tools:
                new_mastery = await self.repository.create_mastery(user_id, tool_type)
                masteries.append(new_mastery)
        
        # Convert to response format
        stats = []
        for mastery in masteries:
            tool_str = mastery.tool_type.value
            stats.append(
                MasteryStatsResponse(
                    tool_type=tool_str,
                    current_xp=mastery.current_xp,
                    current_level=mastery.current_level,
                    total_actions=mastery.total_actions,
                    highest_streak=mastery.highest_streak,
                    max_altitude=mastery.max_altitude,
                    total_distance_tracked=mastery.total_distance_tracked,
                    xp_to_next_level=self.xp_to_next_level(
                        mastery.current_xp, 
                        mastery.current_level
                    ),
                    rank_title=self.get_rank_title(tool_str, mastery.current_level)
                )
            )
        
        return AllMasteryResponse(tools=stats)
    
    async def record_action(
        self, 
        user_id: int, 
        tool_type: ToolType, 
        xp_gained: int,
        metadata: dict | None = None
    ) -> RecordActionResponse:
        """
        Record a survival tool action and update mastery.
        
        Returns information about XP gained and whether user leveled up.
        """
        # Convert ToolType to ToolTypeEnum
        tool_enum = ToolTypeEnum[tool_type.value]
        
        # Get or create mastery record
        mastery = await self.repository.get_or_create_mastery(user_id, tool_enum)
        
        # Store old level
        old_level = mastery.current_level
        
        # Calculate XP (special rules for GPS tracker)
        xp_to_add = xp_gained
        distance_delta = 0.0
        max_altitude = None

        if tool_type.value == "gps_tracker" and metadata:
            distance_meters = float(metadata.get("distance_meters", 0.0))
            altitude_gain = float(metadata.get("altitude_gain_meters", 0.0))
            max_altitude = metadata.get("max_altitude")
            if max_altitude is not None:
                max_altitude = float(max_altitude)

            # XP Calculation:
            # 100 meters walked = 10 XP
            # 10 meters climbed = 50 XP
            xp_from_distance = (distance_meters / 100.0) * 10.0
            xp_from_altitude = (altitude_gain / 10.0) * 50.0
            xp_to_add = int(xp_from_distance + xp_from_altitude)
            distance_delta = max(distance_meters, 0.0)

        # Calculate new XP and level
        new_xp = mastery.current_xp + xp_to_add
        new_level = self.calculate_level(new_xp)
        
        # Update mastery
        updated_mastery = await self.repository.update_mastery(
            mastery=mastery,
            xp_delta=xp_to_add,
            new_level=new_level,
            action_count=1,
            max_altitude=max_altitude,
            distance_delta=distance_delta
        )
        
        # Check if level up occurred
        is_level_up = new_level > old_level
        
        if is_level_up:
            logger.info(
                f"User {user_id} leveled up {tool_type.value}: "
                f"Level {old_level} -> {new_level}"
            )
        
        # Get rank title
        rank_title = self.get_rank_title(tool_type.value, new_level)
        
        return RecordActionResponse(
            success=True,
            tool_type=tool_type,
            new_xp=updated_mastery.current_xp,
            new_level=updated_mastery.current_level,
            is_level_up=is_level_up,
            xp_gained=xp_to_add,
            rank_title=rank_title
        )
