# 🚨 Fix: Service Disabled - Manual Scaling dengan Instances: 0

**Dari Screenshot:**
- ✅ Service: `khasyaraka` ada di list
- ❌ **Status: Disabled** - "Service is disabled since instance is set to 0 for manual scaling"
- ❌ **Scaling: Manual** dengan **Instances: 0**

**Masalah:** Service menggunakan Manual scaling dengan 0 instances, sehingga service disabled.

---

## 🔧 **SOLUSI: Ubah Scaling ke Automatic**

### **Via Console:**

1. **Buka:** https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka
2. **Klik:** **EDIT & DEPLOY NEW REVISION**
3. **Tab:** **GENERAL** atau scroll ke **Scaling** section
4. **Find:** **"Autoscaling"** atau **"Scaling"** settings
5. **Ubah dari "Manual" ke "Automatic":**
   - **Min instances:** `0` (atau `1` jika ingin selalu ada instance)
   - **Max instances:** `20` (atau sesuai kebutuhan)
   - **Concurrency:** `80` (default Cloud Run)
6. **Klik:** **DEPLOY**

---

## 📋 **Scaling Configuration yang Benar**

### **Option 1: Automatic Scaling (Recommended)**

```
Scaling: Automatic
Min instances: 0 (scale to zero when no traffic)
Max instances: 20
Concurrency: 80
```

**Keuntungan:**
- ✅ Scale otomatis berdasarkan traffic
- ✅ Scale to zero saat tidak ada traffic (hemat cost)
- ✅ Scale up saat ada request

---

### **Option 2: Manual Scaling (Jika Tetap Ingin Manual)**

```
Scaling: Manual
Instances: 1 (atau lebih, minimal 1)
```

**Keuntungan:**
- ✅ Selalu ada instance running
- ✅ Tidak ada cold start delay

**Kekurangan:**
- ❌ Tetap bayar meskipun tidak ada traffic
- ❌ Tidak scale otomatis

---

## 🎯 **Recommended: Automatic Scaling**

**Konfigurasi yang Disarankan:**

1. **Scaling:** Automatic
2. **Min instances:** `0` (untuk hemat cost)
3. **Max instances:** `20` (atau sesuai kebutuhan)
4. **Concurrency:** `80` (default Cloud Run)
5. **CPU:** `1`
6. **Memory:** `512MiB`

---

## 🔍 **Step-by-Step: Ubah Scaling**

### **Via Console:**

1. **Buka:** https://console.cloud.google.com/run/detail/asia-southeast2/khasyaraka
2. **Klik:** **EDIT & DEPLOY NEW REVISION**
3. **Tab:** **GENERAL** atau scroll ke **"Scaling"** section
4. **Find:** **"Autoscaling"** dropdown atau radio button
5. **Pilih:** **"Automatic"** (bukan "Manual")
6. **Set:**
   - **Min instances:** `0`
   - **Max instances:** `20`
7. **Klik:** **DEPLOY**

---

## ✅ **Setelah Ubah Scaling**

### **Test Endpoint:**

```bash
curl https://khasyaraka-890949539640.asia-southeast2.run.app/health
```

**Expected:**
- Jika scaling sudah benar: `200 OK` (container akan start otomatis saat ada request)
- Jika masih error: Cek logs untuk error spesifik

---

## 📋 **Checklist**

- [ ] Buka Cloud Run Console
- [ ] Klik "EDIT & DEPLOY NEW REVISION"
- [ ] Find "Scaling" atau "Autoscaling" section
- [ ] Ubah dari "Manual" ke "Automatic"
- [ ] Set Min instances: 0, Max instances: 20
- [ ] Klik DEPLOY
- [ ] Test endpoint (harusnya `200 OK`)

---

## 🔍 **Jika Masih Error Setelah Ubah Scaling**

### **Cek Application Logs:**

1. Cloud Run → `khasyaraka` → **LOGS**
2. Filter: **Error** atau **Warning**
3. Cari error spesifik:
   - `ValidationError` = Environment variable masih salah
   - `ConnectionError` = Database/Redis tidak bisa connect
   - `ModuleNotFoundError` = Dependencies kurang

---

## 💡 **Catatan Penting**

- **Manual scaling dengan 0 instances** = Service disabled
- **Automatic scaling** = Service akan start otomatis saat ada request
- **Min instances: 0** = Scale to zero (hemat cost)
- **Min instances: 1** = Selalu ada instance (tidak ada cold start)

---

**Ubah scaling ke Automatic, lalu deploy ulang!** 🚀
