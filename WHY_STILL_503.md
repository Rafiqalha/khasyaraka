# 🚨 Mengapa Masih Error 503?

**Error:** "Service Unavailable - Service is disabled"

**Penyebab:** Environment variables di Cloud Run belum di-set!

---

## ⚠️ PENTING: .env vs Cloud Run Environment Variables

### **File `.env` (Local Development):**
- ✅ Hanya untuk **local development**
- ✅ Digunakan saat run `uvicorn` di laptop
- ❌ **TIDAK digunakan** oleh Cloud Run

### **Cloud Run Environment Variables:**
- ✅ Harus di-set **langsung di Cloud Run Console**
- ✅ Cloud Run **tidak membaca** file `.env`
- ✅ Setiap deployment perlu environment variables yang benar

---

## 🔧 SOLUSI: Set Environment Variables di Cloud Run

### **Step 1: Buka Cloud Run Console**

1. Buka: https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka
2. Klik **EDIT & DEPLOY NEW REVISION**

---

### **Step 2: Set Environment Variables**

Tab **VARIABLES & SECRETS**, tambahkan/update:

#### **1. ENVIRONMENT**
```
Name: ENVIRONMENT
Value: production
```

#### **2. SECRET_KEY**
```
Name: SECRET_KEY
Value: uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc
```
*(Gunakan nilai dari .env file)*

#### **3. DATABASE_URL**
```
Name: DATABASE_URL
Value: postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```
*(Gunakan nilai dari .env file)*

#### **4. REDIS_URL**
```
Name: REDIS_URL
Value: rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379
```
*(Gunakan nilai dari .env file)*

#### **5. ACCESS_TOKEN_EXPIRE_MINUTES** (Optional)
```
Name: ACCESS_TOKEN_EXPIRE_MINUTES
Value: 10080
```

---

### **Step 3: Deploy**

1. Klik **DEPLOY** (atau **CREATE**)
2. Tunggu deployment selesai
3. Cek logs untuk memastikan tidak ada error

---

## 🧪 Verifikasi Setelah Deploy

### **Test Endpoint:**
```bash
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health
```

**Expected:** `200 OK` (bukan `503`)

---

## 📋 Checklist

- [ ] `ENVIRONMENT=production` di-set di Cloud Run
- [ ] `SECRET_KEY` di-set (bukan placeholder)
- [ ] `DATABASE_URL` di-set (format `postgresql+asyncpg://...`)
- [ ] `REDIS_URL` di-set (format `rediss://...`)
- [ ] Deploy setelah set semua env vars
- [ ] Test endpoint (harusnya `200 OK`)

---

## 🔍 Jika Masih Error Setelah Set Env Vars

### **Cek Application Logs:**

1. Cloud Run → `khasyaraka` → **LOGS**
2. Filter: **Error** atau **Warning**
3. Cari error spesifik:
   - `ValidationError` = Environment variable masih salah
   - `ConnectionError` = Database/Redis tidak bisa connect
   - `ModuleNotFoundError` = Dependencies kurang

---

## 💡 Quick Fix Script

Jika punya `gcloud` CLI:

```bash
cd /home/rafiq/Projek/khasyaraka/scout_os_backend

# Set semua environment variables sekaligus
gcloud run services update khasyaraka \
  --region asia-southeast2 \
  --set-env-vars ENVIRONMENT=production \
  --set-env-vars SECRET_KEY="uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc" \
  --set-env-vars DATABASE_URL="postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres" \
  --set-env-vars REDIS_URL="rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379" \
  --set-env-vars ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Redeploy
gcloud run deploy khasyaraka --source . --region asia-southeast2
```

---

**Set environment variables di Cloud Run Console, lalu deploy ulang!** 🚀
