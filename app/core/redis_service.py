import json
from typing import Optional, Dict, Any, List
from app.core.redis import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

class RedisService:
    """
    Service for Redis operations using Hash structures and Lua scripts.
    Implements atomic counters and data management.
    """
    
    @staticmethod
    def _user_key(user_id: str) -> str:
        return f"user:{user_id}"

    @classmethod
    async def get_user_data(cls, user_id: str, fields: List[str] = None) -> Dict[str, Any]:
        """
        Get user data from Redis Hash.
        If fields is None, returns all fields.
        """
        redis = await get_redis()
        key = cls._user_key(user_id)
        
        if fields:
            # HMGET returns list of values in order of fields
            values = await redis.hmget(key, fields)
            return {field: val for field, val in zip(fields, values) if val is not None}
        else:
            # HGETALL returns dictionary
            return await redis.hgetall(key)

    @classmethod
    async def set_user_data(cls, user_id: str, data: Dict[str, Any], ttl: int = 604800) -> None:
        """
        Set multiple fields in user Hash.
        """
        redis = await get_redis()
        key = cls._user_key(user_id)
        
        # Convert all values to strings for consistency
        # Redis stores everything as bytes/strings
        formatted_data = {k: str(v) for k, v in data.items()}
        
        if formatted_data:
            await redis.hset(key, mapping=formatted_data)
            await redis.expire(key, ttl)

    @classmethod
    async def atomic_increment(cls, user_id: str, field: str, amount: int, min_val: int = None, max_val: int = None) -> int:
        """
        Atomically increment a field in the user Hash.
        Supports optional min/max clamping via Lua script.
        
        Returns:
            New value of the field
        """
        redis = await get_redis()
        key = cls._user_key(user_id)
        
        if min_val is None and max_val is None:
            # Simple HINCRBY
            return await redis.hincrby(key, field, amount)
        
        # Lua script for clamped increment
        script = """
        local current = redis.call('HGET', KEYS[1], ARGV[1])
        current = tonumber(current) or 0
        local change = tonumber(ARGV[2])
        local new_val = current + change
        
        -- Check Min/Max constraints (empty string = no constraint)
        if ARGV[3] ~= "" and new_val < tonumber(ARGV[3]) then
            new_val = tonumber(ARGV[3])
        end
        if ARGV[4] ~= "" and new_val > tonumber(ARGV[4]) then
            new_val = tonumber(ARGV[4])
        end
        
        redis.call('HSET', KEYS[1], ARGV[1], new_val)
        return new_val
        """
        
        # ARGV: [field, amount, min_val, max_val]
        # Use empty string as sentinel (Redis can't handle Python bool)
        args = [field, amount]
        args.append(min_val if min_val is not None else "")
        args.append(max_val if max_val is not None else "")
        
        return await redis.eval(script, 1, key, *args)

    @classmethod
    async def atomic_decrement_hearts(cls, user_id: str) -> int:
        """
        Specialized atomic decrement for hearts.
        Cannot go below 0.
        """
        return await cls.atomic_increment(user_id, 'hearts', -1, min_val=0)

    @classmethod
    async def atomic_add_heart(cls, user_id: str) -> int:
        """
        Specialized atomic increment for hearts.
        Cannot go above 5.
        """
        return await cls.atomic_increment(user_id, 'hearts', 1, max_val=5)
