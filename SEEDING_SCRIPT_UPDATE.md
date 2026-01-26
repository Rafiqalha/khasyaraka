# Seeding Script Update - Auto-Sync Question Counts

## Problem Solved

Previously, the `total_questions` field in `levels.json` often didn't match the actual number of questions seeded from the question JSON files. For example:
- `levels.json` might say: `"total_questions": 8`
- But actual questions seeded: only 1 or 2

This caused UI bugs where the progress bar expected more questions than were actually available.

## Solution Implemented

Added **auto-sync functionality** to the seeding script that automatically calculates and updates the `total_questions` field in the database based on the actual count of questions inserted.

## Changes Made

### 1. Updated Imports

```python
from sqlalchemy import select, text  # Added 'text'
```

### 2. Added New Method: `sync_question_counts()`

Location: Inside `PramukaDataSeeder` class

```python
async def sync_question_counts(self, session: AsyncSession):
    """
    Auto-sync total_questions field in training_levels table
    based on actual count of questions in training_questions table.
    """
    print("\n🔄 Syncing question counts...")
    
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
    
    # ... logging and summary ...
```

**What it does:**
- Counts actual questions for each level in `training_questions` table
- Updates the `total_questions` field in `training_levels` table
- Only counts active questions (`is_active = true`)
- Shows a summary of synced levels

### 3. Updated `seed_all()` Method

Added the sync call as the **last step** before success message:

```python
async def seed_all(self):
    async with SessionLocal() as session:
        try:
            await self.seed_sections(session)
            await self.seed_units(session)
            await self.seed_levels(session)
            await self.seed_questions(session)
            
            # AUTO-SYNC (NEW!)
            await self.sync_question_counts(session)
            
            print("✅ SEEDING COMPLETED SUCCESSFULLY")
```

## How It Works

### Execution Flow

```
1. Seed Sections → DB
2. Seed Units → DB
3. Seed Levels → DB (with initial total_questions from JSON)
4. Seed Questions → DB (actual questions inserted)
5. Sync Question Counts → Update total_questions to match reality ✨
6. Success!
```

### SQL Logic

The sync uses a subquery to count questions per level:

```sql
UPDATE training_levels
SET total_questions = (
    SELECT COUNT(*)
    FROM training_questions
    WHERE training_questions.level_id = training_levels.id
    AND training_questions.is_active = true
);
```

**Example:**
- Before sync: `puk_u1_l1.total_questions = 8` (from JSON)
- After sync: `puk_u1_l1.total_questions = 1` (actual count in DB)

## Benefits

### 1. **Prevents UI Bugs**
Progress bars now show correct question counts.

### 2. **Idempotent**
Safe to run multiple times - always syncs to current reality.

### 3. **Automatic**
No manual intervention needed. Just run the script!

### 4. **Performance**
Uses raw SQL for efficient bulk updates.

### 5. **Logging**
Shows summary of synced levels for verification.

## Example Output

When you run `python seed_pramuka_data.py`:

```
============================================================
🌱 PRAMUKA TRAINING DATA SEEDING
============================================================

📚 Seeding Sections...
  ✓ Created section: puk
  ✓ Created section: ppgd
  ...

📖 Seeding Units...
  ✓ Created unit: puk_u1
  ✓ Created unit: puk_u2
  ...

🎯 Seeding Levels...
  ✓ Created level: puk_u1_l1
  ✓ Created level: puk_u1_l2
  ...

❓ Seeding Questions...
  📄 Processing: question/puk/unit_1.json
    ✓ Created: q_puk_u1_l1_01
  📊 Total questions processed: 1

🔄 Syncing question counts...
  ✓ Synced 25 levels

  📊 Sample of synced levels:
    • puk_u1_l1 (Level 1): 1 questions
    • puk_u1_l2 (Level 2): 0 questions
    • puk_u1_l3 (Level 3): 0 questions
    • puk_u2_l1 (Level 1): 0 questions
    • puk_u2_l2 (Level 2): 0 questions
    ... and 20 more

============================================================
✅ SEEDING COMPLETED SUCCESSFULLY
============================================================
```

## Testing

### Run the Script

```bash
cd scout_os_backend
python seed_pramuka_data.py
```

### Verify in Database

```sql
-- Check synced counts
SELECT 
    id,
    level_number,
    total_questions,
    (SELECT COUNT(*) FROM training_questions WHERE level_id = training_levels.id) as actual_count
FROM training_levels
ORDER BY id;
```

Both columns should match!

### Verify in API

```bash
curl http://localhost:8000/api/v1/training/units/puk_u1/levels
```

Check the `total_questions` field in the response.

### Verify in Flutter UI

The progress bar should now show correct counts and work properly!

## Edge Cases Handled

### 1. **Levels with No Questions**
- `total_questions` will be set to `0`
- UI can handle this gracefully

### 2. **Inactive Questions**
- Only active questions (`is_active = true`) are counted
- Deleted questions won't affect count

### 3. **Multiple Runs**
- Script is idempotent
- Count always reflects current database state

### 4. **Empty Database**
- If no questions exist, all levels will have `total_questions = 0`
- Script won't crash

## Rollback

If you need to revert to JSON values:

```python
# In seed_all(), comment out the sync line:
# await self.sync_question_counts(session)
```

Then re-run the script. Levels will use values from `levels.json`.

## Future Enhancements

Potential improvements:

1. **Also sync `min_correct`** based on difficulty:
   - very_easy: 80% of total
   - easy: 75%
   - medium: 70%
   - hard: 65%

2. **Validate question counts** before syncing:
   - Warn if any level has 0 questions
   - Suggest which levels need questions

3. **Update unit `total_levels`** count similarly:
   - Count actual active levels per unit
   - Sync to database

## Status

✅ **IMPLEMENTED AND TESTED**

- [x] Add `text` import
- [x] Create `sync_question_counts()` method
- [x] Update `seed_all()` to call sync
- [x] Add logging and summary
- [x] Handle edge cases
- [x] Test with current data

---

**Last Updated:** 2026-01-18  
**Author:** AI Assistant  
**Related Files:**
- `seed_pramuka_data.py` (modified)
- `app/data/levels.json` (source data)
- `app/modules/training/models.py` (database models)
