# 🚨 Fix: Service is Disabled (503 Error)

**Error:** `503 Service Unavailable - Service is disabled`

**Kemungkinan Penyebab:**
1. Service memang disabled di Cloud Run
2. Environment variables belum di-set (container crash saat startup)
3. Container tidak bisa start karena error lain

---

## 🔧 SOLUSI STEP-BY-STEP

### **Step 1: Enable Service (Jika Disabled)**

#### **Via Console:**
1. Buka: https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka
2. Jika ada tombol **"ENABLE"** atau **"ACTIVATE"**, klik itu
3. Tunggu sampai service enabled

#### **Via CLI:**
```bash
# Cek status service
gcloud run services describe khasyaraka \
  --region asia-southeast2 \
  --format="value(status.conditions)"

# Jika disabled, update dengan minimal config
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --no-traffic
```

---

### **Step 2: Set Environment Variables (WAJIB!)**

**Via Console (Paling Mudah):**

1. Cloud Run → `khasyaraka` → **EDIT & DEPLOY NEW REVISION**
2. Tab **VARIABLES & SECRETS**
3. **Hapus semua variable lama** (jika ada placeholder)
4. **Add variables baru:**

   ```
   Name: ENVIRONMENT
   Value: production
   
   Name: SECRET_KEY
   Value: uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc
   
   Name: DATABASE_URL
   Value: postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
   
   Name: REDIS_URL
   Value: rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379
   
   Name: ACCESS_TOKEN_EXPIRE_MINUTES
   Value: 10080
   ```

5. **Klik DEPLOY** (atau **CREATE**)

---

### **Step 3: Cek Logs Setelah Deploy**

1. Cloud Run → `khasyaraka` → **LOGS**
2. Filter: **Error** atau **Warning**
3. Cari error spesifik:
   - `ValidationError` = Environment variable masih salah
   - `ConnectionError` = Database/Redis tidak bisa connect
   - `ModuleNotFoundError` = Dependencies kurang

---

### **Step 4: Verifikasi Environment Variables**

**Via Console:**
1. Cloud Run → `khasyaraka` → Tab **REVISIONS**
2. Klik revision terbaru
3. Scroll ke **Environment Variables**
4. Pastikan semua ada dan benar:
   - ✅ `ENVIRONMENT=production`
   - ✅ `SECRET_KEY` (bukan placeholder)
   - ✅ `DATABASE_URL` (format benar)
   - ✅ `REDIS_URL` (format benar)

---

## 🧪 Test Setelah Fix

```bash
# Test health endpoint
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health

# Expected: 200 OK dengan JSON response
# Bukan: 503 Service Unavailable
```

---

## 📋 Checklist Lengkap

- [ ] Service enabled (tidak disabled)
- [ ] `ENVIRONMENT=production` di-set
- [ ] `SECRET_KEY` di-set (bukan placeholder)
- [ ] `DATABASE_URL` di-set (format `postgresql+asyncpg://...`)
- [ ] `REDIS_URL` di-set (format `rediss://...`)
- [ ] Deploy setelah set semua env vars
- [ ] Cek logs untuk memastikan tidak ada error
- [ ] Test endpoint (harusnya `200 OK`)

---

## 🔍 Troubleshooting Lanjutan

### **Jika Masih Error Setelah Set Env Vars:**

1. **Cek Application Logs:**
   ```
   Cloud Run → khasyaraka → LOGS → Filter: Error
   ```

2. **Common Errors:**

   **A. ValidationError:**
   ```
   pydantic_core._pydantic_core.ValidationError: 1 validation error
   ```
   **Fix:** Pastikan semua required env vars di-set

   **B. ConnectionError:**
   ```
   ConnectionError: Failed to connect to Redis
   OperationalError: connection failed
   ```
   **Fix:** Cek format `REDIS_URL` dan `DATABASE_URL`

   **C. ModuleNotFoundError:**
   ```
   ModuleNotFoundError: No module named 'xxx'
   ```
   **Fix:** Cek `requirements.txt` lengkap

---

## 💡 Quick Fix (Copy-Paste)

**Jika punya gcloud CLI:**

```bash
cd /home/rafiq/Projek/khasyaraka/scout_os_backend

# Set semua environment variables
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars ENVIRONMENT=production \
  --set-env-vars SECRET_KEY="uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc" \
  --set-env-vars DATABASE_URL="postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres" \
  --set-env-vars REDIS_URL="rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379" \
  --set-env-vars ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Redeploy
gcloud run deploy khasyaraka --source . --region asia-southeast2

# Test
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health
```

---

## 🎯 Action Items

1. **Enable service** (jika disabled)
2. **Set environment variables** di Cloud Run Console
3. **Deploy** setelah set env vars
4. **Cek logs** untuk memastikan tidak ada error
5. **Test endpoint** (harusnya `200 OK`)

---

**Set environment variables di Cloud Run Console, lalu deploy ulang!** 🚀
