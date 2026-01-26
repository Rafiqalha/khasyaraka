# Architecture Violations & Dependency Analysis Report

**Generated:** After Training module refactoring  
**Purpose:** Identify all architectural violations and propose minimal refactors

---

## 🔍 Executive Summary

**Current State:**
- ✅ Training module: Fully refactored (router → service → repository → db)
- ⚠️ Auth module: Router passes DB directly to service (bypasses repository)
- ❌ SKU module: Direct Supabase usage in router (no repository/service)
- ❌ Legacy files: `app/api/endpoints/sku.py` (duplicate/legacy)
- ❌ Legacy Supabase: Still used in 3 files

**Target Architecture:**
```
Router → Service → Repository → DB Session
```

---

## 📊 Violations by Risk Level

### 🔴 **CRITICAL RISK** (Must Fix Immediately)

#### **Violation 1: SKU Module - Direct Supabase in Router**
- **File:** `app/modules/sku/router.py`
- **Issue:** 
  - Direct Supabase queries in router (lines 28, 47, 66)
  - Business logic in router (answer verification logic, lines 84-118)
  - No repository layer
  - No service layer
- **Impact:** HIGH - Active production code, violates all architectural principles
- **Risk:** Database queries mixed with HTTP handling, business logic in wrong layer
- **Fix Required:**
  1. Create `app/modules/sku/models.py` (SQLAlchemy models)
  2. Create `app/modules/sku/repository.py` (database access)
  3. Create `app/modules/sku/service.py` (business logic)
  4. Refactor router to use service only

#### **Violation 2: Legacy Supabase Client Still Imported**
- **Files:**
  - `app/modules/sku/router.py` (line 5)
  - `app/modules/training/service.py` (line 28) - legacy methods only
  - `app/api/endpoints/sku.py` (line 2) - legacy file
- **Issue:** `app/core/database.py` (Supabase client) still in use
- **Impact:** HIGH - Blocks removal of legacy code
- **Risk:** Technical debt, dependency on deprecated infrastructure
- **Fix Required:**
  1. Refactor SKU module (removes 1 import)
  2. Migrate training legacy methods or deprecate (removes 1 import)
  3. Delete `app/api/endpoints/sku.py` (removes 1 import)
  4. Delete `app/core/database.py`

---

### 🟡 **MEDIUM RISK** (Should Fix Soon)

#### **Violation 3: Auth Module - Bypasses Repository Pattern**
- **File:** `app/modules/auth/router.py`
- **Issue:**
  - Router passes `db: AsyncSession` directly to service (lines 9, 19, 48)
  - Service has direct DB queries (not using repository)
  - Repository file exists but is empty
- **Impact:** MEDIUM - Works but violates architecture
- **Risk:** Inconsistent pattern, harder to test/mock
- **Fix Required:**
  1. Implement `app/modules/auth/repository.py`
  2. Refactor `app/modules/auth/service.py` to use repository
  3. Update router to inject service (not DB session)

#### **Violation 4: Legacy Endpoint File Still Exists**
- **File:** `app/api/endpoints/sku.py`
- **Issue:** Duplicate/legacy endpoint file (not registered in main router)
- **Impact:** LOW-MEDIUM - Dead code, confusion
- **Risk:** Code duplication, maintenance burden
- **Fix Required:**
  1. Verify not used anywhere
  2. Delete file

#### **Violation 5: Training Module - Legacy Supabase Methods**
- **File:** `app/modules/training/service.py`
- **Issue:** Legacy methods still use Supabase (lines 47-95)
- **Impact:** MEDIUM - Backward compatibility vs. clean architecture
- **Risk:** Mixed patterns, technical debt
- **Fix Required:**
  1. Option A: Migrate legacy endpoints to SQLAlchemy
  2. Option B: Deprecate legacy endpoints
  3. Remove Supabase dependency from service

---

### 🟢 **LOW RISK** (Nice to Have)

#### **Violation 6: Empty Repository Files**
- **Files:**
  - `app/modules/auth/repository.py` (empty)
  - `app/modules/users/repository.py` (likely empty)
- **Issue:** Repository files exist but not implemented
- **Impact:** LOW - Not blocking, but inconsistent
- **Risk:** Confusion about architecture
- **Fix Required:** Implement when refactoring those modules

#### **Violation 7: Legacy Folder Structure**
- **Folders:**
  - `app/api/routes/` (empty, can be deleted)
  - `app/schemas/` (empty, can be deleted)
- **Issue:** Empty legacy directories
- **Impact:** LOW - Just cleanup
- **Risk:** None
- **Fix Required:** Delete empty directories

---

## 📋 Detailed Analysis

### **1. Supabase Usage Analysis**

#### **Active Supabase Imports:**
```
app/modules/sku/router.py          → Line 5: from app.core.database import supabase
app/modules/training/service.py    → Line 28: from app.core.database import supabase (legacy only)
app/api/endpoints/sku.py           → Line 2: from app.core.database import supabase (legacy file)
```

#### **Supabase Usage Patterns:**
- **SKU Router:** 3 direct queries (levels, missions, verify)
- **Training Service:** 2 legacy methods (get_learning_path, get_questions_by_lesson)
- **Legacy Endpoint:** 3 queries (duplicate of SKU router)

#### **Supabase Tables Referenced:**
- `khasyaraka_sku_levels`
- `khasyaraka_sku_points`
- `khasyaraka_sku_tasks`
- `khasyaraka_special_missions`
- `khasyaraka_mission_tasks`
- `khasyaraka_training_paths` (legacy)
- `khasyaraka_training_lessons` (legacy)
- `khasyaraka_training_questions` (legacy)

---

### **2. Router Architecture Analysis**

#### **✅ Correct Pattern (Training):**
```python
# app/modules/training/router.py
def get_service(db: AsyncSession = Depends(get_db)) -> TrainingService:
    return TrainingService(db=db)

@router.get("/sections")
async def get_sections(service: TrainingService = Depends(get_service)):
    sections = await service.get_all_sections()
    return SectionListResponse(...)
```

#### **⚠️ Partial Pattern (Auth):**
```python
# app/modules/auth/router.py
@router.post("/register")
async def register(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    user = await service.create_user(db, user_in)  # Direct DB passed to service
    return user
```
**Issue:** Service receives DB directly, bypasses repository

#### **❌ Wrong Pattern (SKU):**
```python
# app/modules/sku/router.py
from app.core.database import supabase

@router.get("/levels")
async def get_sku_levels():
    response = supabase.table("khasyaraka_sku_levels")...  # Direct DB in router
    return response.data
```
**Issue:** Direct database access + business logic in router

---

### **3. Business Logic Location Analysis**

#### **✅ Correct (Training):**
- Business logic: `app/modules/training/service.py`
- Database access: `app/modules/training/repository.py`
- HTTP handling: `app/modules/training/router.py`

#### **⚠️ Partial (Auth):**
- Business logic: `app/modules/auth/service.py` (but uses DB directly)
- Database access: Missing (repository empty)
- HTTP handling: `app/modules/auth/router.py`

#### **❌ Wrong (SKU):**
- Business logic: `app/modules/sku/router.py` (lines 84-118 - answer verification)
- Database access: `app/modules/sku/router.py` (direct Supabase)
- HTTP handling: `app/modules/sku/router.py` (mixed with everything)

---

### **4. Circular Import Risk Analysis**

#### **Current Dependencies:**
```
app/modules/training/router.py
  → app.modules.training.service
  → app.modules.training.repository
  → app.modules.training.models
  → app.db.session
✅ SAFE - Standard flow

app/modules/auth/router.py
  → app.modules.auth.service
  → app.modules.users.models (via service)
  → app.db.session
✅ SAFE - No circular dependencies

app/modules/sku/router.py
  → app.core.database (Supabase)
  → app.modules.sku.schemas
✅ SAFE - But wrong architecture
```

**Overall Risk:** ✅ **LOW** - No circular imports detected

---

### **5. Legacy Files & Folders**

#### **Legacy Files:**
- ✅ `app/api/routes/training/` - **DELETED** (already removed)
- ❌ `app/api/endpoints/sku.py` - **EXISTS** (duplicate, not registered)
- ❌ `app/core/database.py` - **EXISTS** (Supabase client)

#### **Legacy Folders:**
- ❌ `app/api/routes/` - **EMPTY** (can delete)
- ❌ `app/schemas/` - **EMPTY** (can delete)

---

## 🎯 Refactoring Priority & Plan

### **Phase 1: Remove Supabase (CRITICAL)**

#### **Step 1.1: Refactor SKU Module** (Highest Priority)
**Files to Create:**
- `app/modules/sku/models.py` - SQLAlchemy models for SKU tables
- `app/modules/sku/repository.py` - Database access layer
- `app/modules/sku/service.py` - Business logic (answer verification)

**Files to Update:**
- `app/modules/sku/router.py` - Remove Supabase, use service

**Estimated Impact:** Removes 1 Supabase import, fixes critical violation

#### **Step 1.2: Handle Training Legacy Methods**
**Options:**
- **Option A:** Migrate legacy endpoints to SQLAlchemy (recommended)
- **Option B:** Deprecate legacy endpoints, remove Supabase dependency

**Files to Update:**
- `app/modules/training/service.py` - Remove Supabase import

#### **Step 1.3: Delete Legacy Files**
- Delete `app/api/endpoints/sku.py`
- Delete `app/core/database.py`
- Delete `app/api/routes/` (empty)
- Delete `app/schemas/` (empty)

---

### **Phase 2: Fix Auth Module (MEDIUM)**

#### **Step 2.1: Implement Auth Repository**
- Create methods in `app/modules/auth/repository.py`
- Move DB queries from service to repository

#### **Step 2.2: Refactor Auth Service**
- Update service to use repository
- Remove direct DB parameter

#### **Step 2.3: Update Auth Router**
- Inject service (not DB) via dependency
- Remove `db: AsyncSession = Depends(get_db)` from endpoints

---

### **Phase 3: Cleanup (LOW)**

#### **Step 3.1: Verify No Supabase in Requirements**
- Check `requirements.txt` for `supabase` package
- Remove if present

#### **Step 3.2: Update Documentation**
- Remove Supabase references from docs
- Update architecture diagrams

---

## 📈 Risk Assessment Matrix

| Violation | Risk Level | Impact | Effort | Priority |
|-----------|-----------|--------|--------|----------|
| SKU Module Supabase | 🔴 CRITICAL | HIGH | MEDIUM | **P0** |
| Legacy Supabase Client | 🔴 CRITICAL | HIGH | LOW | **P0** |
| Auth Bypasses Repository | 🟡 MEDIUM | MEDIUM | MEDIUM | **P1** |
| Legacy Endpoint File | 🟡 MEDIUM | LOW | LOW | **P2** |
| Training Legacy Methods | 🟡 MEDIUM | MEDIUM | MEDIUM | **P1** |
| Empty Repositories | 🟢 LOW | LOW | LOW | **P3** |
| Empty Folders | 🟢 LOW | NONE | LOW | **P3** |

---

## ✅ Success Criteria

After refactoring, verify:
- [ ] No imports of `app.core.database`
- [ ] No Supabase usage anywhere
- [ ] All routers use service layer
- [ ] All services use repository layer
- [ ] No business logic in routers
- [ ] No direct DB access in routers
- [ ] `app/core/database.py` deleted
- [ ] `app/api/endpoints/sku.py` deleted
- [ ] All modules follow: Router → Service → Repository → DB

---

## 🔄 Migration Order (Recommended)

1. **SKU Module Refactor** (removes 1 Supabase import, fixes critical violation)
2. **Delete Legacy Files** (removes 2 more Supabase imports)
3. **Training Legacy Methods** (removes last Supabase import)
4. **Auth Module Refactor** (completes architecture)
5. **Cleanup** (empty folders, docs)

---

**Report Status:** ✅ Complete  
**Ready for Refactoring:** ✅ Yes - Start with SKU module (P0)
