# Backend Refactoring Plan: Domain-Driven Clean Architecture

## 📊 Current Structure Analysis

### **Issues Identified:**

1. **Duplicate Routing Layers** ⚠️
   - `app/api/routes/training/` (newer, detailed routes - 7 files)
   - `app/modules/training/router.py` (older, simpler routes - 1 file)
   - Both registered in `app/api/router.py` causing confusion

2. **Inconsistent Module Structure**
   - Some modules have complete structure: `models`, `repository`, `service`, `router`, `schemas`
   - Some modules have empty files: `users/router.py`, `payments/router.py` (empty)
   - Training has extra `logic/` subdirectory with 3 files

3. **Scattered Services**
   - Global services in `app/services/` (4 files: achievement, analytics, anti_cheat, notification)
   - Module-specific services in `app/modules/*/service.py`
   - Overlap: `app/services/anti_cheat_service.py` vs `app/modules/training/logic/anti_cheat.py`

4. **Database Confusion**
   - `app/db/` (SQLAlchemy async setup - correct)
   - `app/core/database.py` (Supabase client - legacy, should be removed or moved)

5. **Schema Organization**
   - Global schemas in `app/schemas/` (common.py, sku.py)
   - Module schemas in `app/modules/*/schemas.py`
   - Training has schemas in both `api/routes/training/schemas.py` AND `modules/training/schemas.py`

6. **Missing Target Modules**
   - Current: `auth`, `users`, `training`, `cyber`, `hiking`, `dashboard`, `events`, `gamification`, `payments`, `regu`, `sku`
   - Target needs: `progress`, `billing`, `notification` (some exist but need consolidation)

---

## 🎯 Target Structure

```
app/
├── core/                    # Core infrastructure (unchanged)
│   ├── config.py
│   ├── security.py
│   ├── permissions.py
│   ├── rate_limit.py
│   └── feature_flags.py
│
├── db/                      # Database setup (unchanged)
│   ├── base.py
│   ├── session.py
│   └── migrations/
│
├── middlewares/             # NEW: HTTP middlewares
│   ├── __init__.py
│   ├── auth.py
│   ├── cors.py
│   └── error_handler.py
│
├── modules/                 # Domain modules (refactored)
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── training/            # Consolidate api/routes/training into here
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   ├── router.py        # Merge api/routes/training/* into this
│   │   └── logic/           # Keep business logic separate
│   │       ├── progress_tracker.py
│   │       ├── lesson_engine.py
│   │       └── anti_cheat.py
│   │
│   ├── progress/            # NEW: Extract from training
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── gamification/        # Keep as-is, enhance
│   ├── billing/             # RENAME: payments → billing
│   ├── cyber/               # Keep as-is
│   ├── hiking/              # Keep as-is
│   ├── notification/        # NEW: Extract from services/
│   ├── auth/                # Keep as-is (or merge into users?)
│   └── [other modules...]
│
├── services/                # Shared cross-domain services
│   ├── __init__.py
│   ├── achievement_service.py    # Keep
│   ├── analytics_service.py      # Keep
│   └── anti_cheat_service.py     # Keep (global, not training-specific)
│
├── utils/                   # Shared utilities (unchanged)
│   ├── crypto.py
│   ├── geo.py
│   └── time.py
│
├── data/                    # Static data (unchanged)
│   └── ...
│
└── main.py                  # App entry point
```

---

## 📋 Step-by-Step Refactoring Plan

### **Phase 1: Foundation Cleanup** (Low Risk)

#### Step 1.1: Remove Duplicate Database Setup
- **Action**: Remove or deprecate `app/core/database.py` (Supabase legacy)
- **Impact**: Low - only used by old training service
- **Files**: `app/core/database.py`
- **Check**: Verify no imports reference it

#### Step 1.2: Create Middlewares Directory
- **Action**: Create `app/middlewares/` with `__init__.py`
- **Impact**: None - new directory
- **Files**: New directory structure

#### Step 1.3: Consolidate Global Schemas
- **Action**: Move `app/schemas/common.py` → `app/core/schemas.py` (if truly common)
- **Action**: Move `app/schemas/sku.py` → `app/modules/sku/schemas.py`
- **Impact**: Medium - need to update imports
- **Files**: `app/schemas/*` → move to appropriate locations

---

### **Phase 2: Training Module Consolidation** (Medium Risk)

#### Step 2.1: Analyze Training Routes
- **Current**: 
  - `app/api/routes/training/` (7 files: section, unit, level, question, path, schemas, __init__)
  - `app/modules/training/router.py` (simple, old routes)
- **Action**: 
  1. Review both route sets
  2. Keep `api/routes/training/` (newer, more complete)
  3. Merge into `app/modules/training/router.py`
  4. Delete `app/api/routes/training/` after merge

#### Step 2.2: Consolidate Training Schemas
- **Current**: 
  - `app/api/routes/training/schemas.py`
  - `app/modules/training/schemas.py`
- **Action**: Merge into `app/modules/training/schemas.py`
- **Impact**: Update imports in routes

#### Step 2.3: Update Training Router Registration
- **Action**: Update `app/api/router.py` to import from `modules/training/router`
- **Impact**: Low - just import path change

#### Step 2.4: Clean Up Training Service
- **Action**: Review `app/modules/training/service.py` (uses Supabase)
- **Action**: Migrate to use repository pattern if needed
- **Impact**: Medium - may need to update business logic

---

### **Phase 3: Extract Progress Module** (Medium Risk)

#### Step 3.1: Create Progress Module Structure
- **Action**: Create `app/modules/progress/` with standard structure
- **Files**: `__init__.py`, `models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`

#### Step 3.2: Extract Progress Logic from Training
- **Action**: Move `app/modules/training/logic/progress_tracker.py` → `app/modules/progress/service.py`
- **Action**: Create progress models if needed
- **Impact**: Medium - need to update training module to use progress service

#### Step 3.3: Create Progress Router
- **Action**: Add endpoints for user progress tracking
- **Impact**: Low - new endpoints

---

### **Phase 4: Rename & Consolidate Services** (Low-Medium Risk)

#### Step 4.1: Rename Payments → Billing
- **Action**: `app/modules/payments/` → `app/modules/billing/`
- **Action**: Update all imports
- **Impact**: Medium - need to update imports everywhere

#### Step 4.2: Extract Notification Module
- **Action**: Move `app/services/notification_service.py` → `app/modules/notification/service.py`
- **Action**: Create notification module structure (models, schemas, router)
- **Impact**: Medium - update imports

#### Step 4.3: Consolidate Anti-Cheat
- **Action**: Review overlap between:
  - `app/services/anti_cheat_service.py` (global)
  - `app/modules/training/logic/anti_cheat.py` (training-specific)
- **Action**: Keep global in services/, training-specific in training/logic/
- **Impact**: Low - clarify separation

---

### **Phase 5: Clean Up Empty/Incomplete Modules** (Low Risk)

#### Step 5.1: Audit Module Completeness
- **Check**: `users/router.py`, `payments/router.py` (empty)
- **Action**: Either implement or remove placeholder files
- **Impact**: Low - cleanup

#### Step 5.2: Standardize Module Structure
- **Action**: Ensure all modules have consistent structure
- **Template**: `models.py`, `schemas.py`, `repository.py`, `service.py`, `router.py`
- **Impact**: Low - organizational

---

### **Phase 6: Update Main Router** (Low Risk)

#### Step 6.1: Consolidate Router Registration
- **Action**: Update `app/api/router.py` to import all from `modules/*/router`
- **Action**: Remove `app/api/routes/` directory after migration
- **Impact**: Low - just import updates

#### Step 6.2: Add Billing Feature Gating
- **Action**: Add middleware/decoration for premium features
- **Action**: Use `core/feature_flags.py` for gating
- **Impact**: Medium - new functionality

---

## 🔄 Migration Order (Recommended)

1. **Phase 1** (Foundation) - Safest, no business logic changes
2. **Phase 5** (Cleanup) - Low risk, organizational
3. **Phase 2** (Training) - Most critical, do carefully
4. **Phase 4** (Services) - Medium complexity
5. **Phase 3** (Progress) - New module, can be done in parallel
6. **Phase 6** (Final) - Integration and feature gating

---

## ⚠️ Critical Considerations

1. **Database Migrations**: Ensure Alembic migrations are updated if models move
2. **Import Updates**: Use find/replace carefully, test after each phase
3. **API Compatibility**: Maintain backward compatibility during transition
4. **Testing**: Test each module after refactoring
5. **Business Logic**: DO NOT change business logic - only move files

---

## 📝 Implementation Notes

- **Incremental**: One module at a time, test after each
- **Git Commits**: Commit after each successful phase
- **Rollback Plan**: Keep old structure until new one is verified
- **Documentation**: Update API docs after router changes

---

## ✅ Success Criteria

- [ ] No duplicate routing layers
- [ ] All modules follow consistent structure
- [ ] All imports updated and working
- [ ] No broken business logic
- [ ] Billing feature gating ready
- [ ] Progress module extracted
- [ ] All tests passing

---

**Ready to proceed?** Start with Phase 1, Step 1.1 (Foundation Cleanup).
