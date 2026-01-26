#!/usr/bin/env python3
"""
SKU Twin Pillars Seed Script
"""
import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.modules.sku.models import SkuPoint, SkuLevel

DATA_PATH = Path("app/data/sku/bantara_official.json")


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_points(session: AsyncSession):
    if not DATA_PATH.exists():
        return

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    level = SkuLevel(payload.get("pillar_id", "bantara"))
    points = payload.get("points", [])

    for point in points:
        point_id = f"{level.value}_{point['number']:02d}"
        quiz_items = point.get("quiz", [])
        questions = []
        for item in quiz_items:
            options = item.get("options", [])
            answer_text = item.get("a")
            correct_index = options.index(answer_text) if answer_text in options else 0
            questions.append({
                "question": item.get("q", ""),
                "options": options,
                "correct_index": correct_index
            })

        quiz_content = {
            "briefing": point.get("briefing", ""),
            "official_ref": point.get("official_ref", ""),
            "questions": questions
        }
        stmt = select(SkuPoint).where(SkuPoint.id == point_id)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.level = level
            existing.number = point["number"]
            existing.title = point["title"]
            existing.description = point.get("briefing", "")
            existing.category = point["category"]
            existing.quiz_content = quiz_content
            continue

        session.add(
            SkuPoint(
                id=point_id,
                level=level,
                number=point["number"],
                title=point["title"],
                description=point.get("briefing", ""),
                category=point["category"],
                quiz_content=quiz_content
            )
        )

    await session.commit()


async def main():
    await create_tables()
    async with SessionLocal() as session:
        await seed_points(session)


if __name__ == "__main__":
    asyncio.run(main())
