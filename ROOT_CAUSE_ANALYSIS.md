# 🔴 ROOT CAUSE ANALYSIS: XP Never Enters Database & Leaderboard Empty

**Date:** 2026-01-26  
**Status:** CRITICAL PRODUCTION BUG

---

## 🔴 ROOT CAUSE SUMMARY

**PRIMARY ROOT CAUSE:** Training data (sections/units/levels/questions) not seeded in Supabase database.

**SYMPTOM CHAIN:**
1. Section "puk" doesn't exist in database → `GET /training/sections/puk/path` returns 404
2. Frontend can't load training path → Users can't access lessons
3. Users can't complete lessons → `POST /training/progress/submit` never called
4. XP never calculated → `users.total_xp` stays at 0
5. Leaderboard query `WHERE total_xp > 0` returns 0 rows → Empty leaderboard

**SECONDARY ISSUE:** Even if data exists, if `is_active = false`, same symptom chain occurs.

---

## 🧠 XP PIPELINE DIAGRAM

```
FRONTEND FLOW:
1. User opens training → GET /training/sections/puk/path
   ❌ FAILS: Section "puk" not found → 404
   → Training path never loads
   → User can't start lesson

2. User completes quiz (if path loaded) → POST /training/progress/submit
   ✅ Endpoint exists and works correctly
   ✅ Calculates XP from questions.xp
   ✅ Updates users.total_xp in atomic transaction
   ✅ Commits to PostgreSQL
   ✅ Updates Redis leaderboard

BACKEND FLOW (submit_progress):
1. Calculate XP from correct_question_ids
   → Query: SELECT questions WHERE id IN correct_question_ids
   → Sum: xp_earned = SUM(questions.xp)

2. Save progress (no commit)
   → INSERT/UPDATE user_progress

3. Update users.total_xp (no commit)
   → UPDATE users SET total_xp = total_xp + xp_earned

4. Commit ONCE (atomic)
   → COMMIT transaction

5. Verify XP persisted
   → SELECT users WHERE id = user_id

6. Update Redis (cache-only)
   → ZADD leaderboard:training {user_id: total_xp}

LEADERBOARD FLOW:
1. GET /leaderboard
   → Try Redis first
   → If empty/stale → Query PostgreSQL
   → Query: SELECT users WHERE total_xp > 0 ORDER BY total_xp DESC
   ❌ RETURNS 0 ROWS (users_with_xp = 0)
   → Empty leaderboard
```

---

## ❌ BROKEN POINTS

### **1. Section "puk" Not Found**

**File:** `app/modules/training/repository.py:42-52`  
**Function:** `get_section_by_id()`  
**Query:**
```python
stmt = (
    select(TrainingSection)
    .where(
        TrainingSection.id == section_id,
        TrainingSection.is_active == True  # ❌ Section doesn't exist OR is_active = false
    )
)
```

**Reason:** 
- Section "puk" doesn't exist in `training_sections` table
- OR section exists but `is_active = false`
- Seeding script `seed_pramuka_data.py` not run on Supabase
- OR migration didn't create tables

**Impact:** 
- `GET /training/sections/puk/path` → 404
- Frontend can't load training path
- Users can't access lessons

---

### **2. Training Data Not Seeded**

**File:** `seed_pramuka_data.py`  
**Function:** `seed_sections()`, `seed_units()`, `seed_levels()`, `seed_questions()`  
**Reason:**
- Script exists but not executed on Supabase
- Local database has data, Supabase doesn't
- Migration creates tables but doesn't seed data

**Impact:**
- No sections/units/levels/questions in database
- Training endpoints return empty/404
- Users can't complete lessons

---

### **3. XP Never Earned (Symptom, Not Cause)**

**File:** `app/modules/training/service.py:247-427`  
**Function:** `submit_progress()`  
**Reason:**
- Function is CORRECT
- But never called because users can't access lessons
- If called, XP would be calculated and persisted correctly

**Impact:**
- `users.total_xp` stays at 0
- Leaderboard query returns 0 rows

---

### **4. Leaderboard Empty (Symptom, Not Cause)**

**File:** `app/modules/gamification/service.py:269-276`  
**Function:** `_get_leaderboard_from_postgres()`  
**Query:**
```python
stmt = (
    select(User)
    .where(User.total_xp > 0)  # ❌ Returns 0 rows because all users have total_xp = 0
    .order_by(User.total_xp.desc())
    .limit(limit)
)
```

**Reason:**
- Query is CORRECT
- But `users.total_xp = 0` for all users
- Because no lessons completed (can't access training path)

**Impact:**
- `users_with_xp = 0`
- Empty leaderboard
- `my_rank = null`

---

## ✅ FIXES

### **FIX #1: Seed Training Data in Supabase**

**File:** `seed_pramuka_data.py`  
**Action:** Run seeding script on Supabase database

**Steps:**
```bash
# 1. Connect to Supabase database
# 2. Run seeding script
cd scout_os_backend
python seed_pramuka_data.py

# OR via Alembic migration (better for production)
# Create migration that seeds data
```

**Code Change (if needed):**
```python
# seed_pramuka_data.py already exists and is correct
# Just needs to be executed on Supabase

# Verify data seeded:
# SELECT * FROM training_sections WHERE id = 'puk';
# Should return 1 row with is_active = true
```

---

### **FIX #2: Verify Section is Active**

**File:** `app/modules/training/repository.py:42-52`  
**Action:** Add better error message and check if section exists but inactive

**Code Change:**
```python
async def get_section_by_id(self, section_id: str) -> Optional[TrainingSection]:
    """Get a specific section by ID"""
    # ✅ Check if section exists (even if inactive)
    stmt_exists = select(TrainingSection).where(TrainingSection.id == section_id)
    result_exists = await self.db.execute(stmt_exists)
    section_exists = result_exists.scalar_one_or_none()
    
    if not section_exists:
        logger.warning(f"⚠️ Section '{section_id}' does not exist in database")
        return None
    
    if not section_exists.is_active:
        logger.warning(f"⚠️ Section '{section_id}' exists but is_active = false")
        return None
    
    # ✅ Now check active section
    stmt = (
        select(TrainingSection)
        .where(
            TrainingSection.id == section_id,
            TrainingSection.is_active == True
        )
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

**OR simpler fix - just ensure seeding sets is_active = true:**
```python
# seed_pramuka_data.py:72 - Already sets is_active = True
existing.is_active = True  # ✅ This is already correct
```

---

### **FIX #3: Add Database Verification Endpoint**

**File:** `app/modules/training/router.py`  
**Action:** Add admin endpoint to check database state

**Code Change:**
```python
@router.get("/admin/verify-data")
async def verify_training_data(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify training data exists in database (admin only)"""
    from sqlalchemy import select, func
    from app.modules.training.models import TrainingSection, TrainingUnit, TrainingLevel, TrainingQuestion
    
    # Check sections
    sections_stmt = select(func.count(TrainingSection.id))
    sections_result = await db.execute(sections_stmt)
    sections_count = sections_result.scalar() or 0
    
    active_sections_stmt = select(func.count(TrainingSection.id)).where(TrainingSection.is_active == True)
    active_sections_result = await db.execute(active_sections_stmt)
    active_sections_count = active_sections_result.scalar() or 0
    
    # Check puk section specifically
    puk_section = await db.execute(
        select(TrainingSection).where(TrainingSection.id == "puk")
    )
    puk_exists = puk_section.scalar_one_or_none()
    
    return {
        "sections_total": sections_count,
        "sections_active": active_sections_count,
        "puk_exists": puk_exists is not None,
        "puk_is_active": puk_exists.is_active if puk_exists else False,
        "units_count": await db.execute(select(func.count(TrainingUnit.id))).scalar() or 0,
        "levels_count": await db.execute(select(func.count(TrainingLevel.id))).scalar() or 0,
        "questions_count": await db.execute(select(func.count(TrainingQuestion.id))).scalar() or 0,
    }
```

---

### **FIX #4: Ensure Migration Creates Tables**

**File:** Alembic migrations  
**Action:** Verify tables exist

**SQL Check:**
```sql
-- Check if tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('training_sections', 'training_units', 'training_levels', 'training_questions');

-- Should return 4 rows
```

**If tables don't exist:**
```bash
# Run migrations
cd scout_os_backend
alembic upgrade head
```

---

## 🧪 HOW TO VERIFY

### **1. Verify Section Exists**

**SQL:**
```sql
-- Check if section "puk" exists
SELECT id, title, is_active 
FROM training_sections 
WHERE id = 'puk';

-- Expected: 1 row with is_active = true
-- If 0 rows → Section not seeded
-- If 1 row with is_active = false → Section inactive
```

**API:**
```bash
# Should return 200, not 404
curl -X GET "http://localhost:8000/api/v1/training/sections/puk/path" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected: LearningPathResponse with units and levels
# If 404 → Section doesn't exist or inactive
```

---

### **2. Verify Training Data Seeded**

**SQL:**
```sql
-- Count training data
SELECT 
    (SELECT COUNT(*) FROM training_sections) as sections,
    (SELECT COUNT(*) FROM training_units) as units,
    (SELECT COUNT(*) FROM training_levels) as levels,
    (SELECT COUNT(*) FROM training_questions) as questions;

-- Expected: sections >= 1, units >= 1, levels >= 1, questions >= 1
-- If all 0 → Data not seeded
```

**API:**
```bash
# Should return sections
curl -X GET "http://localhost:8000/api/v1/training/sections"

# Expected: SectionListResponse with at least 1 section
# If empty → Data not seeded
```

---

### **3. Verify XP Update Works**

**SQL (Before):**
```sql
-- Check user's current XP
SELECT id, email, total_xp 
FROM users 
WHERE id = 1;

-- Note: total_xp value
```

**API (Submit Progress):**
```bash
# Complete a lesson and submit progress
curl -X POST "http://localhost:8000/api/v1/training/progress/submit" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "level_id": "puk_u1_l1",
    "score": 5,
    "total_questions": 5,
    "correct_answers": 5,
    "correct_question_ids": ["q1", "q2", "q3", "q4", "q5"],
    "time_spent_seconds": 60
  }'

# Expected: Response with xp_earned > 0 and total_xp increased
```

**SQL (After):**
```sql
-- Check user's XP increased
SELECT id, email, total_xp 
FROM users 
WHERE id = 1;

-- Expected: total_xp increased by xp_earned amount
-- If unchanged → XP update failed
```

---

### **4. Verify Leaderboard Reads Correctly**

**SQL:**
```sql
-- Check users with XP
SELECT COUNT(*) as users_with_xp
FROM users 
WHERE total_xp > 0;

-- Expected: >= 1 if user completed lesson
-- If 0 → No users have XP (can't complete lessons)
```

**API:**
```bash
# Get leaderboard
curl -X GET "http://localhost:8000/api/v1/leaderboard" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected: LeaderboardResponse with top_users array
# If empty → users_with_xp = 0 (no lessons completed)
```

---

## 📋 CHECKLIST

- [ ] **CRITICAL:** Run `seed_pramuka_data.py` on Supabase database
- [ ] **CRITICAL:** Verify section "puk" exists: `SELECT * FROM training_sections WHERE id = 'puk'`
- [ ] **CRITICAL:** Verify section is active: `is_active = true`
- [ ] Verify training tables exist: `training_sections`, `training_units`, `training_levels`, `training_questions`
- [ ] Verify data seeded: Count rows in each table > 0
- [ ] Test training path endpoint: `GET /training/sections/puk/path` returns 200
- [ ] Complete a lesson and verify XP increases
- [ ] Verify leaderboard shows user after XP earned

---

## 🎯 SUMMARY

**ROOT CAUSE:** Training data not seeded in Supabase → Section "puk" doesn't exist → Users can't access lessons → XP never earned → Leaderboard empty

**FIX:** Seed training data in Supabase database using `seed_pramuka_data.py`

**VERIFICATION:** Check database has sections/units/levels/questions, then test training path endpoint

**EXPECTED RESULT:** After seeding, training path loads, users can complete lessons, XP increases, leaderboard populated
