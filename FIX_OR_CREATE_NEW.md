# 🔄 Opsi: Fix Service Lama vs Buat Service Baru

**Status:** Service masih disabled dengan "Manual scaling, instances: 0"

**Dua Opsi:**

---

## 🛠️ **OPSI 1: Fix Service Lama (Coba Dulu)**

### **Step 1: Update DATABASE_URL (WAJIB!)**

1. **Buka:** https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka
2. **Klik:** **EDIT & DEPLOY NEW REVISION**
3. **Tab:** **Containers** → **Variables & Secrets**
4. **Find:** `DATABASE_URL`
5. **Update Value:**
   ```
   postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```
   **⚠️ PENTING:** Pastikan ada `+asyncpg` setelah `postgresql`

---

### **Step 2: Trigger Request untuk Wake Up Service**

Setelah deploy, coba trigger request:

```bash
# Test endpoint (ini akan trigger container start)
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health

# Atau dari browser:
# https://khasyaraka-890949539640.asia-southeast2.run.app/health
```

**Jika container bisa start**, service akan aktif otomatis.

---

### **Step 3: Cek Logs**

1. Cloud Run → `khasyaraka` → **LOGS**
2. Filter: **Error** atau **Warning**
3. Cari error spesifik

---

## 🆕 **OPSI 2: Buat Service Baru (Jika Opsi 1 Gagal)**

Jika service lama masih bermasalah, buat service baru dengan konfigurasi yang benar dari awal.

### **Step 1: Buat Service Baru**

1. **Buka:** https://console.cloud.google.com/run/services?project=scout-os-dev
2. **Klik:** **"+ CREATE SERVICE"** atau **"+ Deploy container"**
3. **Pilih:** **"Deploy one revision from an existing container image"**

---

### **Step 2: Configure Service**

**Basic Settings:**
- **Service name:** `khasyaraka-v2` (atau nama lain)
- **Region:** `asia-southeast2`
- **Container image URL:**
  ```
  asia-southeast2-docker.pkg.dev/scout-os-dev/cloud-run-source-deploy/khasyaraka/khasyaraka:latest
  ```
- **Port:** `8080`

**Scaling (PENTING!):**
- **Min instances:** `0`
- **Max instances:** `20`
- **Concurrency:** `80`

**Environment Variables:**
```
ENVIRONMENT=production
SECRET_KEY=uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc
DATABASE_URL=postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
REDIS_URL=rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

---

### **Step 3: Deploy**

1. **Klik:** **CREATE** atau **DEPLOY**
2. Tunggu deployment selesai
3. Test endpoint

---

## 🎯 **Rekomendasi**

**Coba Opsi 1 dulu:**
1. Update DATABASE_URL di service lama
2. Deploy
3. Trigger request untuk wake up service
4. Cek apakah service aktif

**Jika masih gagal, baru buat service baru (Opsi 2).**

---

## 📋 **Checklist Opsi 1**

- [ ] Update DATABASE_URL dengan format `postgresql+asyncpg://...`
- [ ] Deploy setelah update
- [ ] Trigger request (curl atau browser)
- [ ] Cek logs untuk error spesifik
- [ ] Test endpoint

---

## 📋 **Checklist Opsi 2 (Buat Service Baru)**

- [ ] Buat service baru dengan nama berbeda
- [ ] Set container image yang sama
- [ ] Set scaling: Automatic (min 0, max 20)
- [ ] Set semua environment variables dengan benar
- [ ] Deploy
- [ ] Test endpoint
- [ ] Update Flutter app dengan URL baru (jika perlu)

---

**Coba Opsi 1 dulu, jika masih gagal baru buat service baru!** 🚀
