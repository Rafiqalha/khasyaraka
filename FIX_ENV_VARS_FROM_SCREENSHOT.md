# 🚨 FIX: Environment Variables Masalah Ditemukan!

**Dari screenshot Cloud Run Console:**

## ❌ Masalah yang Ditemukan:

1. **SECRET_KEY masih placeholder:**
   - Current: `ganti_dengan_random_string_y`
   - **Masalah:** Ini bukan secret key yang valid, akan gagal validasi

2. **REDIS_URL tidak ada:**
   - **Masalah:** Di production, `REDIS_URL` wajib di-set
   - Aplikasi akan crash saat startup karena validasi di `model_post_init()`

---

## ✅ SOLUSI: Update Environment Variables

### **Step 1: Generate SECRET_KEY yang Valid**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Copy output-nya** (contoh: `abc123xyz...`)

---

### **Step 2: Set Environment Variables di Cloud Run**

**Ganti dengan nilai yang benar:**

```bash
# Generate SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Update Cloud Run dengan environment variables yang benar
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars ENVIRONMENT=production \
  --set-env-vars SECRET_KEY="$SECRET_KEY" \
  --set-env-vars DATABASE_URL="postgresql+asyncpg://postgres.ngikvu..." \
  --set-env-vars REDIS_URL="redis://your-redis-host:port" \
  --set-env-vars ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

**⚠️ PENTING:**
- Ganti `DATABASE_URL` dengan URL lengkap dari Supabase
- Ganti `REDIS_URL` dengan URL Redis yang benar (Upstash atau Redis provider lain)

---

### **Step 3: Format Environment Variables**

**DATABASE_URL (Supabase):**
```
postgresql+asyncpg://postgres.xxxxx:password@aws-0-asia-southeast2.pooler.supabase.com:6543/postgres
```

**REDIS_URL (Upstash atau Redis):**
```
redis://default:password@host:port
```
**Atau dengan TLS:**
```
rediss://default:password@host:port
```

---

### **Step 4: Redeploy**

Setelah update environment variables, deploy ulang:

```bash
cd /home/rafiq/Projek/khasyaraka/scout_os_backend
gcloud run deploy khasyaraka --source . --region asia-southeast2
```

---

## 📋 Checklist Environment Variables

Pastikan semua ini di-set dengan nilai yang benar:

- [x] `ENVIRONMENT=production` ✅ (sudah benar)
- [ ] `SECRET_KEY` ❌ (masih placeholder, perlu diganti)
- [x] `DATABASE_URL` ✅ (ada, tapi perlu verifikasi format)
- [ ] `REDIS_URL` ❌ (tidak ada, perlu ditambahkan)
- [x] `ACCESS_TOKEN_EXPIRE_MINUTES=10080` ✅ (sudah benar)

---

## 🔍 Verifikasi Setelah Update

```bash
# Cek environment variables yang sudah di-set
gcloud run services describe khasyaraka \
  --region asia-southeast2 \
  --format="value(spec.template.spec.containers[0].env)"
```

**Expected output:**
```
ENVIRONMENT=production
SECRET_KEY=abc123xyz... (bukan placeholder)
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

---

## 🚀 Quick Fix Command (Copy-Paste Ready)

**Ganti `YOUR_REDIS_URL` dengan URL Redis yang benar:**

```bash
cd /home/rafiq/Projek/khasyaraka/scout_os_backend

# Generate SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Update environment variables
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars ENVIRONMENT=production \
  --set-env-vars SECRET_KEY="$SECRET_KEY" \
  --set-env-vars REDIS_URL="YOUR_REDIS_URL_HERE" \
  --set-env-vars ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Redeploy
gcloud run deploy khasyaraka --source . --region asia-southeast2
```

---

**Setelah ini, container harusnya bisa start!** ✅
