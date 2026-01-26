#!/usr/bin/env python3
"""
Pramuka Training Data Seeding Script (FIXED VERSION)

Features:
- Robust JSON parsing (handles arrays, dicts with "questions" key, or single objects)
- Validates Foreign Keys (checks if Level ID exists before inserting Question)
- Idempotent (Safe to run multiple times)
- Detailed logging for debugging
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Import database session and models
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.modules.training.models import (
    TrainingSection,
    TrainingUnit,
    TrainingLevel,
    TrainingQuestion
)

class PramukaDataSeeder:
    """Handles seeding of Pramuka training data"""
    
    def __init__(self, data_dir: Path = Path("app/data")):
        self.data_dir = data_dir
        self.sections_file = data_dir / "section.json"
        self.units_file = data_dir / "units.json"
        self.levels_file = data_dir / "levels.json"
        self.questions_dir = data_dir / "question"
    
    def load_json(self, filepath: Path) -> Any:
        """Load and parse JSON file with error handling"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ File not found: {filepath}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {filepath}: {e}")
            return None
    
    async def seed_sections(self, session: AsyncSession) -> Dict[str, TrainingSection]:
        print("\n📚 Seeding Sections...")
        sections_data = self.load_json(self.sections_file)
        if not sections_data:
            print("⚠️  No sections data found")
            return {}
        
        sections_map = {}
        for section_data in sections_data:
            section_id = section_data["id"]
            
            # Check exist
            result = await session.execute(select(TrainingSection).where(TrainingSection.id == section_id))
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.title = section_data["title"]
                existing.description = section_data.get("description")
                existing.tier = section_data.get("tier", "free")
                existing.order = section_data.get("order", 1)
                existing.is_active = True
                sections_map[section_id] = existing
                print(f"  ✓ Updated section: {section_id}")
            else:
                new_sec = TrainingSection(
                    id=section_id,
                    title=section_data["title"],
                    description=section_data.get("description"),
                    tier=section_data.get("tier", "free"),
                    order=section_data.get("order", 1),
                    is_active=True
                )
                session.add(new_sec)
                sections_map[section_id] = new_sec
                print(f"  ✓ Created section: {section_id}")
        
        await session.commit()
        return sections_map

    async def seed_units(self, session: AsyncSession) -> Dict[str, TrainingUnit]:
        print("\n📖 Seeding Units...")
        units_data = self.load_json(self.units_file)
        if not units_data:
            print("⚠️  No units data found")
            return {}
        
        units_map = {}
        for unit_data in units_data:
            unit_id = unit_data["id"]
            
            result = await session.execute(select(TrainingUnit).where(TrainingUnit.id == unit_id))
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.section_id = unit_data["section_id"]
                existing.title = unit_data["title"]
                existing.description = unit_data.get("description")
                existing.order = unit_data.get("order", 1)
                existing.total_levels = unit_data.get("total_levels", 0)
                existing.is_active = True
                units_map[unit_id] = existing
                print(f"  ✓ Updated unit: {unit_id}")
            else:
                new_unit = TrainingUnit(
                    id=unit_id,
                    section_id=unit_data["section_id"],
                    title=unit_data["title"],
                    description=unit_data.get("description"),
                    order=unit_data.get("order", 1),
                    total_levels=unit_data.get("total_levels", 0),
                    is_active=True
                )
                session.add(new_unit)
                units_map[unit_id] = new_unit
                print(f"  ✓ Created unit: {unit_id}")
        
        await session.commit()
        return units_map

    async def seed_levels(self, session: AsyncSession) -> Dict[str, TrainingLevel]:
        print("\n🎯 Seeding Levels...")
        levels_data = self.load_json(self.levels_file)
        if not levels_data:
            print("⚠️  No levels data found")
            return {}
        
        levels_map = {}
        for level_data in levels_data:
            level_id = level_data["id"]
            
            result = await session.execute(select(TrainingLevel).where(TrainingLevel.id == level_id))
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.unit_id = level_data["unit_id"]
                existing.title = level_data.get("title", f"Level {level_data.get('level_number')}") # FIX: Add Title
                existing.description = level_data.get("description") # FIX: Add Description
                existing.level_number = level_data["level_number"]
                existing.difficulty = level_data.get("difficulty", "easy")
                existing.total_questions = level_data.get("total_questions", 5)
                existing.min_correct = level_data.get("min_correct", 4)
                existing.xp_reward = level_data.get("xp_reward", 10)
                existing.unlock_rule = level_data.get("unlock_rule")
                existing.is_active = True
                levels_map[level_id] = existing
                print(f"  ✓ Updated level: {level_id}")
            else:
                new_level = TrainingLevel(
                    id=level_id,
                    unit_id=level_data["unit_id"],
                    level_number=level_data["level_number"],
                    difficulty=level_data.get("difficulty", "easy"),
                    total_questions=level_data.get("total_questions", 5),
                    min_correct=level_data.get("min_correct", 4),
                    xp_reward=level_data.get("xp_reward", 10),
                    unlock_rule=level_data.get("unlock_rule"),
                    is_active=True
                )
                session.add(new_level)
                levels_map[level_id] = new_level
                print(f"  ✓ Created level: {level_id}")
        
        await session.commit()
        return levels_map

    async def seed_questions(self, session: AsyncSession):
        """Seed training questions with robust JSON handling"""
        print("\n❓ Seeding Questions...")
        
        # Cari semua file .json di folder questions dan subfoldernya
        question_files = list(self.questions_dir.rglob("*.json"))
        
        if not question_files:
            print("⚠️  No question files found")
            return
        
        total_questions = 0
        
        for question_file in question_files:
            print(f"\n  📄 Processing: {question_file.relative_to(self.data_dir)}")
            
            json_content = self.load_json(question_file)
            if not json_content:
                continue
            
            # --- LOGIKA BARU UNTUK MENANGANI BERBAGAI FORMAT JSON ---
            questions_list = []
            
            if isinstance(json_content, list):
                # Format 1: Langsung array of objects [...]
                questions_list = json_content
            elif isinstance(json_content, dict):
                # Format 2: Object wrapper {"unit_id": "...", "questions": [...]}
                if "questions" in json_content and isinstance(json_content["questions"], list):
                    questions_list = json_content["questions"]
                # Format 3: Single Question Object (jarang, tapi mungkin)
                elif "id" in json_content and "question" in json_content:
                    questions_list = [json_content]
            
            if not questions_list:
                print(f"    ⚠️ No valid questions found in {question_file.name}")
                continue
            
            # CRITICAL FIX: Track order PER LEVEL, not per file
            # This ensures that questions from different levels in the same file
            # get correct order values (1, 2, 3...) for each level separately
            # Note: If same level appears in multiple files, we use max existing order + 1
            level_order_counters = {}  # level_id -> current_order
            
            for question_data in questions_list:
                # Validasi field wajib
                if "id" not in question_data or "level_id" not in question_data:
                    print(f"    ❌ Skipping invalid question data (missing id or level_id)")
                    continue

                question_id = question_data["id"]
                level_id = question_data["level_id"]

                # Cek apakah Level ID ini benar-benar ada di database (Foreign Key Check)
                # Ini penting agar tidak error "Insert or update on table violates foreign key constraint"
                level_check = await session.execute(
                    select(TrainingLevel).where(TrainingLevel.id == level_id)
                )
                if not level_check.scalar_one_or_none():
                    print(f"    ❌ Level ID '{level_id}' NOT FOUND. Skipping question '{question_id}'")
                    continue
                
                # CRITICAL: Get or initialize order counter for this level
                # If this is the first question for this level in this file, check existing max order
                if level_id not in level_order_counters:
                    # Get max order for this level from database
                    max_order_stmt = select(TrainingQuestion.order).where(
                        TrainingQuestion.level_id == level_id
                    ).order_by(TrainingQuestion.order.desc()).limit(1)
                    max_order_result = await session.execute(max_order_stmt)
                    max_order = max_order_result.scalar_one_or_none() or 0
                    level_order_counters[level_id] = max_order
                
                level_order_counters[level_id] += 1
                question_order = level_order_counters[level_id]
                
                # Cek apakah pertanyaan sudah ada
                result = await session.execute(
                    select(TrainingQuestion).where(TrainingQuestion.id == question_id)
                )
                existing_question = result.scalar_one_or_none()
                
                # Normalisasi data (menggunakan .get untuk field opsional)
                q_type = question_data.get("type", "multiple_choice")
                q_text = question_data.get("question") or question_data.get("question_text", "No Question Text")
                q_payload = question_data.get("payload", {})
                q_xp = question_data.get("xp") or question_data.get("xp_value", 2)
                
                # Use order from JSON if provided, otherwise use our counter
                json_order = question_data.get("order")
                final_order = json_order if json_order is not None else question_order
                
                if existing_question:
                    # Update - preserve order if question already exists and has valid order
                    # Only update order if it's 0 or invalid
                    if existing_question.order == 0 or existing_question.order is None:
                        existing_question.order = final_order
                    # Otherwise keep existing order to maintain sequence
                    
                    existing_question.level_id = level_id
                    existing_question.type = q_type
                    existing_question.question = q_text
                    existing_question.payload = q_payload
                    existing_question.xp = q_xp
                    existing_question.is_active = True
                    print(f"    ✓ Updated: {question_id} (order={existing_question.order})")
                else:
                    # Create
                    new_question = TrainingQuestion(
                        id=question_id,
                        level_id=level_id,
                        type=q_type,
                        question=q_text,
                        payload=q_payload,
                        xp=q_xp,
                        order=final_order,
                        is_active=True
                    )
                    session.add(new_question)
                    print(f"    ✓ Created: {question_id} (order={final_order})")
                
                total_questions += 1
        
        await session.commit()
        print(f"\n  📊 Total questions processed: {total_questions}")

    async def sync_question_counts(self, session: AsyncSession):
        """
        Auto-sync total_questions field in training_levels table
        based on actual count of questions in training_questions table.
        
        This prevents mismatches between levels.json and actual data.
        """
        print("\n🔄 Syncing question counts...")
        
        try:
            # Use raw SQL for performance
            update_query = text("""
                UPDATE training_levels
                SET total_questions = (
                    SELECT COUNT(*)
                    FROM training_questions
                    WHERE training_questions.level_id = training_levels.id
                    AND training_questions.is_active = true
                )
            """)
            
            result = await session.execute(update_query)
            await session.commit()
            
            # Get summary of synced levels
            summary_query = text("""
                SELECT 
                    id,
                    level_number,
                    total_questions
                FROM training_levels
                WHERE total_questions > 0
                ORDER BY id
            """)
            
            summary_result = await session.execute(summary_query)
            synced_levels = summary_result.fetchall()
            
            print(f"  ✓ Synced {len(synced_levels)} levels")
            
            # Show sample (first 5)
            if synced_levels:
                print("\n  📊 Sample of synced levels:")
                for level in synced_levels[:5]:
                    level_id, level_num, q_count = level
                    print(f"    • {level_id} (Level {level_num}): {q_count} questions")
                
                if len(synced_levels) > 5:
                    print(f"    ... and {len(synced_levels) - 5} more")
            
        except Exception as e:
            print(f"  ❌ Error syncing question counts: {e}")
            await session.rollback()
            raise

    async def seed_all(self):
        """Run all seeding operations in order"""
        print("\n" + "=" * 60)
        print("🌱 PRAMUKA TRAINING DATA SEEDING")
        print("=" * 60)
        
        async with SessionLocal() as session:
            try:
                # Urutan seeding sangat penting karena relasi (Foreign Keys)
                await self.seed_sections(session)
                await self.seed_units(session)
                await self.seed_levels(session)
                await self.seed_questions(session)
                
                # Auto-sync question counts (NEW!)
                # This ensures total_questions matches actual count in DB
                await self.sync_question_counts(session)
                
                print("\n" + "=" * 60)
                print("✅ SEEDING COMPLETED SUCCESSFULLY")
                print("=" * 60)
                
            except Exception as e:
                print(f"\n❌ Error during seeding: {e}")
                await session.rollback()
                raise

async def create_tables():
    """Create all database tables (if they don't exist)"""
    print("\n🔧 Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tables created/verified\n")

async def main():
    try:
        await create_tables()
        seeder = PramukaDataSeeder()
        await seeder.seed_all()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())