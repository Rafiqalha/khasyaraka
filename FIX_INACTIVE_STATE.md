# 🚨 Fix: Service Masih "Inactive State"

**Status:** "This resource is in an inactive state"

**Penyebab:** Container tidak bisa start, kemungkinan karena:
1. **DATABASE_URL format masih salah** (masih `postgresql://` bukan `postgresql+asyncpg://`)
2. **Container crash saat startup** (environment variables salah)
3. **Manual scaling dengan 0 instances** masih aktif

---

## 🔧 **SOLUSI: Fix Environment Variables & Enable Service**

### **Step 1: Update DATABASE_URL (WAJIB!)**

1. **Buka:** https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka
2. **Klik:** **EDIT & DEPLOY NEW REVISION**
3. **Tab:** **Containers** → Sub-tab **"Variables & Secrets"**
4. **Find:** `DATABASE_URL`
5. **Update Value:**
   ```
   postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```
   **⚠️ PENTING:** Pastikan ada `+asyncpg` setelah `postgresql` (bukan `postgresql://`)

---

### **Step 2: Verifikasi Semua Environment Variables**

Pastikan semua ini ada dan benar:

- ✅ `ENVIRONMENT` = `production`
- ✅ `SECRET_KEY` = `uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc`
- ✅ `DATABASE_URL` = `postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres`
- ✅ `REDIS_URL` = `rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379`
- ✅ `ACCESS_TOKEN_EXPIRE_MINUTES` = `10080`

---

### **Step 3: Cari Scaling Settings**

**Cara menemukan scaling settings:**

1. **Di halaman "Deploy revision":**
   - Scroll ke bawah
   - Cari section **"Scaling"** atau **"Autoscaling"**
   - Atau klik **"Show advanced settings"**

2. **Atau di Service Details:**
   - Kembali ke Service Details page
   - Scroll ke bawah
   - Cari section **"Scaling"**
   - Klik **"Edit"** jika ada

3. **Ubah scaling:**
   - Dari **"Manual"** ke **"Automatic"**
   - Atau jika tetap Manual, set **Min instances: 1** (bukan 0)

---

### **Step 4: Deploy**

1. Setelah update semua settings
2. **Klik:** **DEPLOY**
3. Tunggu deployment selesai (1-2 menit)

---

### **Step 5: Test Endpoint**

```bash
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health
```

**Expected:** `200 OK` dengan JSON response (bukan `503` atau inactive)

---

## 🔍 **Jika Masih Inactive Setelah Deploy**

### **Cek Application Logs:**

1. Cloud Run → `khasyaraka` → Tab **LOGS**
2. Filter: **Error** atau **Warning**
3. Cari error spesifik:
   - `ValidationError` = Environment variable masih salah
   - `ConnectionError` = Database/Redis tidak bisa connect
   - `ModuleNotFoundError` = Dependencies kurang

---

## 📋 **Checklist Lengkap**

- [ ] Update `DATABASE_URL` dengan format `postgresql+asyncpg://...`
- [ ] Verifikasi semua environment variables sudah benar
- [ ] Cari scaling settings, ubah ke Automatic (atau Manual dengan min 1)
- [ ] Deploy setelah update semua settings
- [ ] Cek logs untuk memastikan tidak ada error
- [ ] Test endpoint (harusnya `200 OK`)

---

## 💡 **Quick Fix Priority**

**Yang paling penting:**
1. ✅ **Update DATABASE_URL** format (`postgresql+asyncpg://`)
2. ✅ **Deploy** setelah update
3. ✅ **Cek logs** untuk error spesifik

**Scaling bisa di-fix nanti setelah container bisa start.**

---

**Update DATABASE_URL format dulu, lalu deploy ulang!** 🚀
