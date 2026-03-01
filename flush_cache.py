import asyncio
from app.core.redis import get_redis

async def main():
    print("Connecting to Redis...")
    redis = await get_redis()
    
    # Get all training path keys
    keys1 = await redis.keys("training:path:*")
    keys2 = await redis.keys("training:sections")
    
    all_keys = keys1 + keys2
    
    if all_keys:
        print(f"Deleting {len(all_keys)} keys...")
        await redis.delete(*all_keys)
        print("Success.")
    else:
        print("No keys found.")
    
    await redis.close()

if __name__ == "__main__":
    asyncio.run(main())
