# Dependency Impact Report
## Pre-Refactoring Analysis

**Generated:** Before Phase 1 refactoring  
**Purpose:** Identify all dependencies and circular import risks

---

## 1. `app/core/database.py` Dependencies

### **Files Importing `app.core.database`:**
1. ✅ `app/modules/training/service.py` (Line 4)
   - Uses: `from app.core.database import supabase`
   - Usage: Direct Supabase queries for training paths, lessons, questions
   - **Impact:** HIGH - Core service file, actively used
   - **Migration Path:** Replace with SQLAlchemy repository pattern

2. ✅ `app/modules/sku/router.py` (Line 5)
   - Uses: `from app.core.database import supabase`
   - Usage: Direct Supabase queries for SKU levels, missions, tasks
   - **Impact:** HIGH - Active router with multiple endpoints
   - **Migration Path:** Replace with SQLAlchemy repository pattern

3. ✅ `app/api/endpoints/sku.py` (Line 2)
   - Uses: `from app.core.database import supabase`
   - Usage: Direct Supabase queries (duplicate of sku/router.py)
   - **Impact:** MEDIUM - Appears to be duplicate/legacy endpoint
   - **Migration Path:** Consolidate with sku/router.py or remove

### **Files Referencing Supabase (indirect):**
4. ⚠️ `app/core/security.py` (Line 18)
   - Uses: `settings.SUPABASE_JWT_SECRET` (config, not database.py)
   - **Impact:** LOW - Only uses config, not database.py import
   - **Action:** No change needed

### **Summary:**
- **Total Dependencies:** 3 direct imports
- **Risk Level:** HIGH (active production code)
- **Circular Import Risk:** LOW (database.py only exports `supabase` client)
- **Action Required:** Migrate all 3 files to SQLAlchemy before removing database.py

---

## 2. `app/api/routes/training/*` Dependencies

### **Files Importing from `app.api.routes.training`:**
1. ✅ `app/api/router.py` (Line 3)
   - Uses: `from app.api.routes.training import training_router`
   - Usage: Registers training router in main API router
   - **Impact:** CRITICAL - Main router registration
   - **Migration Path:** Update to import from `app.modules.training.router`

### **Internal Dependencies within `app/api/routes/training/`:**
2. ✅ `app/api/routes/training/__init__.py`
   - Imports: All sub-routers (section, unit, level, question, path)
   - Exports: `training_router` (combined router)
   - **Impact:** HIGH - Aggregates all training routes

3. ✅ `app/api/routes/training/section.py`
   - Imports: `from .schemas import SectionListResponse, TrainingSectionResponse`
   - Imports: `from app.modules.training.models import TrainingSection`
   - **Impact:** MEDIUM - Uses local schemas, depends on models

4. ✅ `app/api/routes/training/unit.py`
   - Imports: `from .schemas import UnitListResponse, TrainingUnitResponse`
   - Imports: `from app.modules.training.models import TrainingUnit, TrainingSection`
   - **Impact:** MEDIUM - Uses local schemas, depends on models

5. ✅ `app/api/routes/training/level.py`
   - Imports: `from .schemas import LevelListResponse, TrainingLevelResponse`
   - Imports: `from app.modules.training.models import TrainingLevel, TrainingUnit`
   - **Impact:** MEDIUM - Uses local schemas, depends on models

6. ✅ `app/api/routes/training/question.py`
   - Imports: `from .schemas import QuestionListResponse, TrainingQuestionResponse`
   - Imports: `from app.modules.training.models import TrainingQuestion, TrainingLevel`
   - **Impact:** MEDIUM - Uses local schemas, depends on models

7. ✅ `app/api/routes/training/path.py`
   - Imports: `from .schemas import LearningPathResponse, PathUnitSchema, PathLevelSchema`
   - Imports: `from app.modules.training.models import TrainingSection, TrainingUnit, TrainingLevel`
   - **Impact:** MEDIUM - Uses local schemas, depends on models

### **Schema Dependencies:**
8. ✅ `app/api/routes/training/schemas.py`
   - **Self-contained:** Defines all schemas used by training routes
   - **No external imports** from other schemas
   - **Impact:** LOW - Can be moved independently

### **Summary:**
- **Total Dependencies:** 1 external (api/router.py), 6 internal route files
- **Risk Level:** CRITICAL (main API routing)
- **Circular Import Risk:** LOW (routes import models, not vice versa)
- **Action Required:** 
  - Merge all routes into `app/modules/training/router.py`
  - Merge schemas into `app/modules/training/schemas.py`
  - Update `app/api/router.py` import

---

## 3. `app/schemas/*` Dependencies

### **Files Importing from `app.schemas.sku`:**
1. ✅ `app/modules/sku/router.py` (Line 8)
   - Uses: `from app.schemas.sku import (SkuLevelResponse, MissionResponse, AnswerRequest, AnswerResponse)`
   - **Impact:** HIGH - Active router using schemas
   - **Migration Path:** Move to `app/modules/sku/schemas.py`

2. ✅ `app/api/endpoints/sku.py` (Line 3)
   - Uses: `from app.schemas.sku import SkuLevelResponse, MissionResponse, AnswerRequest, AnswerResponse`
   - **Impact:** MEDIUM - Duplicate/legacy endpoint
   - **Migration Path:** Consolidate with sku/router.py or remove

### **Files Importing from `app.schemas.common`:**
- ❌ **NONE FOUND** - File exists but is empty/unused
- **Impact:** NONE - Safe to remove or move

### **Summary:**
- **Total Dependencies:** 2 files importing `app.schemas.sku`
- **Risk Level:** MEDIUM (only SKU module affected)
- **Circular Import Risk:** NONE (schemas don't import other modules)
- **Action Required:** 
  - Move `app/schemas/sku.py` → `app/modules/sku/schemas.py`
  - Update 2 import statements
  - Remove `app/schemas/common.py` (empty)

---

## 4. Circular Import Risk Analysis

### **Potential Circular Dependencies:**

#### **Risk 1: Training Module**
```
app/modules/training/router.py
  → imports app/modules/training/models.py
  → imports app/modules/training/schemas.py
  → imports app/modules/training/service.py
  → imports app/modules/training/repository.py
```
**Status:** ✅ SAFE - Standard dependency flow (router → service → repository → models)
**Risk Level:** LOW

#### **Risk 2: API Routes → Modules**
```
app/api/routes/training/*.py
  → imports app/modules/training/models.py
  → imports app/api/routes/training/schemas.py
```
**Status:** ✅ SAFE - Routes import models, models don't import routes
**Risk Level:** LOW

#### **Risk 3: SKU Module**
```
app/modules/sku/router.py
  → imports app.core.database (supabase)
  → imports app.schemas.sku
```
**Status:** ✅ SAFE - No circular dependencies
**Risk Level:** LOW

#### **Risk 4: Main Router**
```
app/api/router.py
  → imports app.api.routes.training
  → imports app.modules.auth.router
```
**Status:** ✅ SAFE - Router aggregation, no circular imports
**Risk Level:** LOW

### **Overall Circular Import Risk:** ✅ **LOW**
- No detected circular dependencies
- Standard dependency flow maintained
- Models are leaf nodes (no imports)
- Routers are top-level (import everything)

---

## 5. Migration Impact Summary

### **High Priority (Must Fix Before Removal):**

| File | Current Import | Impact | Migration Required |
|------|---------------|--------|-------------------|
| `app/modules/training/service.py` | `app.core.database` | HIGH | Migrate to SQLAlchemy repository |
| `app/modules/sku/router.py` | `app.core.database` | HIGH | Migrate to SQLAlchemy repository |
| `app/api/endpoints/sku.py` | `app.core.database` | MEDIUM | Consolidate or remove |
| `app/api/router.py` | `app.api.routes.training` | CRITICAL | Update import path |
| `app/modules/sku/router.py` | `app.schemas.sku` | HIGH | Move schema file |
| `app/api/endpoints/sku.py` | `app.schemas.sku` | MEDIUM | Update import path |

### **Medium Priority (Can Fix During Migration):**

| File | Current Import | Impact | Migration Required |
|------|---------------|--------|-------------------|
| All `app/api/routes/training/*.py` | Local `.schemas` | MEDIUM | Merge into modules/training |
| `app/api/routes/training/__init__.py` | All sub-routers | HIGH | Merge into modules/training/router.py |

### **Low Priority (Cleanup):**

| File | Current Import | Impact | Migration Required |
|------|---------------|--------|-------------------|
| `app/schemas/common.py` | None (empty) | NONE | Safe to remove |

---

## 6. Recommended Migration Order

### **Step 1: Move Schemas (Lowest Risk)**
1. Move `app/schemas/sku.py` → `app/modules/sku/schemas.py`
2. Update imports in `app/modules/sku/router.py` and `app/api/endpoints/sku.py`
3. Remove `app/schemas/common.py` (empty)

### **Step 2: Consolidate Training Routes (Medium Risk)**
1. Merge `app/api/routes/training/schemas.py` → `app/modules/training/schemas.py`
2. Merge all route files into `app/modules/training/router.py`
3. Update `app/api/router.py` to import from `app.modules.training.router`
4. Delete `app/api/routes/training/` directory

### **Step 3: Migrate Database (High Risk - Do Last)**
1. Create SQLAlchemy repositories for training and SKU
2. Migrate `app/modules/training/service.py` to use repository
3. Migrate `app/modules/sku/router.py` to use repository
4. Remove or deprecate `app/core/database.py`

---

## 7. Testing Checklist

After each migration step, verify:
- [ ] All imports resolve correctly
- [ ] No circular import errors
- [ ] API endpoints still work
- [ ] Database queries execute successfully
- [ ] No broken business logic

---

## 8. Files to Delete (After Migration)

1. ✅ `app/core/database.py` (after SQLAlchemy migration)
2. ✅ `app/api/routes/training/` (entire directory after merge)
3. ✅ `app/schemas/` (entire directory after moving files)
4. ✅ `app/api/endpoints/sku.py` (if consolidating with sku/router.py)

---

**Report Status:** ✅ Complete  
**Ready for Phase 1:** ✅ Yes (with caution on database migration)
