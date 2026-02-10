# 🚨 FIX: DATABASE_URL Format Salah!

**Masalah Ditemukan dari Cloud Run Configuration:**

## ❌ **DATABASE_URL Format Salah**

**Current (SALAH):**
```
postgresql://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```

**Should be (BENAR):**
```
postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```

**Perbedaan:** Harus pakai `postgresql+asyncpg://` (bukan `postgresql://`)

---

## ✅ **Environment Variables Lainnya Sudah Benar**

- ✅ `SECRET_KEY` = Valid (bukan placeholder)
- ✅ `ENVIRONMENT` = `production`
- ✅ `REDIS_URL` = Format `rediss://` benar (TLS)
- ✅ `ACCESS_TOKEN_EXPIRE_MINUTES` = `10080`

---

## 🔧 **SOLUSI: Update DATABASE_URL**

### **Via Console:**

1. Cloud Run → `khasyaraka` → **EDIT & DEPLOY NEW REVISION**
2. Tab **VARIABLES & SECRETS**
3. Find `DATABASE_URL`
4. **Update Value:**
   ```
   postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```
   **⚠️ PENTING:** Tambahkan `+asyncpg` setelah `postgresql`
5. **Klik DEPLOY**

---

### **Via gcloud CLI:**

```bash
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --update-env-vars DATABASE_URL="postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"
```

---

## 🔍 **Kenapa Harus `postgresql+asyncpg://`?**

- Backend menggunakan **SQLAlchemy Async** dengan driver **asyncpg**
- Format `postgresql://` adalah untuk driver sync (psycopg2)
- Format `postgresql+asyncpg://` adalah untuk driver async (asyncpg)
- Tanpa `+asyncpg`, SQLAlchemy tidak tahu harus pakai driver async

---

## 📋 **Complete Environment Variables (Setelah Fix)**

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
# Test endpoint
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health

# Expected: 200 OK dengan JSON response
# Bukan: 503 atau connection error
```

---

## ✅ **Checklist**

- [ ] Update `DATABASE_URL` dengan format `postgresql+asyncpg://`
- [ ] Deploy setelah update
- [ ] Cek logs untuk memastikan tidak ada error
- [ ] Test endpoint (harusnya `200 OK`)

---

**Fix DATABASE_URL format, lalu deploy ulang!** 🚀
