#!/usr/bin/env python3
"""
Full Question Seeding Script for Bagian 1-5

Seeds all questions from app/data/question/{section}/unit_{n}.json files
into the PostgreSQL database.

Features:
- Idempotent: skips existing questions (safe to re-run)
- Reads from existing JSON data files (real scouting content)
- Validates foreign keys (checks level_id exists before inserting)
- Detailed logging of seeded/skipped counts per level

Usage:
    cd scout_os_backend
    python seed_all_questions.py

Verification:
    SELECT count(*) FROM training_questions;
    SELECT level_id, count(*) FROM training_questions GROUP BY level_id ORDER BY level_id;

Author: Antigravity AI Assistant
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.modules.training.models import (
    TrainingSection,
    TrainingUnit,
    TrainingLevel,
    TrainingQuestion
)
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


# =============================
# CONFIGURATION
# =============================

SECTIONS = ["puk", "ppgd", "nav", "tali", "sandi"]
UNITS_PER_SECTION = 5
DATA_DIR = Path(__file__).parent / "app" / "data" / "question"


# =============================
# HELPER FUNCTIONS
# =============================

def load_json(filepath: Path) -> dict | list | None:
    """Load and parse JSON file with error handling."""
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error in {filepath}: {e}")
        return None


async def level_exists(session: AsyncSession, level_id: str) -> bool:
    """Check if a level exists in the database."""
    result = await session.execute(
        select(TrainingLevel).where(TrainingLevel.id == level_id)
    )
    return result.scalar_one_or_none() is not None


async def question_exists(session: AsyncSession, question_id: str) -> bool:
    """Check if a question already exists in the database."""
    result = await session.execute(
        select(TrainingQuestion).where(TrainingQuestion.id == question_id)
    )
    return result.scalar_one_or_none() is not None


# =============================
# SEEDING LOGIC
# =============================

async def seed_questions_from_file(
    session: AsyncSession,
    section_id: str,
    unit_num: int
) -> tuple[int, int, int]:
    """
    Seed questions from a single unit JSON file.
    
    Returns: (seeded_count, skipped_count, error_count)
    """
    filepath = DATA_DIR / section_id / f"unit_{unit_num}.json"
    
    if not filepath.exists():
        print(f"  ⚠️  File not found: {filepath.name}")
        return (0, 0, 0)
    
    data = load_json(filepath)
    if data is None:
        return (0, 0, 1)
    
    # Handle different JSON structures
    questions = []
    if isinstance(data, dict):
        if "questions" in data:
            questions = data["questions"]
        else:
            # Single question object
            questions = [data]
    elif isinstance(data, list):
        questions = data
    
    seeded = 0
    skipped = 0
    errors = 0
    
    for q in questions:
        try:
            q_id = q.get("id")
            level_id = q.get("level_id")
            
            if not q_id or not level_id:
                print(f"    ⚠️  Missing id or level_id in question: {q}")
                errors += 1
                continue
            
            # Check if question already exists (idempotent)
            if await question_exists(session, q_id):
                skipped += 1
                continue
            
            # Validate foreign key
            if not await level_exists(session, level_id):
                print(f"    ⚠️  Level not found: {level_id} (question: {q_id})")
                errors += 1
                continue
            
            # Build question object
            question = TrainingQuestion(
                id=q_id,
                level_id=level_id,
                type=q.get("type", "multiple_choice"),
                question=q.get("question", ""),
                payload=q.get("payload", {}),
                xp=q.get("xp", 2),
                order=q.get("order", 1),
                is_active=True,
            )
            
            session.add(question)
            seeded += 1
            
        except Exception as e:
            print(f"    ❌ Error processing question {q.get('id', 'unknown')}: {e}")
            errors += 1
    
    # Commit this unit's questions
    if seeded > 0:
        await session.commit()
    
    return (seeded, skipped, errors)


async def seed_section(session: AsyncSession, section_id: str) -> dict:
    """Seed all questions for a section."""
    print(f"\n📚 Seeding section: {section_id.upper()}")
    print(f"   Path: {DATA_DIR / section_id}")
    
    total_seeded = 0
    total_skipped = 0
    total_errors = 0
    level_stats = {}
    
    for unit_num in range(1, UNITS_PER_SECTION + 1):
        seeded, skipped, errors = await seed_questions_from_file(
            session, section_id, unit_num
        )
        
        total_seeded += seeded
        total_skipped += skipped
        total_errors += errors
        
        status = "✅" if seeded > 0 else ("⏭️" if skipped > 0 else "⚠️")
        print(f"   {status} Unit {unit_num}: seeded={seeded}, skipped={skipped}, errors={errors}")
        
        level_stats[f"unit_{unit_num}"] = {
            "seeded": seeded,
            "skipped": skipped,
            "errors": errors
        }
    
    print(f"   📊 Section total: seeded={total_seeded}, skipped={total_skipped}, errors={total_errors}")
    
    return {
        "section_id": section_id,
        "seeded": total_seeded,
        "skipped": total_skipped,
        "errors": total_errors,
        "units": level_stats
    }


async def seed_all_sections(session: AsyncSession) -> list[dict]:
    """Seed questions for all sections."""
    results = []
    
    for section_id in SECTIONS:
        section_stats = await seed_section(session, section_id)
        results.append(section_stats)
    
    return results


async def drop_all_questions(session: AsyncSession):
    """
    Drop all questions from the training_questions table.
    Use with caution - this will delete ALL question data.
    """
    print("\n🗑️  DROPPING ALL QUESTIONS...")
    
    # Count before delete
    result = await session.execute(text("SELECT COUNT(*) FROM training_questions"))
    count_before = result.scalar()
    print(f"   Questions before drop: {count_before}")
    
    # Delete all questions
    await session.execute(text("DELETE FROM training_questions"))
    await session.commit()
    
    print(f"   ✅ Deleted {count_before} questions")
    return count_before


async def sync_question_counts(session: AsyncSession):
    """
    Auto-sync total_questions field in training_levels table
    based on actual count of questions in training_questions table.
    """
    print("\n🔄 Syncing question counts in training_levels...")
    
    # Get actual question counts per level
    result = await session.execute(text("""
        SELECT level_id, COUNT(*) as count 
        FROM training_questions 
        WHERE is_active = true
        GROUP BY level_id
    """))
    
    counts = {row[0]: row[1] for row in result.fetchall()}
    
    # Update each level
    updated = 0
    for level_id, count in counts.items():
        await session.execute(text("""
            UPDATE training_levels
            SET total_questions = :count
            WHERE id = :level_id AND total_questions != :count
        """), {"level_id": level_id, "count": count})
        updated += 1
    
    await session.commit()
    print(f"   ✅ Updated {updated} levels with correct question counts")


async def verify_seeding(session: AsyncSession):
    """Print verification statistics."""
    print("\n" + "=" * 60)
    print("📊 VERIFICATION")
    print("=" * 60)
    
    # Total questions
    result = await session.execute(text("SELECT COUNT(*) FROM training_questions"))
    total = result.scalar()
    print(f"\n✅ Total questions in database: {total}")
    
    # Questions per section
    print("\n📚 Questions per section:")
    result = await session.execute(text("""
        SELECT 
            SPLIT_PART(level_id, '_', 1) as section,
            COUNT(*) as count
        FROM training_questions
        GROUP BY SPLIT_PART(level_id, '_', 1)
        ORDER BY section
    """))
    for row in result.fetchall():
        print(f"   {row[0]}: {row[1]} questions")
    
    # Questions per level (sample)
    print("\n📖 Sample level counts (first 10):")
    result = await session.execute(text("""
        SELECT level_id, COUNT(*) as count
        FROM training_questions
        GROUP BY level_id
        ORDER BY level_id
        LIMIT 10
    """))
    for row in result.fetchall():
        print(f"   {row[0]}: {row[1]} questions")


# =============================
# MAIN ENTRY POINT
# =============================

async def main(drop_first: bool = False):
    """Main seeding function."""
    print("=" * 60)
    print("🌱 PRAMUKA QUESTION SEEDING SCRIPT")
    print("=" * 60)
    print(f"\n📁 Data directory: {DATA_DIR}")
    print(f"📚 Sections to seed: {', '.join(SECTIONS)}")
    print(f"📖 Units per section: {UNITS_PER_SECTION}")
    if drop_first:
        print("\n⚠️  DROP MODE ENABLED - Will delete all existing questions first!")
    
    # Check data directory exists
    if not DATA_DIR.exists():
        print(f"\n❌ ERROR: Data directory not found: {DATA_DIR}")
        print("   Make sure you run this script from the backend root directory.")
        return
    
    async with SessionLocal() as session:
        try:
            # Drop all questions if flag is set
            if drop_first:
                await drop_all_questions(session)
            
            # Seed all sections
            results = await seed_all_sections(session)
            
            # Calculate totals
            total_seeded = sum(r["seeded"] for r in results)
            total_skipped = sum(r["skipped"] for r in results)
            total_errors = sum(r["errors"] for r in results)
            
            print("\n" + "=" * 60)
            print("📊 SEEDING SUMMARY")
            print("=" * 60)
            print(f"\n✅ Total seeded:  {total_seeded}")
            print(f"⏭️  Total skipped: {total_skipped}")
            print(f"❌ Total errors:  {total_errors}")
            
            # Sync question counts
            await sync_question_counts(session)
            
            # Verify
            await verify_seeding(session)
            
            print("\n" + "=" * 60)
            print("✅ SEEDING COMPLETED SUCCESSFULLY")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Fatal error during seeding: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Pramuka questions into the database")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all existing questions before seeding (USE WITH CAUTION)"
    )
    args = parser.parse_args()
    
    asyncio.run(main(drop_first=args.drop))
