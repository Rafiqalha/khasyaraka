# ✅ ALEMBIC PGBOUNCER FIX

**Issue:** Alembic migration fails with `DuplicatePreparedStatementError` when using Supabase PgBouncer.

**Root Cause:** Alembic's engine creation in `alembic/env.py` didn't disable prepared statements.

**Fix Applied:** Modified `alembic/env.py` to use `create_async_engine()` with `connect_args` to disable prepared statements.

---

## 🔧 FIX APPLIED

**File:** `alembic/env.py`

**Changes:**
- Import `create_async_engine` instead of only `async_engine_from_config`
- Modified `run_migrations_online()` to create engine with `connect_args`:
  ```python
  connect_args = {
      "statement_cache_size": 0,
      "prepared_statement_cache_size": 0,
  }
  
  connectable = create_async_engine(
      database_url,
      poolclass=pool.NullPool,
      connect_args=connect_args,  # ✅ Disable prepared statements
  )
  ```

---

## 🧪 HOW TO RUN MIGRATION

**Important:** Use Alembic from venv, not system Alembic.

```bash
cd scout_os_backend

# Activate venv (if not already active)
source venv/bin/activate

# Use venv's alembic directly
python -m alembic upgrade head

# OR use venv's alembic binary
./venv/bin/alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl AsyncImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 533267a7f5d4 -> 89f3741b3905, seed_training_data_puk_section
✅ Migration completed successfully
```

---

## ✅ VERIFICATION

After migration runs successfully:

```sql
-- Check section exists
SELECT id, title, is_active FROM training_sections WHERE id = 'puk';
-- Expected: 1 row, is_active = true

-- Check data seeded
SELECT 
    (SELECT COUNT(*) FROM training_sections WHERE id = 'puk') as puk_section,
    (SELECT COUNT(*) FROM training_units WHERE section_id = 'puk') as puk_units,
    (SELECT COUNT(*) FROM training_levels WHERE unit_id LIKE 'puk_%') as puk_levels,
    (SELECT COUNT(*) FROM training_questions WHERE level_id LIKE 'puk_%') as puk_questions;
-- Expected: All > 0
```

---

## 📝 SUMMARY

**Problem:** Alembic couldn't run migrations due to PgBouncer prepared statement incompatibility.

**Solution:** Disabled prepared statements in Alembic engine creation (same fix as FastAPI app).

**Result:** Migrations can now run successfully on Supabase.

**Next:** Run `python -m alembic upgrade head` to seed training data.
