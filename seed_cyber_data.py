#!/usr/bin/env python3
"""
CyberScout Data Seeding Script

Loads cyber challenges from app/data/cyber_challenges.json into database.
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.modules.cyber.models import CyberChallenge, CyberCategory, CyberModule


MODULES_PATH = Path("app/data/cyber_modules.json")
CHALLENGES_DIR = Path("app/data/cyber")


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_challenges(session: AsyncSession):
    if not CHALLENGES_DIR.exists():
        return

    json_files = list(CHALLENGES_DIR.glob("*.json"))
    for path in json_files:
        with open(path, "r", encoding="utf-8") as file:
            content = json.load(file)

        questions = []
        module_id = path.stem

        if isinstance(content, dict):
            module_id = content.get("module_id", module_id)
            questions = content.get("questions", [])
        elif isinstance(content, list):
            questions = content

        for item in questions:
            challenge_id = item["id"]
            result = await session.execute(
                select(CyberChallenge).where(CyberChallenge.id == challenge_id)
            )
            existing = result.scalar_one_or_none()

            payload = {
                "id": challenge_id,
                "module_id": module_id,
                "level": item.get("level", 1),
                "category": CyberCategory(item["category"]),
                "difficulty": item.get("difficulty", 1),
                "encrypted_data": item.get("encrypted_data", {}),
                "decrypted_answer": item.get("decrypted_answer", ""),
                "xp_reward": item.get("xp_reward", 5)
            }

            if existing:
                existing.module_id = payload["module_id"]
                existing.level = payload["level"]
                existing.category = payload["category"]
                existing.difficulty = payload["difficulty"]
                existing.encrypted_data = payload["encrypted_data"]
                existing.decrypted_answer = payload["decrypted_answer"]
                existing.xp_reward = payload["xp_reward"]
            else:
                session.add(CyberChallenge(**payload))

    await session.commit()


async def seed_modules(session: AsyncSession):
    with open(MODULES_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    for item in data:
        module_id = item["id"]
        result = await session.execute(
            select(CyberModule).where(CyberModule.id == module_id)
        )
        existing = result.scalar_one_or_none()

        payload = {
            "id": module_id,
            "title": item["title"],
            "original_title": item["original_title"],
            "difficulty": item.get("difficulty", 1),
            "min_read_seconds": item.get("min_read_seconds", 20),
            "intel_content": item.get("intel_content", {})
        }

        if existing:
            existing.title = payload["title"]
            existing.original_title = payload["original_title"]
            existing.difficulty = payload["difficulty"]
            existing.min_read_seconds = payload["min_read_seconds"]
            existing.intel_content = payload["intel_content"]
        else:
            session.add(CyberModule(**payload))

    await session.commit()


async def main():
    await create_tables()
    async with SessionLocal() as session:
        await seed_modules(session)
        await seed_challenges(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
