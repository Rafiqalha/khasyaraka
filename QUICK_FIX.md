# Quick Fix Guide

## 1. Fix Uvicorn Command
❌ Wrong: `uvicorn main:app`
✅ Correct: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## 2. Fix Database Connection for Alembic

### Option A: Setup Local PostgreSQL (Fastest)
```bash
sudo -u postgres psql
```
Then run:
```sql
CREATE USER scout_admin WITH PASSWORD 'scout_password_local';
CREATE DATABASE scout_os_local OWNER scout_admin;
GRANT ALL PRIVILEGES ON DATABASE scout_os_local TO scout_admin;
\q
```

### Option B: Use Docker (Stop Local PostgreSQL First)
```bash
sudo systemctl stop postgresql
cd /home/rafiq/Projek/khasyaraka
docker-compose up -d db
```

## 3. Test Database Connection
```bash
cd scout_os_backend
source venv/bin/activate
python -c "from app.core.config import settings; print(settings.SQLALCHEMY_DATABASE_URI)"
```

## 4. Run Alembic (After Database is Ready)
```bash
# Autogenerate requires database connection
alembic revision --autogenerate -m "initial_migration"

# Or create manual migration (no database needed)
alembic revision -m "initial_migration"
```

## 5. Start Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
