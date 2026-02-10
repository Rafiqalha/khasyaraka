# ✅ Verifikasi Konfigurasi Service Baru

**Dari Screenshot:**

## ✅ **Yang Sudah Benar:**

- ✅ **Service name:** `khasyaraka-v2`
- ✅ **Region:** `asia-southeast2 (Jakarta)`
- ✅ **Deployment:** "Continuously deploy from a repository" - GitHub selected
- ✅ **Cloud Build:** Selected
- ✅ **Branch:** `^main$` (matches main branch)

---

## ❌ **MASALAH: Source Location Dockerfile**

**Current (SALAH):**
```
Source location: /Dockerfile
```

**Should be (BENAR):**
```
Source location: scout_os_backend/Dockerfile
```

**Alasan:** Dockerfile ada di folder `scout_os_backend/`, bukan di root repository.

---

## 🔧 **FIX: Update Source Location**

### **Di Modal "Set up with Cloud Build":**

1. **Find:** Field **"Source location *"**
2. **Update Value:**
   ```
   scout_os_backend/Dockerfile
   ```
   **⚠️ PENTING:** Harus include folder `scout_os_backend/`
3. **Klik:** **SAVE** di modal

---

## 📋 **Setelah Setup Cloud Build**

### **Step 1: Set Environment Variables**

Setelah modal Cloud Build selesai, di halaman "Create service":

1. **Tab:** **"Variables & Secrets"** atau scroll ke section Environment Variables
2. **Add variables:**
   ```
   ENVIRONMENT=production
   SECRET_KEY=uWi3eQyhnsmFjRr9ta70c6hVvFM25SrZVVw2VpiWHFc
   DATABASE_URL=postgresql+asyncpg://postgres.ngikvuvhqiabpuarrbev:rafiqalha29@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
   REDIS_URL=rediss://default:AdscAAIncDExMjA2YjRkYTlkNjU0ZDUyOTE0ZDc4NGE3YjU4YjMwNHAxNTYwOTI@finer-leech-56092.upstash.io:6379
   ACCESS_TOKEN_EXPIRE_MINUTES=10080
   ```

---

### **Step 2: Set Scaling**

1. **Find:** Section **"Scaling"** atau **"Autoscaling"**
2. **Set:**
   - **Min instances:** `0`
   - **Max instances:** `20`
   - **Concurrency:** `80`

---

### **Step 3: Set Port**

1. **Find:** Field **"Container port"**
2. **Set:** `8080`

---

### **Step 4: Create Service**

1. **Klik:** **CREATE**
2. Tunggu deployment selesai (biasanya 2-3 menit untuk build pertama)

---

## ✅ **Checklist Konfigurasi**

- [ ] **Service name:** `khasyaraka-v2` ✅
- [ ] **Region:** `asia-southeast2` ✅
- [ ] **Deployment:** GitHub selected ✅
- [ ] **Cloud Build:** Selected ✅
- [ ] **Branch:** `^main$` ✅
- [ ] **Build Type:** Dockerfile ✅
- [ ] **Source location:** `scout_os_backend/Dockerfile` ❌ **PERLU DIUBAH!**
- [ ] **Environment Variables:** Akan di-set setelah ini
- [ ] **Scaling:** Akan di-set setelah ini
- [ ] **Port:** `8080` (akan di-set setelah ini)

---

## 🎯 **Action Items**

1. **Update Source Location** di modal Cloud Build:
   - Dari: `/Dockerfile`
   - Ke: `scout_os_backend/Dockerfile`
2. **Klik SAVE** di modal
3. **Set Environment Variables** setelah modal selesai
4. **Set Scaling** (Automatic, min 0, max 20)
5. **Set Port** (8080)
6. **CREATE** service

---

**Update Source Location ke `scout_os_backend/Dockerfile`, lalu lanjutkan setup!** 🚀
