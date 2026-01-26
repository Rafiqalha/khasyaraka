"""seed_training_data_puk_section

Revision ID: 89f3741b3905
Revises: 533267a7f5d4
Create Date: 2026-01-25 23:38:40.397959+00:00

PRODUCTION-GRADE TRAINING DATA SEEDING

This migration seeds the core "puk" (Pengetahuan Umum Kepramukaan) training section
with sections, units, levels, and questions. It is idempotent and safe to run multiple times.

CRITICAL: This migration ensures training data exists in production.
Without this data, users cannot access training paths and XP cannot be earned.
"""
from typing import Sequence, Union
import json
from pathlib import Path
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89f3741b3905'
down_revision: Union[str, Sequence[str], None] = '533267a7f5d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def load_json_file(filepath: Path) -> list:
    """Load JSON file safely"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def upgrade() -> None:
    """
    Seed training data for PUK section.
    
    This is idempotent - uses INSERT ... ON CONFLICT DO UPDATE.
    Safe to run multiple times.
    """
    # Get connection
    conn = op.get_bind()
    
    # Load data files (relative to project root)
    # Migration files are in alembic/versions/, data is in app/data/
    # Path: alembic/versions/ -> alembic/ -> project_root/ -> app/data/
    migration_file = Path(__file__)
    project_root = migration_file.parent.parent.parent  # alembic/versions/ -> project_root
    data_dir = project_root / "app" / "data"
    
    # Verify data directory exists
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Data directory not found: {data_dir}. "
            f"Expected location: {project_root}/app/data/"
        )
    
    # ==================== SEED SECTIONS ====================
    sections_file = data_dir / "section.json"
    sections_data = load_json_file(sections_file)
    
    for section in sections_data:
        if section.get("id") == "puk":  # Only seed PUK for now (core section)
            conn.execute(
                sa.text("""
                    INSERT INTO training_sections (id, title, description, tier, "order", is_active, created_at)
                    VALUES (:id, :title, :description, :tier, :order, :is_active, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        tier = EXCLUDED.tier,
                        "order" = EXCLUDED."order",
                        is_active = EXCLUDED.is_active
                """),
                {
                    "id": section["id"],
                    "title": section["title"],
                    "description": section.get("description"),
                    "tier": section.get("tier", "free"),
                    "order": section.get("order", 1),
                    "is_active": True,
                    "created_at": datetime.utcnow()
                }
            )
    
    # ==================== SEED UNITS ====================
    units_file = data_dir / "units.json"
    units_data = load_json_file(units_file)
    
    for unit in units_data:
        if unit.get("section_id") == "puk":  # Only PUK units
            conn.execute(
                sa.text("""
                    INSERT INTO training_units (id, section_id, title, description, "order", total_levels, is_active, created_at)
                    VALUES (:id, :section_id, :title, :description, :order, :total_levels, :is_active, :created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        section_id = EXCLUDED.section_id,
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        "order" = EXCLUDED."order",
                        total_levels = EXCLUDED.total_levels,
                        is_active = EXCLUDED.is_active
                """),
                {
                    "id": unit["id"],
                    "section_id": unit["section_id"],
                    "title": unit["title"],
                    "description": unit.get("description"),
                    "order": unit.get("order", 1),
                    "total_levels": unit.get("total_levels", 0),
                    "is_active": True,
                    "created_at": datetime.utcnow()
                }
            )
    
    # ==================== SEED LEVELS ====================
    levels_file = data_dir / "levels.json"
    levels_data = load_json_file(levels_file)
    
    for level in levels_data:
        if level.get("unit_id", "").startswith("puk_"):  # Only PUK levels
            unlock_rule_json = json.dumps(level.get("unlock_rule", {}))
            conn.execute(
                sa.text("""
                    INSERT INTO training_levels (
                        id, unit_id, level_number, difficulty, total_questions,
                        min_correct, xp_reward, unlock_rule, is_active, created_at
                    )
                    VALUES (
                        :id, :unit_id, :level_number, :difficulty, :total_questions,
                        :min_correct, :xp_reward, CAST(:unlock_rule AS jsonb), :is_active, :created_at
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        unit_id = EXCLUDED.unit_id,
                        level_number = EXCLUDED.level_number,
                        difficulty = EXCLUDED.difficulty,
                        total_questions = EXCLUDED.total_questions,
                        min_correct = EXCLUDED.min_correct,
                        xp_reward = EXCLUDED.xp_reward,
                        unlock_rule = EXCLUDED.unlock_rule,
                        is_active = EXCLUDED.is_active
                """),
                {
                    "id": level["id"],
                    "unit_id": level["unit_id"],
                    "level_number": level["level_number"],
                    "difficulty": level.get("difficulty", "easy"),
                    "total_questions": level.get("total_questions", 0),
                    "min_correct": level.get("min_correct", 1),
                    "xp_reward": level.get("xp_reward", 10),
                    "unlock_rule": unlock_rule_json,
                    "is_active": True,
                    "created_at": datetime.utcnow()
                }
            )
    
    # ==================== SEED QUESTIONS ====================
    questions_dir = data_dir / "question" / "puk"
    if questions_dir.exists():
        question_files = sorted(questions_dir.glob("unit_*.json"))
        
        for question_file in question_files:
            questions_data = load_json_file(question_file)
            
            # Handle both formats: {"questions": [...]} or [...]
            questions_list = []
            if isinstance(questions_data, list):
                questions_list = questions_data
            elif isinstance(questions_data, dict) and "questions" in questions_data:
                questions_list = questions_data["questions"]
            
            for question in questions_list:
                if not question.get("id") or not question.get("level_id"):
                    continue
                
                # Only seed questions for PUK levels
                if not question["level_id"].startswith("puk_"):
                    continue
                
                payload_json = json.dumps(question.get("payload", {}))
                
                conn.execute(
                    sa.text("""
                        INSERT INTO training_questions (
                            id, level_id, type, question, payload, xp, "order", is_active, created_at
                        )
                        VALUES (
                            :id, :level_id, :type, :question, CAST(:payload AS jsonb), :xp, :order, :is_active, :created_at
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            level_id = EXCLUDED.level_id,
                            type = EXCLUDED.type,
                            question = EXCLUDED.question,
                            payload = EXCLUDED.payload,
                            xp = EXCLUDED.xp,
                            "order" = EXCLUDED."order",
                            is_active = EXCLUDED.is_active
                    """),
                    {
                        "id": question["id"],
                        "level_id": question["level_id"],
                        "type": question.get("type", "multiple_choice"),
                        "question": question["question"],
                        "payload": payload_json,
                        "xp": question.get("xp", 0),
                        "order": question.get("order", 1),
                        "is_active": True,
                        "created_at": datetime.utcnow()
                    }
                )
    
    # ==================== SYNC QUESTION COUNTS ====================
    # Update total_questions in training_levels to match actual question count
    conn.execute(
        sa.text("""
            UPDATE training_levels
            SET total_questions = (
                SELECT COUNT(*)
                FROM training_questions
                WHERE training_questions.level_id = training_levels.id
                AND training_questions.is_active = true
            )
            WHERE id LIKE 'puk_%'
        """)
    )
    
    # Commit transaction
    conn.commit()


def downgrade() -> None:
    """
    Remove seeded training data.
    
    WARNING: This will delete all PUK training data including user progress.
    Only use in development/testing.
    """
    conn = op.get_bind()
    
    # Delete in reverse order (respecting foreign keys)
    conn.execute(sa.text("DELETE FROM training_questions WHERE level_id LIKE 'puk_%'"))
    conn.execute(sa.text("DELETE FROM training_levels WHERE id LIKE 'puk_%'"))
    conn.execute(sa.text("DELETE FROM training_units WHERE id LIKE 'puk_%'"))
    conn.execute(sa.text("DELETE FROM training_sections WHERE id = 'puk'"))
    
    conn.commit()
