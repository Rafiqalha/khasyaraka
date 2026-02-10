# 🚨 Build Berhasil, Tapi Service Masih 503

**Status:**
- ✅ Build: Success
- ✅ Push: Success  
- ✅ Deploy: Success
- ❌ **Endpoint: Masih 503** (container tidak bisa start)

---

## 🔍 **Root Cause: DATABASE_URL Format Masih Salah**

Dari konfigurasi yang kamu tunjukkan, `DATABASE_URL` masih:
```
postgresql://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```

**Masalah:** Format `postgresql://` tidak compatible dengan SQLAlchemy Async + asyncpg driver.

**Harus diubah menjadi:**
```
postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```

**Perbedaan:** Tambahkan `+asyncpg` setelah `postgresql`

---

## 🔧 **SOLUSI: Update DATABASE_URL di Cloud Run**

### **Via Console (Paling Mudah):**

1. **Buka:** https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka
2. **Klik:** EDIT & DEPLOY NEW REVISION
3. **Tab:** VARIABLES & SECRETS
4. **Find:** `DATABASE_URL`
5. **Update Value:**
   ```
   postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```
   **⚠️ PENTING:** Tambahkan `+asyncpg` setelah `postgresql`
6. **Klik:** DEPLOY

---

### **Via gcloud CLI:**

```bash
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --update-env-vars DATABASE_URL="postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"
```

---

## 📋 **Complete Environment Variables (Setelah Fix)**

Pastikan semua ini di-set dengan benar:

```
ENVIRONMENT = production
SECRET_KEY = uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc
DATABASE_URL = postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
REDIS_URL = rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379
ACCESS_TOKEN_EXPIRE_MINUTES = 10080
```

---

## 🧪 **Test Setelah Fix**

```bash
# Test health endpoint
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health

# Expected: 200 OK dengan JSON response
# Bukan: 503 Service Unavailable
```

---

## 🔍 **Jika Masih Error Setelah Fix DATABASE_URL**

### **Cek Application Logs:**

1. Cloud Run → `khasyaraka` → **LOGS**
2. Filter: **Error** atau **Warning**
3. Cari error spesifik:
   - `ValidationError` = Environment variable masih salah
   - `ConnectionError` = Database/Redis tidak bisa connect
   - `ModuleNotFoundError` = Dependencies kurang

---

## ✅ **Checklist**

- [ ] Update `DATABASE_URL` dengan format `postgresql+asyncpg://`
- [ ] Deploy setelah update
- [ ] Cek logs untuk memastikan tidak ada error
- [ ] Test endpoint (harusnya `200 OK`)

---

**Fix DATABASE_URL format, lalu deploy ulang!** 🚀
