# 🚨 Cloud Run Application Logs - Cara Akses

**Error:** Container failed to start and listen on port 8080

**Penyebab:** Masih perlu dilihat di **Application Logs** (bukan Build Logs)

---

## 📋 Cara Akses Application Logs (PENTING!)

### **Method 1: Via Google Cloud Console (Termudah)**

1. **Buka:** https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka/logs?project=scout-os-dev

2. **Atau manual:**
   - Google Cloud Console → **Cloud Run**
   - Klik service: **`khasyaraka`**
   - Klik tab **LOGS** (bukan "Build logs")
   - Filter: **Error** atau **Warning**

3. **Cari log dengan format:**
   ```
   ERROR | app.main | ...
   ERROR | app.core.config | ...
   Traceback (most recent call last):
   ```

---

### **Method 2: Via gcloud CLI**

```bash
# Cek log aplikasi terbaru (Error & Warning)
gcloud run services logs read khasyaraka \
  --region asia-southeast2 \
  --limit 50 \
  --format json | jq '.[] | select(.severity=="ERROR" or .severity=="WARNING") | .textPayload'

# Atau format lebih readable
gcloud run services logs read khasyaraka \
  --region asia-southeast2 \
  --limit 50
```

---

### **Method 3: Via Cloud Logging (Advanced)**

```bash
# Filter log dengan severity ERROR
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=khasyaraka AND severity>=ERROR" \
  --limit 50 \
  --format json | jq -r '.[] | "\(.timestamp) | \(.severity) | \(.textPayload)"'
```

---

## 🔍 Yang Harus Dicari di Log

### **1. ValidationError (Environment Variables)**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
Field required [type=missing, input_value=None, input_type=NoneType]
```
**Fix:** Set environment variables

---

### **2. ModuleNotFoundError**
```
ModuleNotFoundError: No module named 'xxx'
```
**Fix:** Tambahkan ke requirements.txt

---

### **3. ConnectionError**
```
ConnectionError: Failed to connect to Redis
OperationalError: connection failed
```
**Fix:** Cek REDIS_URL dan DATABASE_URL

---

### **4. ImportError**
```
ImportError: cannot import name 'xxx' from 'app.xxx'
```
**Fix:** Cek struktur code

---

## 🛠️ Quick Fix: Set Environment Variables

**Kemungkinan besar masalahnya adalah environment variables tidak di-set!**

### **Via gcloud CLI:**

```bash
# Set semua environment variables sekaligus
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars ENVIRONMENT=production \
  --set-env-vars SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  --set-env-vars DATABASE_URL="postgresql+asyncpg://user:pass@host:port/dbname" \
  --set-env-vars REDIS_URL="redis://host:port"

# Atau jika pakai rediss:// (TLS)
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars REDIS_URL="rediss://host:port"
```

**⚠️ GANTI:**
- `DATABASE_URL` dengan URL Supabase yang benar
- `REDIS_URL` dengan URL Redis yang benar
- `SECRET_KEY` dengan secret key yang aman

---

### **Via Console:**

1. Cloud Run → `khasyaraka` → **EDIT & DEPLOY NEW REVISION**
2. Tab **VARIABLES & SECRETS**
3. Add variables:
   - `ENVIRONMENT` = `production`
   - `SECRET_KEY` = (generate secret key)
   - `DATABASE_URL` = (Supabase connection string)
   - `REDIS_URL` = (Redis connection string)
4. **DEPLOY**

---

## 📝 Checklist Environment Variables

Pastikan semua ini di-set:

- [ ] `ENVIRONMENT=production`
- [ ] `SECRET_KEY` (tidak kosong, minimal 32 karakter)
- [ ] `DATABASE_URL` (format: `postgresql+asyncpg://...`)
- [ ] `REDIS_URL` (format: `redis://...` atau `rediss://...`)

---

## 🎯 Next Steps

1. **Cek Application Logs** (Method 1, 2, atau 3 di atas)
2. **Copy error message** yang muncul
3. **Set Environment Variables** (jika belum)
4. **Redeploy** setelah set env vars

---

**Setelah set environment variables, deploy ulang dan cek log lagi!**
