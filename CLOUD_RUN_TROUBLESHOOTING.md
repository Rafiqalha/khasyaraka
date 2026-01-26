# 🔍 Cloud Run Troubleshooting Guide - Diagnosa Bedah Jantung

**Tujuan:** Menemukan penyebab pasti error "Container failed to start" di Cloud Run

---

## 📋 Langkah 1: Cek Log Aplikasi (WAJIB!)

### **Cara Akses Log:**

1. Buka **Google Cloud Console**: https://console.cloud.google.com
2. Pilih project: **`scout-os-dev`**
3. Navigasi ke: **Cloud Run** → **Services** → **`khasyaraka`**
4. Klik tab **LOGS** (di menu atas)
5. **PENTING:** Filter log:
   - **Severity:** Pilih **Error** atau **Warning**
   - **Time Range:** Pilih **Last 1 hour** atau **Last 24 hours**

### **Yang Harus Dicari:**

#### **A. ModuleNotFoundError (Dependencies Missing)**
```
ModuleNotFoundError: No module named 'xxx'
```
**Artinya:** Package tidak ada di `requirements.txt` atau tidak terinstall

**Solusi:** Tambahkan ke `requirements.txt` dan redeploy

---

#### **B. ValidationError (Environment Variables)**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
Field required [type=missing, input_value=None, input_type=NoneType]
```
**Artinya:** Environment variable tidak di-set di Cloud Run

**Solusi:** Set environment variables di Cloud Run:
- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `ENVIRONMENT=production`

---

#### **C. ConnectionError (Database/Redis)**
```
OperationalError: connection failed
ConnectionError: Failed to connect to Redis
```
**Artinya:** Database atau Redis tidak bisa diakses

**Solusi:** 
- Cek `DATABASE_URL` format (harus `postgresql+asyncpg://...`)
- Cek `REDIS_URL` format (harus `redis://...` atau `rediss://...`)
- Cek firewall/network settings

---

#### **D. ImportError (Code Issues)**
```
ImportError: cannot import name 'xxx' from 'app.xxx'
```
**Artinya:** Ada masalah di struktur code atau circular import

**Solusi:** Cek file yang disebutkan di error

---

## 🛠️ Langkah 2: Verifikasi Requirements.txt

### **Dependencies Wajib (Sudah Ada):**

✅ **Core Framework:**
- `fastapi==0.128.0` ✅
- `uvicorn==0.40.0` ✅
- `starlette==0.50.0` ✅ (dependency FastAPI)

✅ **Database:**
- `sqlalchemy==2.0.45` ✅
- `asyncpg==0.31.0` ✅
- `alembic==1.18.1` ✅
- `psycopg2-binary==2.9.11` ✅

✅ **Validation & Config:**
- `pydantic==2.12.5` ✅
- `pydantic-settings==2.12.0` ✅
- `pydantic_core==2.41.5` ✅

✅ **Authentication:**
- `python-jose==3.5.0` ✅
- `passlib==1.7.4` ✅
- `python-multipart==0.0.21` ✅
- `cryptography==46.0.3` ✅ (untuk JWT)

✅ **Cache:**
- `redis==7.1.0` ✅

✅ **Utilities:**
- `python-dotenv==1.2.1` ✅
- `requests==2.32.5` ✅

---

### **Verifikasi Requirements.txt:**

**Status:** ✅ **SEMUA DEPENDENCIES SUDAH LENGKAP**

Tidak ada yang kurang! Semua package yang digunakan di code sudah tercatat.

---

## 🔧 Langkah 3: Generate Requirements.txt Ulang (Opsional)

Jika masih ragu, generate ulang dari venv:

```bash
cd /home/rafiq/Projek/khasyaraka/scout_os_backend

# Aktifkan venv
source venv/bin/activate

# Generate requirements.txt dari packages yang terinstall
pip freeze > requirements.txt

# Review dan commit
git add requirements.txt
git commit -m "Update requirements.txt"
git push origin main
```

**⚠️ PERHATIAN:** `pip freeze` akan include SEMUA packages, termasuk dependencies transitif. Ini bisa membuat file besar, tapi lebih aman.

---

## 🚀 Langkah 4: Deploy dengan Environment Variables

### **Set Environment Variables di Cloud Run:**

```bash
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars SECRET_KEY="your-secret-key-here" \
  --set-env-vars DATABASE_URL="postgresql+asyncpg://user:pass@host:port/db" \
  --set-env-vars REDIS_URL="redis://host:port" \
  --set-env-vars ENVIRONMENT="production"
```

**Atau via Console:**
1. Cloud Run → `khasyaraka` → **EDIT & DEPLOY NEW REVISION**
2. Tab **VARIABLES & SECRETS**
3. Add variables:
   - `SECRET_KEY` = `your-secret-key`
   - `DATABASE_URL` = `your-db-url`
   - `REDIS_URL` = `your-redis-url`
   - `ENVIRONMENT` = `production`

---

## 📝 Langkah 5: Checklist Pre-Deploy

Sebelum deploy, pastikan:

- [ ] `requirements.txt` lengkap (✅ sudah lengkap)
- [ ] `Dockerfile` benar (✅ sudah fix)
- [ ] Environment variables di-set (⚠️ **CEK INI!**)
- [ ] `SECRET_KEY` tidak kosong
- [ ] `DATABASE_URL` format benar (`postgresql+asyncpg://...`)
- [ ] `REDIS_URL` format benar (`redis://...` atau `rediss://...`)

---

## 🎯 Langkah 6: Test Lokal Sebelum Deploy

```bash
cd /home/rafiq/Projek/khasyaraka/scout_os_backend

# Test dengan environment variables production
export ENVIRONMENT=production
export SECRET_KEY="test-secret-key"
export DATABASE_URL="your-db-url"
export REDIS_URL="your-redis-url"

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Expected output:
# INFO:     Started server process
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8080
```

Jika error di lokal, fix dulu sebelum deploy ke Cloud Run.

---

## 🔍 Common Errors & Solutions

### **Error 1: "Container failed to start"**
**Kemungkinan:**
- Environment variables tidak di-set
- `SECRET_KEY` kosong
- Database connection failed

**Solusi:** Cek log aplikasi (Langkah 1)

---

### **Error 2: "ModuleNotFoundError"**
**Kemungkinan:**
- Package tidak ada di `requirements.txt`
- Versi tidak compatible

**Solusi:** 
- Tambahkan ke `requirements.txt`
- Atau generate ulang dengan `pip freeze`

---

### **Error 3: "ValidationError"**
**Kemungkinan:**
- Environment variable required tidak di-set
- Format environment variable salah

**Solusi:**
- Set semua required env vars
- Cek format `DATABASE_URL` dan `REDIS_URL`

---

## 📞 Next Steps

1. **Cek Log Cloud Run** (Langkah 1) - **WAJIB!**
2. Copy error message merah ke sini
3. Kita akan fix berdasarkan error spesifik

**Jangan menyerah! Error ini pasti bisa diatasi setelah kita tahu penyebab pastinya.** 💪

---

**File ini:** `CLOUD_RUN_TROUBLESHOOTING.md`
