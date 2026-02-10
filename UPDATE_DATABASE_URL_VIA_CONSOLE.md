# 🔧 Update DATABASE_URL via Cloud Run Console (Step-by-Step)

**Masalah:** `gcloud` command tidak terinstall  
**Solusi:** Update via Cloud Run Console (UI)

---

## 📋 **Step-by-Step Guide**

### **Step 1: Buka Cloud Run Console**

1. Buka browser
2. Kunjungi: **https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka?project=scout-os-dev**
3. Login jika diperlukan

---

### **Step 2: Edit Revision**

1. Di halaman Service details, klik tombol **"EDIT & DEPLOY NEW REVISION"** (di bagian atas)
2. Tunggu sampai halaman edit terbuka

---

### **Step 3: Update Environment Variables**

1. Scroll ke bawah sampai menemukan section **"VARIABLES & SECRETS"**
2. Cari variable **`DATABASE_URL`** di list
3. **Klik variable `DATABASE_URL`** untuk edit
4. **Update Value** dengan:
   ```
   postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```
   **⚠️ PENTING:** Pastikan ada `+asyncpg` setelah `postgresql`
5. **Klik SAVE** atau **UPDATE**

---

### **Step 4: Verifikasi Semua Environment Variables**

Pastikan semua variable ini ada dan benar:

- ✅ `ENVIRONMENT` = `production`
- ✅ `SECRET_KEY` = `uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc`
- ✅ `DATABASE_URL` = `postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres`
- ✅ `REDIS_URL` = `rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379`
- ✅ `ACCESS_TOKEN_EXPIRE_MINUTES` = `10080`

---

### **Step 5: Deploy**

1. Scroll ke bawah
2. Klik tombol **"DEPLOY"** atau **"CREATE"**
3. Tunggu deployment selesai (biasanya 1-2 menit)

---

### **Step 6: Test Endpoint**

Setelah deployment selesai, test endpoint:

```bash
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health
```

**Expected:** `200 OK` dengan JSON response (bukan `503`)

---

## 🔍 **Visual Guide**

**Di Cloud Run Console, cari section ini:**

```
┌─────────────────────────────────────┐
│ VARIABLES & SECRETS                 │
├─────────────────────────────────────┤
│ Name              Value              │
│ ENVIRONMENT       production         │
│ SECRET_KEY        uWi3eQyhnsmFjRr... │
│ DATABASE_URL      postgresql://...   │ ← EDIT INI!
│ REDIS_URL         rediss://...       │
│ ACCESS_TOKEN...   10080              │
└─────────────────────────────────────┘
```

**Klik `DATABASE_URL`, ubah value menjadi:**
```
postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```

---

## ⚠️ **PENTING: Format DATABASE_URL**

**SALAH:**
```
postgresql://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```

**BENAR:**
```
postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```

**Perbedaan:** Tambahkan `+asyncpg` setelah `postgresql`

---

## 🧪 **Verifikasi Setelah Update**

### **1. Cek Environment Variables:**

Di Cloud Run Console → Tab **REVISIONS** → Klik revision terbaru → Scroll ke **Environment Variables**

Pastikan `DATABASE_URL` sudah:
- ✅ Format: `postgresql+asyncpg://...`
- ✅ Bukan: `postgresql://...`

---

### **2. Test Endpoint:**

```bash
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health
```

**Expected:**
```json
{
  "success": true,
  "message": "Service health check completed",
  "data": {
    "status": "healthy" or "degraded",
    "environment": "production",
    "database": "connected",
    "redis": "connected"
  }
}
```

---

## 📋 **Checklist**

- [ ] Buka Cloud Run Console
- [ ] Klik "EDIT & DEPLOY NEW REVISION"
- [ ] Find `DATABASE_URL` di VARIABLES & SECRETS
- [ ] Update value dengan format `postgresql+asyncpg://...`
- [ ] Verifikasi semua env vars sudah benar
- [ ] Klik DEPLOY
- [ ] Tunggu deployment selesai
- [ ] Test endpoint (harusnya `200 OK`)

---

## 🔍 **Jika Masih Error Setelah Update**

### **Cek Application Logs:**

1. Cloud Run → `khasyaraka` → Tab **LOGS**
2. Filter: **Error** atau **Warning**
3. Cari error spesifik:
   - `ValidationError` = Environment variable masih salah
   - `ConnectionError` = Database/Redis tidak bisa connect
   - `ModuleNotFoundError` = Dependencies kurang

---

**Update DATABASE_URL via Console, lalu deploy ulang!** 🚀
