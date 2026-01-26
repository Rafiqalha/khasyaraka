# 🎓 Training API - Complete Guide

## Overview

This document provides complete documentation for the Training API module, including:
- API endpoints
- Database schema
- Data seeding
- Testing guide

---

## 📂 Project Structure

```
scout_os_backend/
├── app/
│   ├── api/
│   │   ├── router.py                    # Main API router (UPDATED)
│   │   └── routes/
│   │       └── training/                # NEW Training routes
│   │           ├── __init__.py          # Combines all training routers
│   │           ├── schemas.py           # Pydantic response models
│   │           ├── section.py           # Section endpoints
│   │           ├── unit.py              # Unit endpoints
│   │           ├── level.py             # Level endpoints
│   │           └── question.py          # Question endpoints
│   ├── data/
│   │   ├── section.json                 # Sections data (CLEANED)
│   │   ├── units.json                   # Units data (CLEANED)
│   │   ├── levels.json                  # Levels data (CLEANED)
│   │   └── question/
│   │       └── puk/
│   │           └── unit_1.json          # Questions data (CLEANED)
│   └── modules/
│       └── training/
│           └── models.py                # Database models (UPDATED)
└── seed_pramuka_data.py                 # NEW Seeding script
```

---

## 🗄️ Database Schema

### Tables Created

#### 1. `training_sections`
```sql
CREATE TABLE training_sections (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    tier VARCHAR(20) DEFAULT 'free',
    order INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Example:**
- id: `"puk"`
- title: `"Pengetahuan Umum Kepramukaan"`
- tier: `"free"`

#### 2. `training_units`
```sql
CREATE TABLE training_units (
    id VARCHAR(50) PRIMARY KEY,
    section_id VARCHAR(50) REFERENCES training_sections(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    order INTEGER DEFAULT 1,
    total_levels INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Example:**
- id: `"puk_unit_1"`
- section_id: `"puk"`
- title: `"Sejarah dan Trivia Kepramukaan"`

#### 3. `training_levels`
```sql
CREATE TABLE training_levels (
    id VARCHAR(50) PRIMARY KEY,
    unit_id VARCHAR(50) REFERENCES training_units(id),
    level_number INTEGER NOT NULL,
    difficulty VARCHAR(20) DEFAULT 'easy',
    total_questions INTEGER DEFAULT 5,
    min_correct INTEGER DEFAULT 4,
    xp_reward INTEGER DEFAULT 10,
    unlock_rule JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Example:**
- id: `"puk_u1_l1"`
- unit_id: `"puk_unit_1"`
- level_number: `1`
- difficulty: `"very_easy"`

#### 4. `training_questions`
```sql
CREATE TABLE training_questions (
    id VARCHAR(50) PRIMARY KEY,
    level_id VARCHAR(50) REFERENCES training_levels(id),
    type VARCHAR(30) NOT NULL,
    question TEXT NOT NULL,
    payload JSON NOT NULL,
    xp INTEGER DEFAULT 2,
    order INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Example:**
- id: `"q_puk_u1_l1_01"`
- level_id: `"puk_u1_l1"`
- type: `"multiple_choice"`
- question: `"Siapakah pendiri Gerakan Kepanduan Dunia?"`

---

## 🚀 Getting Started

### 1. Database Setup

Ensure PostgreSQL is running and environment variables are set:

```bash
# .env file
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scout_os
```

### 2. Run Migrations (Create Tables)

```bash
cd scout_os_backend
python seed_pramuka_data.py
```

This script will:
- ✅ Create all tables (if they don't exist)
- ✅ Seed data from JSON files
- ✅ Safe to run multiple times (idempotent)

### 3. Start FastAPI Server

```bash
uvicorn app.main:app --reload
```

### 4. Access API Documentation

Open browser:
```
http://localhost:8000/docs
```

You should see a new **"Training"** section in Swagger UI.

---

## 📡 API Endpoints

Base URL: `http://localhost:8000/api/v1/training`

### Section Endpoints

#### GET `/training/sections`
Get all active training sections.

**Response:**
```json
{
  "total": 1,
  "sections": [
    {
      "id": "puk",
      "title": "Pengetahuan Umum Kepramukaan",
      "description": "Materi dasar dan hafalan umum kepramukaan",
      "tier": "free",
      "order": 1,
      "is_active": true,
      "created_at": "2026-01-18T10:00:00Z"
    }
  ]
}
```

#### GET `/training/sections/{section_id}`
Get a specific section.

**Response:**
```json
{
  "id": "puk",
  "title": "Pengetahuan Umum Kepramukaan",
  "description": "Materi dasar dan hafalan umum kepramukaan",
  "tier": "free",
  "order": 1,
  "is_active": true,
  "created_at": "2026-01-18T10:00:00Z"
}
```

---

### Unit Endpoints

#### GET `/training/sections/{section_id}/units`
Get all units in a section.

**Response:**
```json
{
  "total": 1,
  "section_id": "puk",
  "units": [
    {
      "id": "puk_unit_1",
      "section_id": "puk",
      "title": "Sejarah dan Trivia Kepramukaan",
      "description": "Sejarah singkat dan pengetahuan umum dasar tentang Pramuka",
      "order": 1,
      "total_levels": 1,
      "is_active": true,
      "created_at": "2026-01-18T10:00:00Z"
    }
  ]
}
```

#### GET `/training/units/{unit_id}`
Get a specific unit.

---

### Level Endpoints

#### GET `/training/units/{unit_id}/levels`
Get all levels in a unit.

**Response:**
```json
{
  "total": 1,
  "unit_id": "puk_unit_1",
  "levels": [
    {
      "id": "puk_u1_l1",
      "unit_id": "puk_unit_1",
      "level_number": 1,
      "difficulty": "very_easy",
      "total_questions": 1,
      "min_correct": 1,
      "xp_reward": 10,
      "unlock_rule": {
        "type": "start",
        "value": true
      },
      "is_active": true,
      "created_at": "2026-01-18T10:00:00Z"
    }
  ]
}
```

#### GET `/training/levels/{level_id}`
Get a specific level.

---

### Question Endpoints

#### GET `/training/levels/{level_id}/questions`
Get all questions in a level.

**Response:**
```json
{
  "total": 1,
  "level_id": "puk_u1_l1",
  "questions": [
    {
      "id": "q_puk_u1_l1_01",
      "level_id": "puk_u1_l1",
      "type": "multiple_choice",
      "question": "Siapakah pendiri Gerakan Kepanduan Dunia?",
      "payload": {
        "options": [
          "Lord Baden Powell",
          "Ki Hajar Dewantara",
          "Soekarno",
          "Sri Sultan Hamengkubuwono IX"
        ],
        "correct_answer": "Lord Baden Powell",
        "shuffle": true
      },
      "xp": 2,
      "order": 1,
      "is_active": true,
      "created_at": "2026-01-18T10:00:00Z"
    }
  ]
}
```

#### GET `/training/questions/{question_id}`
Get a specific question.

---

## 🧪 Testing Guide

### Using cURL

```bash
# Get all sections
curl http://localhost:8000/api/v1/training/sections

# Get units for a section
curl http://localhost:8000/api/v1/training/sections/puk/units

# Get levels for a unit
curl http://localhost:8000/api/v1/training/units/puk_unit_1/levels

# Get questions for a level
curl http://localhost:8000/api/v1/training/levels/puk_u1_l1/questions
```

### Using Python Requests

```python
import requests

base_url = "http://localhost:8000/api/v1/training"

# Get sections
response = requests.get(f"{base_url}/sections")
print(response.json())

# Get units
response = requests.get(f"{base_url}/sections/puk/units")
print(response.json())

# Get levels
response = requests.get(f"{base_url}/units/puk_unit_1/levels")
print(response.json())

# Get questions
response = requests.get(f"{base_url}/levels/puk_u1_l1/questions")
print(response.json())
```

---

## 📊 Data Flow

```
JSON Files → Seeding Script → PostgreSQL → FastAPI → Client
    ↓             ↓               ↓           ↓
section.json   CREATE       training_    GET /training/
units.json     INSERT       sections      sections
levels.json    UPDATE       training_         ↓
questions/                  units         Response JSON
                           training_
                           levels
                           training_
                           questions
```

---

## 🔄 JSON to Database Mapping

| JSON Field | Database Column | Type | Notes |
|------------|----------------|------|-------|
| `id` | `id` | VARCHAR(50) | Primary key, used as-is |
| `title` | `title` | VARCHAR(200) | Display name |
| `description` | `description` | TEXT | Optional |
| `tier` | `tier` | VARCHAR(20) | "free" or "premium" |
| `order` | `order` | INTEGER | Display order |
| `section_id` | `section_id` | VARCHAR(50) | Foreign key |
| `unit_id` | `unit_id` | VARCHAR(50) | Foreign key |
| `level_id` | `level_id` | VARCHAR(50) | Foreign key |
| `level_number` | `level_number` | INTEGER | 1, 2, 3, ... |
| `difficulty` | `difficulty` | VARCHAR(20) | very_easy, easy, medium, hard |
| `total_questions` | `total_questions` | INTEGER | Expected question count |
| `min_correct` | `min_correct` | INTEGER | Passing threshold |
| `xp_reward` | `xp_reward` | INTEGER | XP for completing level |
| `unlock_rule` | `unlock_rule` | JSON | Unlock conditions |
| `type` | `type` | VARCHAR(30) | Question type |
| `question` | `question` | TEXT | Question text |
| `payload` | `payload` | JSON | Question-specific data |
| `xp` | `xp` | INTEGER | XP per question |

---

## 🎯 Current Data Status

**Seeded Data:**
- ✅ 1 Section: "Pengetahuan Umum Kepramukaan"
- ✅ 1 Unit: "Sejarah dan Trivia Kepramukaan"
- ✅ 1 Level: Level 1 (very_easy)
- ✅ 1 Question: Multiple choice about Baden Powell

**Tier:** All data is `free` (freemium content)

---

## 🛠️ Maintenance

### Re-seeding Data

If you update JSON files and want to refresh the database:

```bash
python seed_pramuka_data.py
```

The script is idempotent:
- Existing records are **UPDATED** (not duplicated)
- New records are **INSERTED**
- Uses exact IDs from JSON files

### Adding New Content

1. **Add a new section:**
   - Edit `app/data/section.json`
   - Add new entry with unique `id`
   - Run seeding script

2. **Add a new unit:**
   - Edit `app/data/units.json`
   - Link to existing `section_id`
   - Run seeding script

3. **Add a new level:**
   - Edit `app/data/levels.json`
   - Link to existing `unit_id`
   - Run seeding script

4. **Add new questions:**
   - Create/edit `app/data/question/{section}/{unit}.json`
   - Link to existing `level_id`
   - Run seeding script

---

## 🔒 Security Notes

**Current Status:**
- ❌ No authentication required (intentional for MVP)
- ❌ No rate limiting
- ❌ No premium content filtering

**Future Enhancements:**
- Add JWT authentication for user-specific progress
- Add rate limiting for abuse prevention
- Add premium tier logic
- Add user progress tracking

---

## 📝 Notes

1. **scout_data.json is deprecated** - Use modular JSON files instead
2. **All IDs are strings** - Not UUIDs, but human-readable IDs (e.g., "puk", "puk_unit_1")
3. **No cascade deletes exposed** - Only soft deletes via `is_active` flag
4. **Question payloads are flexible** - Different question types can have different payload structures

---

## ✅ Checklist

- [x] Database models created
- [x] Seeding script implemented
- [x] JSON data cleaned (1 section, 1 unit, 1 level, 1 question)
- [x] API routes created (sections, units, levels, questions)
- [x] Routes registered in main router
- [x] Swagger documentation available
- [x] Idempotent seeding
- [x] Read-only endpoints
- [x] Active records filtering
- [x] Proper error handling (404s)

---

**Status:** ✅ COMPLETE  
**API Prefix:** `/api/v1/training`  
**Swagger Tag:** `Training`  
**Authentication:** None (yet)  
**Data Tier:** Freemium (all free for now)

---

*Last Updated: 2026-01-18*
